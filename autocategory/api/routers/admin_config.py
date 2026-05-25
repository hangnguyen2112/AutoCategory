"""
System configuration management endpoints (Admin only)
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime

from database import get_db
from models import SystemConfig
from schemas.system_config import (
    SystemConfigCreate,
    SystemConfigUpdate,
    SystemConfigResponse,
    SystemConfigBulkUpdate,
)
from schemas.auth import MessageResponse
from dependencies import CurrentAdminUser
from runtime_config import runtime_config

router = APIRouter(prefix="/api/admin/config", tags=["Admin - Configuration"])


@router.get("", response_model=list[SystemConfigResponse])
async def list_system_configs(
    current_admin: CurrentAdminUser,
    db: Session = Depends(get_db),
    category: Optional[str] = None,
    is_active: Optional[bool] = None,
    search: Optional[str] = None,
):
    """
    List system configurations
    """
    query = db.query(SystemConfig)
    
    # Apply filters
    if category:
        query = query.filter(SystemConfig.category == category)
    
    if is_active is not None:
        query = query.filter(SystemConfig.is_active == is_active)
    
    if search:
        query = query.filter(
            SystemConfig.key.ilike(f"%{search}%") |
            SystemConfig.description.ilike(f"%{search}%")
        )
    
    # Order by category, then key
    query = query.order_by(SystemConfig.category, SystemConfig.key)
    
    configs = query.all()
    
    return [SystemConfigResponse.model_validate(config) for config in configs]


@router.post("", response_model=SystemConfigResponse)
async def create_system_config(
    config_data: SystemConfigCreate,
    current_admin: CurrentAdminUser,
    db: Session = Depends(get_db)
):
    """
    Create a new system configuration
    """
    # Check if key already exists
    existing = db.query(SystemConfig).filter(SystemConfig.key == config_data.key).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Configuration key '{config_data.key}' already exists"
        )
    
    config = SystemConfig(
        key=config_data.key,
        value=config_data.value,
        value_type=config_data.value_type,
        description=config_data.description,
        category=config_data.category,
        is_secret=config_data.is_secret,
        is_active=config_data.is_active,
        updated_by=current_admin.id
    )
    
    db.add(config)
    db.commit()
    db.refresh(config)
    
    return SystemConfigResponse.model_validate(config)


@router.get("/{key}", response_model=SystemConfigResponse)
async def get_system_config(
    key: str,
    current_admin: CurrentAdminUser,
    db: Session = Depends(get_db),
    reveal_secret: bool = Query(False)
):
    """
    Get system configuration by key
    """
    config = db.query(SystemConfig).filter(SystemConfig.key == key).first()
    
    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Configuration key '{key}' not found"
        )
    
    response = SystemConfigResponse.model_validate(config)
    
    # If reveal_secret is True, show actual value for secrets
    if reveal_secret and config.is_secret:
        response.value = config.value
    
    return response


@router.patch("/{key}", response_model=SystemConfigResponse)
async def update_system_config(
    key: str,
    update_data: SystemConfigUpdate,
    current_admin: CurrentAdminUser,
    db: Session = Depends(get_db)
):
    """
    Update system configuration
    """
    config = db.query(SystemConfig).filter(SystemConfig.key == key).first()
    
    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Configuration key '{key}' not found"
        )
    
    # Update fields
    update_dict = update_data.model_dump(exclude_unset=True)
    for field, value in update_dict.items():
        setattr(config, field, value)
    
    config.updated_by = current_admin.id
    config.updated_at = datetime.utcnow()
    
    db.commit()
    db.refresh(config)

    # Sync llm.* changes into runtime_config immediately (no restart needed)
    if key.startswith("llm.") and config.value:
        runtime_config._data[key] = config.value

    return SystemConfigResponse.model_validate(config)


@router.delete("/{key}", response_model=MessageResponse)
async def delete_system_config(
    key: str,
    current_admin: CurrentAdminUser,
    db: Session = Depends(get_db)
):
    """
    Delete system configuration
    """
    config = db.query(SystemConfig).filter(SystemConfig.key == key).first()
    
    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Configuration key '{key}' not found"
        )
    
    db.delete(config)
    db.commit()
    
    return MessageResponse(
        message=f"Configuration key '{key}' deleted successfully"
    )


@router.post("/bulk-update", response_model=MessageResponse)
async def bulk_update_configs(
    bulk_data: SystemConfigBulkUpdate,
    current_admin: CurrentAdminUser,
    db: Session = Depends(get_db)
):
    """
    Bulk update multiple configurations
    """
    updated_count = 0
    errors = []
    
    for config_dict in bulk_data.configs:
        key = config_dict.get("key")
        value = config_dict.get("value")
        
        if not key or value is None:
            errors.append(f"Missing key or value in config: {config_dict}")
            continue
        
        config = db.query(SystemConfig).filter(SystemConfig.key == key).first()
        
        if config:
            config.value = value
            config.updated_by = current_admin.id
            config.updated_at = datetime.utcnow()
            updated_count += 1
        else:
            errors.append(f"Configuration key '{key}' not found")
    
    db.commit()

    # Sync llm.* changes into runtime_config immediately
    for config_dict in bulk_data.configs:
        k = config_dict.get("key", "")
        v = config_dict.get("value")
        if k.startswith("llm.") and v is not None:
            runtime_config._data[k] = v
    
    message = f"Updated {updated_count} configurations"
    if errors:
        message += f". Errors: {', '.join(errors)}"
    
    return MessageResponse(message=message, detail=", ".join(errors) if errors else None)


@router.get("/categories/list")
async def list_config_categories(
    current_admin: CurrentAdminUser,
    db: Session = Depends(get_db)
):
    """
    Get list of unique configuration categories
    """
    categories = db.query(SystemConfig.category).distinct().filter(
        SystemConfig.category.isnot(None)
    ).all()
    
    return {"categories": [cat[0] for cat in categories]}
