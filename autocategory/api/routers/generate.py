"""
Generate router: Auto-generate content from images for rao vặt.

3 modes:
  1. POST /generate/from-images  – AI đọc ảnh → sinh tiêu đề + danh mục + thuộc tính
  2. POST /generate/from-text    – Từ tiêu đề + mô tả → phân loại danh mục + thuộc tính
  3. POST /generate/full         – Ảnh + tiêu đề + mô tả → phân tích đầy đủ
  4. POST /generate/stream       – SSE streaming: image → classification → attributes
"""
from __future__ import annotations

import json
import logging

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from database import get_db
from dependencies import require_api_key
from models import APIKey
from services import attribute_selector, classifier, image_analyzer
from services.llm_service import suggest_field_values, understand_product
from services.omni_sync_service import get_attributes_for_category

logger = logging.getLogger(__name__)
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


class GenerateStreamRequest(BaseModel):
    image_urls: list[str] = Field(default_factory=list, max_length=5)
    title: str = Field(default="", max_length=500)
    description: str = Field(default="", max_length=5000)
    price: float | None = Field(default=None, ge=0)
    full: bool = Field(default=False, description="True = dùng LLM suggest-fields thay vì Qdrant")


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


@router.post("/generate/from-text", summary="[Nút 2] Tiêu đề + mô tả → phân loại danh mục + thuộc tính + gợi ý nội dung")
async def generate_from_text(req: GenerateFromTextRequest, db: Session = Depends(get_db)):
    """
    Mode 2: Từ tiêu đề + mô tả – phân loại danh mục, trả về thuộc tính cần điền
    và đề xuất tiêu đề/mô tả được cải thiện (không cần ảnh).
    """
    try:
        # Gợi ý tiêu đề & mô tả dựa trên text (không cần ảnh)
        understanding = await understand_product(
            title=req.title,
            description=req.description,
            price=req.price,
        )
        suggested_title = understanding.get("suggested_title") or req.title
        suggested_description = understanding.get("suggested_description") or req.description

        # Phân loại dùng text đã được chuẩn hoá
        classify_title = understanding.get("normalized_product_text") or suggested_title or req.title
        category_result = await classifier.classify_product(
            title=classify_title,
            description=suggested_description or req.description,
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
            "suggested": {
                "title": suggested_title,
                "description": suggested_description,
                "confidence": understanding.get("confidence"),
            },
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
async def generate_full(req: GenerateFullRequest, db: Session = Depends(get_db), api_key: APIKey = Depends(require_api_key)):
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


# ── SSE helpers ───────────────────────────────────────────────────────────────

def _sse(data: dict) -> str:
    """Format một SSE event."""
    return f"data: {json.dumps(data, ensure_ascii=False)}\n\n"


# ── Streaming endpoint ────────────────────────────────────────────────────────

@router.post(
    "/generate/stream",
    summary="[Streaming] Phân tích ảnh → phân loại → thuộc tính (SSE)",
    response_class=StreamingResponse,
)
async def generate_stream(req: GenerateStreamRequest, db: Session = Depends(get_db), api_key: APIKey = Depends(require_api_key)):
    """
    Streaming pipeline qua Server-Sent Events (SSE).

    Thứ tự events trả về:
    1. `analyzing_image`   – bắt đầu phân tích ảnh
    2. `image_analysis`    – kết quả: title, description, detected_attributes, price_suggestion
    3. `classifying`       – bắt đầu phân loại
    4. `classification`    – kết quả: category, candidates
    5. `loading_attributes`– bắt đầu load thuộc tính
    6. `attributes`        – kết quả: danh sách trường cần điền
    7. `done`              – hoàn tất

    Khi có lỗi: `error` event với `stage` và `message`.
    Frontend kết nối bằng fetch() + ReadableStream, KHÔNG dùng EventSource (POST body).
    """

    async def event_gen():
        title = req.title.strip()
        description = req.description.strip()
        category_id: int | None = None
        detected_attributes: dict = {}

        # ── Step 1: Image analysis ────────────────────────────────────────
        if req.image_urls:
            yield _sse({"step": "analyzing_image", "message": "Đang phân tích ảnh…"})
            try:
                image_result = await image_analyzer.generate_from_images(
                    image_urls=req.image_urls,
                    existing_title=title,
                    existing_description=description,
                )
                title = (image_result.get("title") or title).strip()
                description = (image_result.get("description") or description).strip()
                detected_attributes = image_result.get("detected_attributes") or {}
                yield _sse({
                    "step": "image_analysis",
                    "title": title,
                    "description": description,
                    "detected_attributes": detected_attributes,
                    "price_suggestion": image_result.get("price_suggestion"),
                })
            except Exception as exc:
                logger.exception("generate_stream image_analysis error")
                yield _sse({"step": "error", "stage": "image_analysis", "message": str(exc)})
                return
        elif not title:
            yield _sse({"step": "error", "stage": "input", "message": "Cần ít nhất ảnh hoặc tiêu đề sản phẩm."})
            return
        else:
            # Không có ảnh nhưng có text → gợi ý tiêu đề/mô tả từ LLM
            yield _sse({"step": "analyzing_text", "message": "Đang phân tích nội dung để gợi ý tiêu đề và mô tả…"})
            try:
                text_result = await understand_product(
                    title=title,
                    description=description,
                    price=req.price,
                )
                title = (text_result.get("suggested_title") or title).strip()
                description = (text_result.get("suggested_description") or description).strip()
                yield _sse({
                    "step": "text_analysis",
                    "title": title,
                    "description": description,
                    "confidence": text_result.get("confidence"),
                })
            except Exception as exc:
                logger.exception("generate_stream text_analysis error")
                yield _sse({"step": "error", "stage": "text_analysis", "message": str(exc)})
                return

        # ── Step 2: Classification ────────────────────────────────────────
        yield _sse({"step": "classifying", "message": "Đang phân loại danh mục…"})
        try:
            cat_result = await classifier.classify_product(
                title=title,
                description=description,
                price=req.price,
                image_urls=req.image_urls if req.image_urls else None,
                fast=False,
            )
            selected = cat_result.get("selected_category") or {}
            rerank = cat_result.get("rerank") or {}
            category_id_raw = selected.get("category_id") or rerank.get("category_id")
            category_id = int(category_id_raw) if category_id_raw is not None else None
            yield _sse({
                "step": "classification",
                "category_id": category_id,
                "category_name": selected.get("name") or rerank.get("category_name"),
                "category_path": selected.get("path") or rerank.get("category_path"),
                "confidence": rerank.get("confidence"),
                "decision": cat_result.get("decision"),
                "llm_reason": cat_result.get("llm_reason") or rerank.get("reason"),
                "candidates": cat_result.get("candidates", [])[:5],
            })
        except Exception as exc:
            logger.exception("generate_stream classification error")
            yield _sse({"step": "error", "stage": "classification", "message": repr(exc)})
            return

        # ── Step 3: Attributes ────────────────────────────────────────────
        if category_id:
            yield _sse({"step": "loading_attributes", "message": "Đang tải thuộc tính…"})
            try:
                attributes = get_attributes_for_category(category_id, db)
                if req.full:
                    # AI Đầy đủ: LLM thấy toàn bộ options và chọn trực tiếp
                    selected_values = await suggest_field_values(
                        title=title,
                        description=description,
                        fields=attributes,
                    )
                else:
                    # Phân tích nhanh: Qdrant/hybrid
                    selected_values = await attribute_selector.select_attributes(
                        attributes=attributes,
                        title=title,
                        description=description,
                        detected_attributes=detected_attributes,
                    )
                yield _sse({
                    "step": "attributes",
                    "attributes": attributes,
                    "selected_values": selected_values,
                })
            except Exception as exc:
                logger.exception("generate_stream attributes error")
                yield _sse({"step": "error", "stage": "attributes", "message": str(exc)})

        yield _sse({"step": "done"})

    return StreamingResponse(
        event_gen(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )
