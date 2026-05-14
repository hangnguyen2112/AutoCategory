"""
Omni Sync Service – đồng bộ danh mục & fields từ API omni → PostgreSQL DB.
"""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

import httpx
from sqlalchemy.orm import Session

from models import Category, CategoryField

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────

def _flatten_categories(
    nested: list[dict],
    result: list[dict],
    parent_id: int | None = None,
) -> None:
    for cat in nested:
        result.append({
            "id": cat["id"],
            "name": cat["name"],
            "slug": cat.get("slug", ""),
            "description": cat.get("name", ""),
            "icon": cat.get("icon") or "fas fa-folder",
            "image": cat.get("image"),
            "parent_id": cat.get("parent_id") or parent_id,
            "sort_order": 0,
            "is_featured": 1 if cat.get("is_featured") else 0,
            "is_home_cheap": 0,
            "is_active": 1,
        })
        children = cat.get("children") or []
        if children:
            _flatten_categories(children, result, parent_id=cat["id"])


# ─────────────────────────────────────────────
# DB read helpers (thay thế JSON helpers cũ)
# ─────────────────────────────────────────────

def get_attributes_for_category(category_id: int, db: Session) -> list[dict]:
    """Trả về danh sách fields cho một category từ DB."""
    fields = (
        db.query(CategoryField)
        .filter(CategoryField.category_id == category_id)
        .order_by(CategoryField.sort_order)
        .all()
    )
    return [_field_to_dict(f) for f in fields]


def get_all_attributes(db: Session) -> dict[str, list]:
    """Trả về toàn bộ {category_id: [fields]} từ DB."""
    fields = db.query(CategoryField).order_by(CategoryField.category_id, CategoryField.sort_order).all()
    result: dict[str, list] = {}
    for f in fields:
        key = str(f.category_id)
        result.setdefault(key, []).append(_field_to_dict(f))
    return result


def _field_to_dict(f: CategoryField) -> dict:
    return {
        "id": f.id,
        "field_key": f.field_key,
        "field_label": f.field_label,
        "field_type": f.field_type,
        "field_options": f.field_options or [],
        "is_required": f.is_required,
        "is_featured": f.is_featured,
        "parent_field_id": f.parent_field_id,
        "parent_field_value": f.parent_field_value,
        "sort_order": f.sort_order,
    }


# ─────────────────────────────────────────────
# Sync functions — ghi vào DB
# ─────────────────────────────────────────────

async def sync_categories_from_omni(base_url: str, db: Session) -> dict[str, Any]:
    """
    Gọi GET {base_url}/api/v1/app/categories, flatten và upsert vào bảng categories.
    """
    url = f"{base_url.rstrip('/')}/api/v1/app/categories"
    logger.info(f"Syncing categories from {url}")

    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.get(url)
        resp.raise_for_status()
        data = resp.json()

    nested_categories: list[dict] = data.get("data", [])
    flat_categories: list[dict] = []
    _flatten_categories(nested_categories, flat_categories)

    # Upsert categories vào DB (INSERT ON CONFLICT UPDATE)
    existing_ids = {row.id for row in db.query(Category.id).all()}
    now = datetime.utcnow()

    for cat in flat_categories:
        if cat["id"] in existing_ids:
            db.query(Category).filter(Category.id == cat["id"]).update({
                "name": cat["name"],
                "slug": cat["slug"],
                "description": cat["description"],
                "icon": cat["icon"],
                "image": cat["image"],
                "parent_id": cat["parent_id"],
                "sort_order": cat["sort_order"],
                "is_featured": cat["is_featured"],
                "is_home_cheap": cat["is_home_cheap"],
                "is_active": cat["is_active"],
                "updated_at": now,
            }, synchronize_session=False)
        else:
            db.add(Category(
                id=cat["id"],
                name=cat["name"],
                slug=cat["slug"],
                description=cat["description"],
                icon=cat["icon"],
                image=cat["image"],
                parent_id=cat["parent_id"],
                sort_order=cat["sort_order"],
                is_featured=cat["is_featured"],
                is_home_cheap=cat["is_home_cheap"],
                is_active=cat["is_active"],
                created_at=now,
                updated_at=now,
            ))

    db.commit()
    logger.info(f"Synced {len(flat_categories)} categories to DB")
    return {
        "categories_synced": len(flat_categories),
        "synced_at": datetime.now().isoformat(),
    }


async def sync_attributes_from_omni(
    base_url: str,
    db: Session,
    category_ids: list[int] | None = None,
) -> dict[str, Any]:
    """
    Gọi GET {base_url}/api/v1/app/categories/{id}/fields cho từng category.
    Response: { data: { category: {...}, fields: [{id, field_key, field_label, field_type,
               field_options, is_required, is_featured, parent_field_id, parent_field_value}] } }
    Upsert vào bảng category_fields.
    """
    if not category_ids:
        category_ids = [row.id for row in db.query(Category.id).filter(Category.is_active == 1).all()]

    base = base_url.rstrip("/")
    success_count = 0

    async with httpx.AsyncClient(timeout=30.0) as client:
        for cat_id in category_ids:
            try:
                resp = await client.get(f"{base}/api/v1/app/categories/{cat_id}/fields")
                if resp.status_code != 200:
                    continue
                d = resp.json()
                fields: list[dict] = d.get("data", {}).get("fields", [])
                if not fields:
                    continue

                # Xóa fields cũ của category này rồi insert lại
                db.query(CategoryField).filter(CategoryField.category_id == cat_id).delete()
                for idx, f in enumerate(fields):
                    db.add(CategoryField(
                        category_id=cat_id,
                        field_key=f.get("field_key", ""),
                        field_label=f.get("field_label", ""),
                        field_type=f.get("field_type", "text"),
                        field_options=f.get("field_options") or [],
                        is_required=bool(f.get("is_required", False)),
                        is_featured=bool(f.get("is_featured", False)),
                        parent_field_id=f.get("parent_field_id"),
                        parent_field_value=f.get("parent_field_value"),
                        sort_order=f.get("sort_order", idx),
                    ))
                success_count += 1
            except Exception as e:
                logger.debug(f"No fields for category {cat_id}: {e}")

    db.commit()
    logger.info(f"Synced fields for {success_count}/{len(category_ids)} categories")
    return {
        "categories_checked": len(category_ids),
        "categories_with_fields": success_count,
        "synced_at": datetime.now().isoformat(),
    }


async def sync_full_from_omni(base_url: str, db: Session) -> dict[str, Any]:
    """Full sync: categories + fields."""
    cat_result = await sync_categories_from_omni(base_url, db)
    category_ids = [row.id for row in db.query(Category.id).filter(Category.is_active == 1).all()]
    attr_result = await sync_attributes_from_omni(base_url, db, category_ids)
    return {**cat_result, **attr_result}
