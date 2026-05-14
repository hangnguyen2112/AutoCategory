"""
Training data management endpoints (Admin only)
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from typing import Optional
from datetime import datetime

from database import get_db
from models import TrainingData, User
from schemas.training_data import (
    TrainingDataCreate,
    TrainingDataUpdate,
    TrainingDataResponse,
    TrainingDataStats,
)
from dependencies import CurrentAdminUser, CurrentDeveloperOrAdminUser

router = APIRouter(prefix="/api/admin/training-data", tags=["Admin - Training Data"])


@router.get("", response_model=list[TrainingDataResponse])
async def list_training_data(
    current_user: CurrentDeveloperOrAdminUser,
    db: Session = Depends(get_db),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    source: Optional[str] = None,
    is_validated: Optional[bool] = None,
    actual_category_id: Optional[int] = None,
    min_quality_score: Optional[float] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
):
    """
    List training data with filtering
    """
    query = db.query(TrainingData)
    
    # Apply filters
    if source:
        query = query.filter(TrainingData.source == source)
    
    if is_validated is not None:
        query = query.filter(TrainingData.is_validated == is_validated)
    
    if actual_category_id:
        query = query.filter(TrainingData.actual_category_id == actual_category_id)
    
    if min_quality_score is not None:
        query = query.filter(TrainingData.quality_score >= min_quality_score)
    
    if start_date:
        query = query.filter(TrainingData.created_at >= start_date)
    
    if end_date:
        query = query.filter(TrainingData.created_at <= end_date)
    
    # Order by created_at descending
    query = query.order_by(desc(TrainingData.created_at))
    
    # Paginate
    data = query.offset(skip).limit(limit).all()
    
    return [TrainingDataResponse.model_validate(item) for item in data]


@router.post("", response_model=TrainingDataResponse)
async def create_training_data(
    data: TrainingDataCreate,
    current_admin: CurrentAdminUser,
    db: Session = Depends(get_db)
):
    """
    Manually create training data
    """
    training_data = TrainingData(
        title=data.title,
        description=data.description,
        price=data.price,
        image_urls=data.image_urls,
        predicted_category_id=data.predicted_category_id,
        predicted_confidence=data.predicted_confidence,
        predicted_decision=data.predicted_decision,
        actual_category_id=data.actual_category_id,
        actual_category_name=data.actual_category_name,
        actual_category_path=data.actual_category_path,
        llm_reason=data.llm_reason,
        understanding_output=data.understanding_output,
        source=data.source,
        quality_score=data.quality_score,
        user_id=current_admin.id
    )
    
    db.add(training_data)
    db.commit()
    db.refresh(training_data)
    
    return TrainingDataResponse.model_validate(training_data)


@router.get("/{data_id}", response_model=TrainingDataResponse)
async def get_training_data(
    data_id: int,
    current_user: CurrentDeveloperOrAdminUser,
    db: Session = Depends(get_db)
):
    """
    Get training data by ID
    """
    data = db.query(TrainingData).filter(TrainingData.id == data_id).first()
    
    if not data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Training data not found"
        )
    
    return TrainingDataResponse.model_validate(data)


@router.patch("/{data_id}", response_model=TrainingDataResponse)
async def update_training_data(
    data_id: int,
    update_data: TrainingDataUpdate,
    current_admin: CurrentAdminUser,
    db: Session = Depends(get_db)
):
    """
    Update training data (e.g., validate, correct category)
    """
    data = db.query(TrainingData).filter(TrainingData.id == data_id).first()
    
    if not data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Training data not found"
        )
    
    # Update fields
    update_dict = update_data.model_dump(exclude_unset=True)
    for field, value in update_dict.items():
        setattr(data, field, value)
    
    # If validating, set validated_at and validated_by
    if update_data.is_validated is True:
        data.validated_at = datetime.utcnow()
        data.validated_by = current_admin.id
    
    db.commit()
    db.refresh(data)
    
    return TrainingDataResponse.model_validate(data)


@router.delete("/{data_id}")
async def delete_training_data(
    data_id: int,
    current_admin: CurrentAdminUser,
    db: Session = Depends(get_db)
):
    """
    Delete training data
    """
    data = db.query(TrainingData).filter(TrainingData.id == data_id).first()
    
    if not data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Training data not found"
        )
    
    db.delete(data)
    db.commit()
    
    return {"message": f"Training data {data_id} deleted successfully"}


@router.get("/stats/overview", response_model=TrainingDataStats)
async def get_training_data_stats(
    current_user: CurrentDeveloperOrAdminUser,
    db: Session = Depends(get_db)
):
    """
    Get training data statistics
    """
    # Total samples
    total_samples = db.query(TrainingData).count()
    
    # Validated samples
    validated_samples = db.query(TrainingData).filter(
        TrainingData.is_validated == True
    ).count()
    
    validation_rate = (validated_samples / total_samples * 100) if total_samples > 0 else 0
    
    # Samples by source
    source_stats = db.query(
        TrainingData.source,
        func.count(TrainingData.id).label('count')
    ).group_by(TrainingData.source).all()
    
    samples_by_source = {source: count for source, count in source_stats}
    
    # Samples by category (top 10)
    category_stats = db.query(
        TrainingData.actual_category_name,
        func.count(TrainingData.id).label('count')
    ).filter(
        TrainingData.actual_category_name.isnot(None)
    ).group_by(TrainingData.actual_category_name).order_by(desc('count')).limit(10).all()
    
    samples_by_category = {name: count for name, count in category_stats}
    
    # Average quality score
    avg_quality_result = db.query(
        func.avg(TrainingData.quality_score)
    ).filter(TrainingData.quality_score.isnot(None)).scalar()
    
    avg_quality_score = float(avg_quality_result) if avg_quality_result else 0
    
    # Ready for training if we have at least 100 validated samples
    ready_for_training = validated_samples >= 100
    
    return TrainingDataStats(
        total_samples=total_samples,
        validated_samples=validated_samples,
        validation_rate=round(validation_rate, 2),
        samples_by_source=samples_by_source,
        samples_by_category=samples_by_category,
        avg_quality_score=round(avg_quality_score, 2),
        ready_for_training=ready_for_training
    )


@router.post("/bulk-validate")
async def bulk_validate_training_data(
    current_admin: CurrentAdminUser,
    db: Session = Depends(get_db),
    data_ids: list[int] = Query(...),
    validation_notes: Optional[str] = None
):
    """
    Bulk validate multiple training data samples
    """
    updated_count = 0
    
    for data_id in data_ids:
        data = db.query(TrainingData).filter(TrainingData.id == data_id).first()
        if data:
            data.is_validated = True
            data.validated_at = datetime.utcnow()
            data.validated_by = current_admin.id
            if validation_notes:
                data.validation_notes = validation_notes
            updated_count += 1
    
    db.commit()
    
    return {
        "message": f"Validated {updated_count} training data samples",
        "validated_ids": data_ids[:updated_count]
    }
