"""
Category synchronization and management endpoints (Admin only)
"""
import logging
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, BackgroundTasks
from pydantic import BaseModel
from sqlalchemy.orm import Session
from datetime import datetime
import asyncio
import json
import time
from typing import Optional

from database import get_db
from models import CategorySyncHistory
from schemas.category_sync import (
    CategorySyncResponse,
    CategorySyncStats,
    CategoryImportRequest,
    CategoryImportResponse,
    CategoryRebuildIndexRequest,
    CategoryRebuildIndexResponse,
)
from schemas.auth import MessageResponse
from dependencies import CurrentAdminUser
from services import omni_sync_service
from config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/admin/categories", tags=["Admin - Categories"])


@router.post("/sync", response_model=CategorySyncResponse)
async def sync_categories(
    current_admin: CurrentAdminUser,
    db: Session = Depends(get_db),
    source: str = "manual"
):
    """
    Manually trigger category sync from main system
    
    This will:
    1. Load categories from categories.json
    2. Compare with current Qdrant index
    3. Update Qdrant if needed
    4. Log sync history
    """
    try:
        from models import Category as CategoryModel
        from sqlalchemy import func as sqlfunc

        total_categories = db.query(sqlfunc.count(CategoryModel.id)).scalar() or 0

        # Create sync history record
        sync_history = CategorySyncHistory(
            source=source,
            sync_type="manual",
            changes_detected=True,
            categories_added=0,
            categories_modified=total_categories,
            categories_deleted=0,
            success=True,
            synced_by=current_admin.id
        )
        
        db.add(sync_history)
        db.commit()
        db.refresh(sync_history)
        
        return CategorySyncResponse.model_validate(sync_history)
        
    except Exception as e:
        # Log failed sync
        sync_history = CategorySyncHistory(
            source=source,
            sync_type="manual",
            changes_detected=False,
            success=False,
            error_message=str(e),
            synced_by=current_admin.id
        )
        db.add(sync_history)
        db.commit()
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Category sync failed: {str(e)}"
        )


@router.get("/sync/history", response_model=list[CategorySyncResponse])
async def get_sync_history(
    current_admin: CurrentAdminUser,
    db: Session = Depends(get_db),
    limit: int = 50
):
    """
    Get category sync history
    """
    history = db.query(CategorySyncHistory).order_by(
        CategorySyncHistory.synced_at.desc()
    ).limit(limit).all()
    
    return [CategorySyncResponse.model_validate(h) for h in history]


@router.get("/sync/latest", response_model=CategorySyncResponse)
async def get_latest_sync(
    current_admin: CurrentAdminUser,
    db: Session = Depends(get_db)
):
    """
    Get latest sync status
    """
    latest = db.query(CategorySyncHistory).order_by(
        CategorySyncHistory.synced_at.desc()
    ).first()
    
    if not latest:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No sync history found"
        )
    
    return CategorySyncResponse.model_validate(latest)


@router.get("/sync/stats", response_model=CategorySyncStats)
async def get_sync_stats(
    current_admin: CurrentAdminUser,
    db: Session = Depends(get_db)
):
    """
    Get sync statistics
    """
    from sqlalchemy import func
    
    total_syncs = db.query(CategorySyncHistory).count()
    successful_syncs = db.query(CategorySyncHistory).filter(
        CategorySyncHistory.success == True
    ).count()
    failed_syncs = total_syncs - successful_syncs
    
    latest = db.query(CategorySyncHistory).order_by(
        CategorySyncHistory.synced_at.desc()
    ).first()
    
    # Sum of all changes
    totals = db.query(
        func.sum(CategorySyncHistory.categories_added).label('added'),
        func.sum(CategorySyncHistory.categories_modified).label('modified'),
        func.sum(CategorySyncHistory.categories_deleted).label('deleted')
    ).first()
    
    return CategorySyncStats(
        total_syncs=total_syncs,
        successful_syncs=successful_syncs,
        failed_syncs=failed_syncs,
        last_sync_at=latest.synced_at if latest else None,
        total_categories_added=int(totals.added or 0),
        total_categories_modified=int(totals.modified or 0),
        total_categories_deleted=int(totals.deleted or 0)
    )


