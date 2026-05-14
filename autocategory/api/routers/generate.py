"""
Generate router: Auto-generate content from images for rao vặt.

3 modes:
  1. POST /generate/from-images  – AI đọc ảnh → sinh tiêu đề + danh mục + thuộc tính
  2. POST /generate/from-text    – Từ tiêu đề + mô tả → phân loại danh mục + thuộc tính
  3. POST /generate/full         – Ảnh + tiêu đề + mô tả → phân tích đầy đủ
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from database import get_db
from services import classifier, image_analyzer
from services.omni_sync_service import get_attributes_for_category

router = APIRouter()


# ─────────────────────────────────────────────
# Request/Response models
# ─────────────────────────────────────────────

class GenerateFromImagesRequest(BaseModel):
    image_urls: list[str] = Field(..., min_length=1, max_length=5)
    existing_title: str = Field(default="")
    existing_description: str = Field(default="")
    generate_category: bool = Field(default=True)


class GenerateFromTextRequest(BaseModel):
    title: str = Field(default="", max_length=500)
    description: str = Field(default="", max_length=5000)
    price: float | None = Field(default=None, ge=0)


class GenerateFullRequest(BaseModel):
    image_urls: list[str] = Field(..., min_length=1, max_length=5)
    title: str = Field(default="", max_length=500)
    description: str = Field(default="", max_length=5000)
    price: float | None = Field(default=None, ge=0)


class ValidateConsistencyRequest(BaseModel):
    title: str = Field(..., min_length=1)
    description: str = Field(default="")
    image_urls: list[str] = Field(..., min_length=1, max_length=5)


# ─────────────────────────────────────────────
# Helper
# ─────────────────────────────────────────────

def _attach_attributes(result: dict, category_result: dict, db: Session) -> dict:
    """Gắn category suggestion + attribute definitions vào result."""
    selected = category_result.get("selected_category") or {}
    rerank = category_result.get("rerank") or {}

    category_id = selected.get("category_id") or rerank.get("category_id")
    attributes = get_attributes_for_category(int(category_id), db) if category_id else []

    result["category_suggestion"] = {
        "category_id": category_id,
        "category_name": selected.get("name") or rerank.get("category_name"),
        "category_path": selected.get("path") or rerank.get("category_path"),
        "confidence": rerank.get("confidence"),
        "decision": category_result.get("decision"),
        "attributes": attributes,
    }
    return result


# ─────────────────────────────────────────────
# Endpoints
# ─────────────────────────────────────────────

@router.post("/generate/from-images", summary="[Nút 1] AI đọc ảnh → sinh tiêu đề + danh mục + thuộc tính")
async def generate_from_images(req: GenerateFromImagesRequest, db: Session = Depends(get_db)):
    """
    Mode 1: Chỉ cần ảnh – AI tự sinh tiêu đề, mô tả, đề xuất danh mục và thuộc tính.
    """
    try:
        result = await image_analyzer.generate_from_images(
            image_urls=req.image_urls,
            existing_title=req.existing_title,
            existing_description=req.existing_description,
        )

        if req.generate_category:
            category_result = await classifier.classify_product(
                title=result.get("title", ""),
                description=result.get("description", ""),
                price=result.get("price_suggestion", {}).get("estimate") if result.get("price_suggestion") else None,
                image_urls=req.image_urls,
                fast=False,
            )
            _attach_attributes(result, category_result, db)

        return {"status": "ok", "mode": "from_images", "generated": result}

    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/generate/from-text", summary="[Nút 2] Tiêu đề + mô tả → phân loại danh mục + thuộc tính")
async def generate_from_text(req: GenerateFromTextRequest, db: Session = Depends(get_db)):
    """
    Mode 2: Từ tiêu đề + mô tả – phân loại danh mục và trả về thuộc tính cần điền.
    """
    try:
        category_result = await classifier.classify_product(
            title=req.title,
            description=req.description,
            price=req.price,
            fast=False,
        )

        selected = category_result.get("selected_category") or {}
        rerank = category_result.get("rerank") or {}
        category_id = selected.get("category_id") or rerank.get("category_id")
        attributes = get_attributes_for_category(int(category_id), db) if category_id else []

        return {
            "status": "ok",
            "mode": "from_text",
            "category_suggestion": {
                "category_id": category_id,
                "category_name": selected.get("name") or rerank.get("category_name"),
                "category_path": selected.get("path") or rerank.get("category_path"),
                "confidence": rerank.get("confidence"),
                "decision": category_result.get("decision"),
                "llm_reason": category_result.get("llm_reason") or rerank.get("reason"),
                "attributes": attributes,
            },
            "candidates": category_result.get("candidates", []),
        }

    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/generate/full", summary="[Nút 3] Ảnh + tiêu đề + mô tả → phân tích đầy đủ")
async def generate_full(req: GenerateFullRequest, db: Session = Depends(get_db)):
    """
    Mode 3: Kết hợp ảnh + tiêu đề + mô tả – phân tích toàn diện.
    Nếu không có title, AI sinh từ ảnh trước rồi classify.
    """
    try:
        # Step 1: Luôn phân tích ảnh để sinh tiêu đề/mô tả AI (truyền nội dung hiện có làm gợi ý)
        image_generated = await image_analyzer.generate_from_images(
            image_urls=req.image_urls,
            existing_title=req.title,
            existing_description=req.description,
        )
        ai_title = image_generated.get("title") or req.title
        ai_description = image_generated.get("description") or req.description

        # Step 2: Classify với đầy đủ thông tin (AI + input người dùng)
        category_result = await classifier.classify_product(
            title=ai_title,
            description=ai_description,
            price=req.price,
            image_urls=req.image_urls,
            fast=False,
        )

        selected = category_result.get("selected_category") or {}
        rerank = category_result.get("rerank") or {}
        category_id = selected.get("category_id") or rerank.get("category_id")
        attributes = get_attributes_for_category(int(category_id), db) if category_id else []

        return {
            "status": "ok",
            "mode": "full",
            "generated": {
                "title": ai_title,
                "description": ai_description,
            },
            "image_analysis": image_generated,
            "category_suggestion": {
                "category_id": category_id,
                "category_name": selected.get("name") or rerank.get("category_name"),
                "category_path": selected.get("path") or rerank.get("category_path"),
                "confidence": rerank.get("confidence"),
                "decision": category_result.get("decision"),
                "llm_reason": category_result.get("llm_reason") or rerank.get("reason"),
                "attributes": attributes,
            },
            "candidates": category_result.get("candidates", []),
        }

    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/generate/validate-consistency", summary="Kiểm tra text vs ảnh có khớp không")
async def validate_consistency(req: ValidateConsistencyRequest):
    """
    Validate xem title + description có khớp với ảnh không.
    """
    try:
        result = await image_analyzer.validate_image_text_consistency(
            title=req.title,
            description=req.description,
            image_urls=req.image_urls,
        )
        return result

    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
