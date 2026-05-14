"""
Category router: list categories và fields từ DB.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database import get_db
from models import Category, CategoryField
from services.omni_sync_service import get_attributes_for_category
from services.llm_service import suggest_field_values

router = APIRouter()


class SuggestFieldsRequest(BaseModel):
    title: str
    description: str | None = None


def _build_path(cat_id: int, cat_map: dict) -> str:
    names: list[str] = []
    current_id: int | None = cat_id
    visited: set = set()
    while current_id and current_id not in visited:
        visited.add(current_id)
        cat = cat_map.get(current_id)
        if not cat:
            break
        names.append(cat.name)
        current_id = cat.parent_id
    return " > ".join(reversed(names))


@router.get("/categories", summary="Danh sách tất cả danh mục")
async def list_categories(db: Session = Depends(get_db)):
    from sqlalchemy import func
    categories = db.query(Category).filter(Category.is_active == 1).all()
    cat_map = {c.id: c for c in categories}
    # Count fields per category
    field_counts = {
        row[0]: row[1]
        for row in db.query(CategoryField.category_id, func.count(CategoryField.id))
                      .group_by(CategoryField.category_id).all()
    }
    profiles = [
        {
            "category_id": c.id,
            "name": c.name,
            "parent_id": c.parent_id,
            "path": _build_path(c.id, cat_map),
            "description": c.description,
            "image": c.image,
            "fields_count": field_counts.get(c.id, 0),
        }
        for c in categories
    ]
    return {"categories": profiles}


@router.get("/categories/leaves", summary="Chỉ leaf categories")
async def list_leaf_categories(db: Session = Depends(get_db)):
    categories = db.query(Category).filter(Category.is_active == 1).all()
    cat_map = {c.id: c for c in categories}
    parent_ids = {c.parent_id for c in categories if c.parent_id is not None}
    leaves = [c for c in categories if c.id not in parent_ids]
    profiles = [
        {
            "category_id": c.id,
            "name": c.name,
            "parent_id": c.parent_id,
            "path": _build_path(c.id, cat_map),
            "description": c.description,
            "is_leaf": True,
            "is_active": True,
        }
        for c in leaves
    ]
    return {"categories": profiles, "count": len(profiles)}


@router.get("/categories/{category_id}/attributes", summary="Thuộc tính của một danh mục")
async def get_attributes(category_id: int, db: Session = Depends(get_db)):
    """Lấy danh sách fields cần điền khi đăng trong danh mục này."""
    attrs = get_attributes_for_category(category_id, db)
    return {"category_id": category_id, "attributes": attrs}


@router.post("/categories/{category_id}/suggest-fields", summary="AI gợi ý giá trị fields")
async def suggest_fields(
    category_id: int,
    body: SuggestFieldsRequest,
    db: Session = Depends(get_db),
):
    """Dùng AI để gợi ý giá trị phù hợp cho các fields của danh mục dựa vào thông tin sản phẩm."""
    attrs = get_attributes_for_category(category_id, db)
    if not attrs:
        return {"category_id": category_id, "suggestions": {}}
    suggestions = await suggest_field_values(
        title=body.title,
        description=body.description or "",
        fields=attrs,
    )
    return {"category_id": category_id, "suggestions": suggestions}