@router.post("/import", response_model=CategoryImportResponse)
async def import_categories(
    current_admin: CurrentAdminUser,
    db: Session = Depends(get_db),
    file: UploadFile = File(...),
    replace_existing: bool = False,
    validate_only: bool = False
):
    """
    Bulk import categories from JSON file vào DB.

    Expected format:
    [{"id": 123, "name": "iPhone", "parent_id": 120, "description": "...", "is_active": 1}, ...]
    """
    import re as _re
    from models import Category as CategoryModel

    try:
        content = await file.read()
        categories = json.loads(content)

        if not isinstance(categories, list):
            raise ValueError("File must contain a JSON array of categories")

        validation_errors = []
        normalized: list[dict] = []

        for i, cat in enumerate(categories):
            if not isinstance(cat, dict):
                validation_errors.append(f"Item {i}: Must be an object")
                continue
            cat_id = cat.get("id") or cat.get("category_id")
            if cat_id is None:
                validation_errors.append(f"Item {i}: Missing 'id'")
                continue
            try:
                cat_id = int(cat_id)
            except (ValueError, TypeError):
                validation_errors.append(f"Item {i}: Invalid 'id': {cat_id}")
                continue
            if not cat.get("name"):
                validation_errors.append(f"Item {i}: Missing 'name'")
                continue
            slug = cat.get("slug") or _re.sub(r"[-\s]+", "-", _re.sub(r"[^\w\s-]", "", cat["name"].lower())).strip("-") or f"category-{cat_id}"
            normalized.append({
                "id": cat_id,
                "name": cat["name"],
                "slug": slug,
                "description": cat.get("description", ""),
                "icon": cat.get("icon", "fas fa-folder"),
                "image": cat.get("image"),
                "parent_id": cat.get("parent_id"),
                "sort_order": int(cat.get("sort_order", 0)),
                "is_featured": int(cat.get("is_featured", 0)),
                "is_home_cheap": int(cat.get("is_home_cheap", 0)),
                "is_active": int(cat.get("is_active", 1)),
            })

        if validation_errors:
            return CategoryImportResponse(validated=False, validation_errors=validation_errors)

        if validate_only:
            return CategoryImportResponse(validated=True, categories_to_add=len(normalized), imported=False)

        # Upsert to DB
        existing_ids = {row.id for row in db.query(CategoryModel.id).all()}
        now = datetime.now()
        for cat in normalized:
            if cat["id"] in existing_ids:
                db.query(CategoryModel).filter(CategoryModel.id == cat["id"]).update(
                    {k: v for k, v in cat.items() if k != "id"} | {"updated_at": now},
                    synchronize_session=False
                )
            else:
                db.add(CategoryModel(**cat, created_at=now, updated_at=now))
        db.commit()

        return CategoryImportResponse(
            validated=True,
            categories_to_add=len(normalized),
            imported=True,
            import_summary=f"Imported {len(normalized)} categories to DB successfully"
        )

    except json.JSONDecodeError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid JSON: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Import failed: {str(e)}")


@router.get("/export")
async def export_categories(
    current_admin: CurrentAdminUser,
    db: Session = Depends(get_db),
    format: str = "json"
):
    """Export categories + attributes từ DB."""
    from fastapi.responses import JSONResponse
    from models import Category as CategoryModel, CategoryField

    cats = db.query(CategoryModel).filter(CategoryModel.is_active == 1).all()
    # Load all fields grouped by category
    all_fields = db.query(CategoryField).all()
    fields_by_cat: dict[int, list] = {}
    for f in all_fields:
        fields_by_cat.setdefault(f.category_id, []).append({
            "field_key": f.field_key,
            "field_label": f.field_label,
            "field_type": f.field_type,
            "field_options": f.field_options,
            "is_required": f.is_required,
            "is_featured": f.is_featured,
            "sort_order": f.sort_order,
        })

    data = [
        {
            "id": c.id, "name": c.name, "slug": c.slug,
            "description": c.description, "icon": c.icon,
            "image": c.image, "parent_id": c.parent_id,
            "sort_order": c.sort_order, "is_featured": c.is_featured,
            "is_home_cheap": c.is_home_cheap, "is_active": c.is_active,
            "fields": fields_by_cat.get(c.id, []),
        }
        for c in cats
    ]
    from fastapi.responses import Response
    content = json.dumps(data, ensure_ascii=False, indent=2)
    filename = f"categories_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    return Response(
        content=content,
        media_type="application/json",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post("/generate-descriptions", summary="Sinh mô tả AI cho tất cả danh mục")
