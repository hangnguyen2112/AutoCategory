"""
Classify router: nhận bài đăng, trả về kết quả phân loại.
"""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, HTTPException, Request, Depends
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field

from services import classifier
from database import get_db
from models import RequestLog, TrainingData, APIKey
from dependencies import CurrentUser, require_api_key

router = APIRouter()


class ClassifyRequest(BaseModel):
    title: str = Field(default="", max_length=500)
    description: str = Field(default="", max_length=5000)
    price: Optional[float] = Field(default=None, ge=0)
    image_urls: list[str] = Field(default_factory=list, max_length=5)
    fast: bool = Field(default=False, description="Bỏ qua LLM understand, chỉ dùng LLM rerank")


class FeedbackRequest(BaseModel):
    request_log_id: int = Field(..., description="ID của request log cần feedback")
    actual_category_id: int = Field(..., description="Category ID đúng theo user")
    actual_category_name: Optional[str] = Field(None, description="Tên category đúng")
    actual_category_path: Optional[str] = Field(None, description="Path của category đúng")
    note: Optional[str] = Field(None, max_length=500, description="Ghi chú thêm")


@router.post("/classify", summary="Phân loại danh mục cho bài đăng sản phẩm")
async def classify_post(
    req: ClassifyRequest, 
    request: Request,
    api_key: APIKey = Depends(require_api_key)
):
    """
    Phân loại danh mục cho bài đăng sản phẩm.
    
    Requires valid API key in X-API-Key header.
    Kết quả sẽ được log tự động bởi RequestLoggingMiddleware.
    """
    try:
        result = await classifier.classify_product(
            title=req.title,
            description=req.description,
            price=req.price,
            image_urls=req.image_urls if req.image_urls else None,
            fast=req.fast,
        )

        selected_category = result.get("selected_category") or {}
        rerank = result.get("rerank") or {}
        
        # Store classification result in request.state for middleware logging
        request.state.classification_result = {
            "input_title": req.title,
            "input_description": req.description,
            "predicted_category_id": selected_category.get("category_id") or rerank.get("category_id"),
            "predicted_category_name": selected_category.get("name"),
            "predicted_category_path": selected_category.get("path"),
            "confidence": rerank.get("confidence"),
            "decision": result.get("decision"),
            "llm_reason": result.get("llm_reason") or rerank.get("reason"),
            "understanding_output": str(result.get("understanding")) if result.get("understanding") else None,
            "api_key_id": api_key.id if api_key else None,
        }
        
        return result
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/classify/feedback", summary="Gửi feedback để sửa kết quả phân loại")
async def submit_feedback(
    feedback: FeedbackRequest,
    current_user: CurrentUser,
    db: Session = Depends(get_db)
):
    """
    Gửi feedback khi user sửa kết quả phân loại.
    
    Feedback này sẽ:
    1. Cập nhật request_log với actual_category_id
    2. Tạo training_data entry cho việc training model
    """
    # Get request log
    request_log = db.query(RequestLog).filter(
        RequestLog.id == feedback.request_log_id
    ).first()
    
    if not request_log:
        raise HTTPException(status_code=404, detail="Request log not found")
    
    # Check if already has feedback
    existing_training = db.query(TrainingData).filter(
        TrainingData.request_log_id == feedback.request_log_id
    ).first()
    
    if existing_training:
        raise HTTPException(
            status_code=400, 
            detail="This request already has feedback. Please update the existing training data."
        )
    
    # Update request log with actual category
    request_log.actual_category_id = feedback.actual_category_id
    request_log.was_corrected = (
        request_log.predicted_category_id != feedback.actual_category_id
    )
    
    # Create training data from this feedback
    training_data = TrainingData(
        title=request_log.input_title or "",
        description=request_log.input_description or "",
        price=None,  # Not stored in request_log
        image_urls=[],  # Not stored in request_log
        predicted_category_id=request_log.predicted_category_id,
        predicted_category_name=request_log.predicted_category_name,
        predicted_category_path=request_log.predicted_category_path,
        predicted_confidence=request_log.confidence,
        predicted_decision=request_log.decision,
        actual_category_id=feedback.actual_category_id,
        actual_category_name=feedback.actual_category_name,
        actual_category_path=feedback.actual_category_path,
        llm_reason=feedback.note,  # Store user note as llm_reason
        understanding_output=None,  # Not stored in request_log
        source="feedback",
        quality_score=1.0 if request_log.was_corrected else 0.8,
        user_id=current_user.id,
        request_log_id=request_log.id
    )
    
    db.add(training_data)
    db.commit()
    db.refresh(training_data)
    db.refresh(request_log)
    
    return {
        "message": "Feedback received successfully",
        "request_log_id": request_log.id,
        "training_data_id": training_data.id,
        "was_correction": request_log.was_corrected,
        "note": "This feedback will be used to improve the model"
    }
