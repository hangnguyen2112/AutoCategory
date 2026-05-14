"""
Pydantic schemas for training data
"""
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List
from datetime import datetime


class TrainingDataBase(BaseModel):
    """Base training data schema"""
    title: str = Field(..., min_length=1)
    description: Optional[str] = None
    price: Optional[float] = None
    image_urls: Optional[List[str]] = None


class TrainingDataCreate(TrainingDataBase):
    """Schema for creating training data"""
    actual_category_id: int
    actual_category_name: Optional[str] = None
    actual_category_path: Optional[str] = None
    
    predicted_category_id: Optional[int] = None
    predicted_confidence: Optional[float] = None
    predicted_decision: Optional[str] = None
    
    llm_reason: Optional[str] = None
    understanding_output: Optional[str] = None
    
    source: str = Field(default="manual", pattern="^(feedback|manual|import|generated)$")
    quality_score: Optional[float] = Field(None, ge=0, le=1)


class TrainingDataUpdate(BaseModel):
    """Schema for updating training data"""
    actual_category_id: Optional[int] = None
    actual_category_name: Optional[str] = None
    actual_category_path: Optional[str] = None
    is_validated: Optional[bool] = None
    validation_notes: Optional[str] = None
    quality_score: Optional[float] = Field(None, ge=0, le=1)


class TrainingDataResponse(TrainingDataBase):
    """Schema for training data response"""
    id: int
    
    # Prediction
    predicted_category_id: Optional[int]
    predicted_category_name: Optional[str]
    predicted_category_path: Optional[str]
    predicted_confidence: Optional[float]
    predicted_decision: Optional[str]
    
    # Ground truth
    actual_category_id: int
    actual_category_name: Optional[str]
    actual_category_path: Optional[str]
    
    # LLM reasoning
    llm_reason: Optional[str]
    understanding_output: Optional[str]
    
    # Source and validation
    source: str
    is_validated: bool
    validation_notes: Optional[str]
    quality_score: Optional[float]
    
    # Metadata
    user_id: Optional[int]
    request_log_id: Optional[int]
    created_at: datetime
    validated_at: Optional[datetime]
    validated_by: Optional[int]
    
    model_config = ConfigDict(from_attributes=True)


class TrainingDataFilter(BaseModel):
    """Schema for filtering training data"""
    source: Optional[str] = None
    is_validated: Optional[bool] = None
    actual_category_id: Optional[int] = None
    predicted_category_id: Optional[int] = None
    min_quality_score: Optional[float] = None
    max_quality_score: Optional[float] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None


class TrainingDataStats(BaseModel):
    """Schema for training data statistics"""
    total_samples: int
    validated_samples: int
    validation_rate: float
    samples_by_source: dict
    samples_by_category: dict
    avg_quality_score: float
    ready_for_training: bool