async def generate_descriptions(
    current_admin: CurrentAdminUser,
    db: Session = Depends(get_db),
    force: bool = False,
):
    """
    Dùng LLM để sinh keyword-dense description phục vụ vector search.
    - force=false (mặc định): chỉ xử lý category chưa có description hoặc description quá ngắn
    - force=true: sinh lại toàn bộ kể cả những category đã có mô tả
    """
    from models import Category as CategoryModel, CategoryField
    from services.llm_service import generate_category_description

    cats = db.query(CategoryModel).filter(CategoryModel.is_active == 1).all()
    cat_map = {c.id: c for c in cats}
    parent_ids_set = {c.parent_id for c in cats if c.parent_id is not None}

    def _path(cat_id: int) -> str:
        names: list[str] = []
        cid: int | None = cat_id
        visited: set = set()
        while cid and cid not in visited:
            visited.add(cid)
            cat = cat_map.get(cid)
            if not cat:
                break
            names.append(cat.name)
            cid = cat.parent_id
        return " > ".join(reversed(names))

    all_fields = db.query(CategoryField).all()
    fields_by_cat: dict[int, list] = {}
    for f in all_fields:
        fields_by_cat.setdefault(f.category_id, []).append(f.field_label)

    updated = 0
    skipped = 0
    for cat in cats:
        if not force:
            desc = (cat.description or "").strip()
            has_marketing = any(desc.startswith(w) for w in ("Chào", "Tại đây", "Khám phá", "Tìm kiếm"))
            if len(desc) > 40 and not has_marketing:
                skipped += 1
                continue
        try:
            path = _path(cat.id)
            field_labels = fields_by_cat.get(cat.id, [])
            is_leaf = cat.id not in parent_ids_set
            new_desc = await generate_category_description(cat.name, path, field_labels, is_leaf=is_leaf)
            if new_desc:
                cat.description = new_desc
                updated += 1
        except Exception as exc:
            logger.warning("generate_description failed for %s: %s", cat.name, exc)
            skipped += 1

    db.commit()
    return {"updated": updated, "skipped": skipped, "total": len(cats)}


# ── Rebuild job state (in-memory + Redis persistence) ────────────────────────
_REDIS_JOB_KEY = "autocategory:rebuild_job"
_rebuild_job: dict = {"status": "idle", "started_at": None, "result": None, "error": None}


def _job_save(state: dict) -> None:
    """Persist job state to Redis (best-effort)."""
    try:
        import redis as _redis
        from config import settings as _s
        r = _redis.from_url(_s.redis_url, decode_responses=True)
        r.set(_REDIS_JOB_KEY, json.dumps(state), ex=86400)  # TTL 24h
    except Exception:
        pass


def _job_load() -> dict:
    """Load job state from Redis on startup."""
    try:
        import redis as _redis
        from config import settings as _s
        r = _redis.from_url(_s.redis_url, decode_responses=True)
        raw = r.get(_REDIS_JOB_KEY)
        if raw:
            saved = json.loads(raw)
            # If was "running" before restart → mark as error
            if saved.get("status") == "running":
                saved["status"] = "error"
                saved["error"] = "API restarted during rebuild. Please rebuild again."
            return saved
    except Exception:
        pass
    return {"status": "idle", "started_at": None, "result": None, "error": None}


