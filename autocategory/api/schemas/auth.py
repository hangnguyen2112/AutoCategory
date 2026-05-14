"""
Pydantic schemas for authentication
"""
from pydantic import BaseModel, EmailStr, Field, ConfigDict
from typing import Optional
from datetime import datetime


class UserBase(BaseModel):
    """Base user schema"""
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    full_name: Optional[str] = None


class UserCreate(UserBase):
    """Schema for creating a new user"""
    password: str = Field(..., min_length=8, max_length=100)
    role: str = Field(default="viewer", pattern="^(admin|developer|viewer)$")


class UserUpdate(BaseModel):
    """Schema for updating a user"""
    email: Optional[EmailStr] = None
    full_name: Optional[str] = None
    role: Optional[str] = Field(None, pattern="^(admin|developer|viewer)$")
    is_active: Optional[bool] = None


class UserChangePassword(BaseModel):
    """Schema for changing password"""
    old_password: str
    new_password: str = Field(..., min_length=8, max_length=100)


class UserResponse(UserBase):
    """Schema for user response"""
    id: int
    role: str
    is_active: bool
    created_at: datetime
    last_login_at: Optional[datetime] = None
    
    model_config = ConfigDict(from_attributes=True)


class Token(BaseModel):
    """Schema for authentication token"""
    access_token: str
    refresh_token: Optional[str] = None
    token_type: str = "bearer"
    expires_in: int  # seconds


class TokenData(BaseModel):
    """Schema for token data"""
    username: Optional[str] = None


class LoginRequest(BaseModel):
    """Schema for login request"""
    username: str
    password: str


class LoginResponse(BaseModel):
    """Schema for login response"""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserResponse


class RefreshTokenRequest(BaseModel):
    """Schema for refresh token request"""
    refresh_token: str


class APIKeyBase(BaseModel):
    """Base API key schema"""
    name: str = Field(..., min_length=1, max_length=255)
    environment: str = Field(default="production", pattern="^(production|development|test)$")


class APIKeyCreate(APIKeyBase):
    """Schema for creating API key"""
    rate_limit_per_minute: int = Field(default=60, ge=1, le=1000)
    rate_limit_per_day: int = Field(default=1000, ge=1, le=100000)
    can_classify: bool = True
    can_generate: bool = True
    can_admin: bool = False
    expires_at: Optional[datetime] = None


class APIKeyResponse(APIKeyBase):
    """Schema for API key response"""
    id: int
    key_prefix: str
    user_id: int
    rate_limit_per_minute: int
    rate_limit_per_day: int
    can_classify: bool
    can_generate: bool
    can_admin: bool
    total_requests: int
    last_used_at: Optional[datetime]
    expires_at: Optional[datetime]
    is_active: bool
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


class APIKeyCreateResponse(BaseModel):
    """Schema for API key creation response (includes full key)"""
    api_key: str  # Full key, only shown once!
    key_info: APIKeyResponse


class MessageResponse(BaseModel):
    """Generic message response"""
    message: str
    detail: Optional[str] = None
