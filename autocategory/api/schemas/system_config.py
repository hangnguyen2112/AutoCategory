"""
Pydantic schemas for system configuration
"""
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, Any
from datetime import datetime


class SystemConfigBase(BaseModel):
    """Base system config schema"""
    key: str = Field(..., min_length=1, max_length=255)
    value: str
    value_type: str = Field(default="string", pattern="^(string|int|float|bool|json)$")
    description: Optional[str] = None
    category: Optional[str] = None


class SystemConfigCreate(SystemConfigBase):
    """Schema for creating system config"""
    is_secret: bool = False
    is_active: bool = True


class SystemConfigUpdate(BaseModel):
    """Schema for updating system config"""
    value: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None


class SystemConfigResponse(SystemConfigBase):
    """Schema for system config response"""
    id: int
    is_secret: bool
    is_active: bool
    updated_by: Optional[int]
    created_at: datetime
    updated_at: datetime
    
    # Mask secret values
    def model_post_init(self, __context):
        if self.is_secret:
            self.value = "***SECRET***"
    
    model_config = ConfigDict(from_attributes=True)


class SystemConfigFilter(BaseModel):
    """Schema for filtering system config"""
    category: Optional[str] = None
    is_active: Optional[bool] = None
    search: Optional[str] = None


class SystemConfigBulkUpdate(BaseModel):
    """Schema for bulk updating system config"""
    configs: list[dict[str, str]]