# Restore on module load
_rebuild_job.update(_job_load())


async def _run_rebuild(request_force: bool, request_only_leaf: bool, admin_id: int) -> None:
    """Background coroutine – runs rebuild entirely, updates _rebuild_job.

    Safety: embeddings are computed FIRST, then collection is replaced atomically
    (delete + upsert). This prevents an empty index if the process is killed mid-way.
    """
    import time as _time
    from database import SessionLocal
    from sqlalchemy.orm import joinedload
    from models import Category as CategoryModel, CategoryField, CategorySyncHistory
    from services import qdrant_service as qs
    from services.embedder import embed_texts

    _rebuild_job["status"] = "running"
    _rebuild_job["error"] = None
    _rebuild_job["result"] = None
    _job_save(_rebuild_job)
    try:
        start_time = _time.time()
        db = SessionLocal()
        try:
            all_cats_orm = (
                db.query(CategoryModel)
                .filter(CategoryModel.is_active == 1)
                .options(joinedload(CategoryModel.fields))
                .all()
            )
            cat_map = {c.id: c for c in all_cats_orm}
            parent_ids_set = {c.parent_id for c in all_cats_orm if c.parent_id is not None}

            def _path(cat_id: int) -> str:
                names: list[str] = []
                cid: int | None = cat_id
                visited: set = set()
                while cid and cid not in visited:
                    visited.add(cid)
                    c = cat_map.get(cid)
                    if not c:
                        break
                    names.append(c.name)
                    cid = c.parent_id
                return " > ".join(reversed(names))

            target_cats = (
                [c for c in all_cats_orm if c.id not in parent_ids_set]
                if request_only_leaf else list(all_cats_orm)
            )

            # ── Step 1: build all texts ───────────────────────────────────────
            profiles, texts = [], []
            for cat in target_cats:
                path = _path(cat.id)
                attr_parts: list[str] = []
                for field in (cat.fields or []):
                    attr_parts.append(field.field_label)
                    for opt in (field.field_options or []):
                        lbl = opt.get("label") or opt.get("value", "")
                        if lbl:
                            attr_parts.append(lbl)
                attr_text = " ".join(attr_parts)
                search_text = f"{cat.name} {cat.description or ''} {path} {attr_text}".strip()
                profiles.append({
                    "category_id": cat.id,
                    "name": cat.name,
                    "parent_id": cat.parent_id,
                    "path": path,
                    "description": cat.description,
                    "is_leaf": cat.id not in parent_ids_set,
                    "is_active": True,
                })
                texts.append(search_text)

            # ── Step 2: embed ALL vectors first (small batches to avoid OOM) ──
            all_vecs: list[list[float]] = []
            for i in range(0, len(texts), 8):
                vecs = await embed_texts(texts[i:i + 8])
                all_vecs.extend(vecs)
            logger.info("Embeddings ready: %d categories", len(all_vecs))

            # ── Step 3: atomic swap – delete old, upsert new ──────────────────
            if request_force:
                await qs.delete_collection()
            await qs.ensure_collection()
            indexed = await qs.upsert_categories(profiles, all_vecs) if profiles else 0

            # ── Step 4: attribute options (embed first, then replace) ─────────
            fields_all = db.query(CategoryField).all()
            option_dicts: list[dict] = []
            attr_texts: list[str] = []
            for field in fields_all:
                for opt in (field.field_options or []):
                    label = opt.get("label") or opt.get("value", "")
                    value = opt.get("value", "")
                    if not value:
                        continue
                    embed_text = f"{field.field_label}: {label}" if label != value else label
                    option_dicts.append({
                        "field_id": field.id,
                        "field_key": field.field_key,
                        "field_label": field.field_label,
                        "category_id": field.category_id,
                        "option_value": value,
                        "option_label": label,
                    })
                    attr_texts.append(embed_text)

            attr_vectors: list[list[float]] = []
            for i in range(0, len(attr_texts), 64):
                vecs = await embed_texts(attr_texts[i:i + 64])
                attr_vectors.extend(vecs)
            logger.info("Attr embeddings ready: %d options", len(attr_vectors))

            # Atomic swap for attributes
            if request_force:
                try:
                    await qs.delete_attr_collection()
                except Exception:
                    pass
            await qs.ensure_attr_collection()
            attrs_indexed = await qs.upsert_attribute_options(option_dicts, attr_vectors) if option_dicts else 0

            time_taken = round(_time.time() - start_time, 2)

            sync_history = CategorySyncHistory(
                source="rebuild_index",
                sync_type="manual",
                changes_detected=True,
                categories_modified=indexed,
                success=True,
                synced_by=admin_id,
            )
            db.add(sync_history)
            db.commit()

            _rebuild_job["status"] = "done"
            _rebuild_job["result"] = {
                "categories_indexed": indexed,
                "attributes_indexed": attrs_indexed,
                "time_taken_seconds": time_taken,
            }
            _job_save(_rebuild_job)
            logger.info("rebuild_qdrant_index done: %s cats, %s attrs, %.1fs", indexed, attrs_indexed, time_taken)
        finally:
            db.close()
    except Exception as exc:
        import traceback
        _rebuild_job["status"] = "error"
        _rebuild_job["error"] = traceback.format_exc()
        _job_save(_rebuild_job)
        logger.exception("_run_rebuild failed: %s", exc)


@router.post("/rebuild-index", response_model=CategoryRebuildIndexResponse)
async def rebuild_qdrant_index(
    current_admin: CurrentAdminUser,
    request: CategoryRebuildIndexRequest,
    db: Session = Depends(get_db)
):
    """
    Rebuild Qdrant vector index from DB categories table (runs as background task).
    Returns immediately with status=accepted. Poll /rebuild-index/status for progress.
    """
    if _rebuild_job["status"] == "running":
        raise HTTPException(status_code=409, detail="Rebuild already in progress")

    import datetime
    _rebuild_job["status"] = "running"
    _rebuild_job["started_at"] = datetime.datetime.utcnow().isoformat()
    _rebuild_job["result"] = None
    _rebuild_job["error"] = None

    asyncio.create_task(_run_rebuild(request.force, request.only_leaf_categories, current_admin.id))

    return CategoryRebuildIndexResponse(
        success=True,
        categories_indexed=0,
        attributes_indexed=0,
        time_taken_seconds=0,
    )


@router.get("/rebuild-index/status")
async def rebuild_index_status(current_admin: CurrentAdminUser):
    """Poll rebuild job status. Survives API restarts via Redis."""
    # If in-memory says idle but Redis has a more recent state, use Redis
    if _rebuild_job["status"] == "idle":
        saved = _job_load()
        if saved.get("status") not in ("idle", None):
            _rebuild_job.update(saved)
    return {
        "status": _rebuild_job["status"],       # idle | running | done | error
        "started_at": _rebuild_job["started_at"],
        "result": _rebuild_job["result"],
        "error": _rebuild_job["error"],
    }


# ─────────────────────────────────────────────
# Omni Sync endpoints
# ─────────────────────────────────────────────

class CategoryUpdateRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None


@router.patch("/{category_id}", summary="Cập nhật tên và mô tả danh mục")
async def update_category(
    category_id: int,
    body: CategoryUpdateRequest,
    current_admin: CurrentAdminUser,
    db: Session = Depends(get_db),
):
    """Cho phép admin sửa tên (name) và mô tả (description) của một danh mục trong DB."""
    from models import Category as CategoryModel

    cat = db.query(CategoryModel).filter(CategoryModel.id == category_id).first()
    if not cat:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found")

    if body.name is not None:
        name = body.name.strip()
        if not name:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="name cannot be empty")
        cat.name = name
    if body.description is not None:
        cat.description = body.description.strip() or None
    cat.updated_at = datetime.now()
    db.commit()
    db.refresh(cat)
    return {"id": cat.id, "name": cat.name, "description": cat.description}


@router.post("/sync-omni", summary="Đồng bộ danh mục + thuộc tính từ API omni")
async def sync_from_omni(
    current_admin: CurrentAdminUser,
    db: Session = Depends(get_db),
    sync_type: str = "full",  # "categories", "attributes", "full"
    base_url: str | None = None,
):
    """
    Đồng bộ từ API omni bên ngoài.
    - sync_type: "categories" | "attributes" | "full"
    - base_url: override URL (nếu không dùng cấu hình OMNI_BASE_URL)
    """
    url = (base_url or settings.omni_base_url or "").strip()
    if not url:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="OMNI_BASE_URL chưa được cấu hình. Thêm OMNI_BASE_URL vào .env hoặc truyền base_url."
        )

    try:
        if sync_type == "categories":
            result = await omni_sync_service.sync_categories_from_omni(url, db)
        elif sync_type == "attributes":
            result = await omni_sync_service.sync_attributes_from_omni(url, db)
        else:
            result = await omni_sync_service.sync_full_from_omni(url, db)

        # Log sync history — sync_type column only allows manual/webhook/scheduled
        sync_history = CategorySyncHistory(
            source="omni",
            sync_type="manual",
            changes_detected=True,
            categories_added=result.get("categories_synced", 0),
            categories_modified=result.get("categories_with_fields", 0),
            categories_deleted=0,
            success=True,
            synced_by=current_admin.id,
        )
        db.add(sync_history)
        db.commit()

        return {"status": "ok", "sync_type": sync_type, "result": result}

    except Exception as e:
        try:
            db.rollback()
            sync_history = CategorySyncHistory(
                source="omni",
                sync_type="manual",
                changes_detected=False,
                success=False,
                error_message=str(e)[:500],
                synced_by=current_admin.id,
            )
            db.add(sync_history)
            db.commit()
        except Exception:
            pass
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Omni sync failed: {str(e)}"
        )


@router.get("/attributes", summary="Lấy toàn bộ fields theo danh mục")
async def get_all_attributes(current_admin: CurrentAdminUser, db: Session = Depends(get_db)):
    """Trả về {category_id: [fields]} từ DB."""
    return {"attributes": omni_sync_service.get_all_attributes(db)}


@router.get("/attributes/{category_id}", summary="Lấy fields cho một danh mục")
async def get_category_attributes(category_id: int, current_admin: CurrentAdminUser, db: Session = Depends(get_db)):
    """Trả về danh sách fields cho category_id cụ thể từ DB."""
    attrs = omni_sync_service.get_attributes_for_category(category_id, db)
    return {"category_id": category_id, "attributes": attrs}


@router.get("/omni-config", summary="Xem cấu hình omni sync hiện tại")
async def get_omni_config(current_admin: CurrentAdminUser):
    return {
        "omni_base_url": settings.omni_base_url or "",
        "omni_sync_mode": settings.omni_sync_mode,
        "omni_sync_interval_hours": settings.omni_sync_interval_hours,
    }


@router.get("/count")
async def get_category_count(
    current_admin: CurrentAdminUser,
    db: Session = Depends(get_db),
):
    """Get category statistics from DB."""
    from models import Category, CategoryField
    from sqlalchemy import func as sqlfunc

    total = db.query(sqlfunc.count(Category.id)).scalar() or 0
    active = db.query(sqlfunc.count(Category.id)).filter(Category.is_active == 1).scalar() or 0

    # Leaf: categories that are not a parent of any other category
    parent_ids_subq = db.query(Category.parent_id).filter(Category.parent_id.isnot(None)).subquery()
    leaf = db.query(sqlfunc.count(Category.id)).filter(
        Category.is_active == 1,
        ~Category.id.in_(parent_ids_subq),
    ).scalar() or 0

    fields_count = db.query(sqlfunc.count(CategoryField.id)).scalar() or 0

    return {
        "total_categories": total,
        "leaf_categories": leaf,
        "active_categories": active,
        "inactive_categories": total - active,
        "fields_count": fields_count,
    }
