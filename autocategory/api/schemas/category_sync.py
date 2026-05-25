"""
Category sync schemas
"""
from pydantic import BaseModel
from datetime import datetime
from typing import Optional


class CategorySyncBase(BaseModel):
    source: str
    sync_type: str  # manual, webhook, scheduled


class CategorySyncCreate(CategorySyncBase):
    changes_detected: bool = False
    categories_added: int = 0
    categories_modified: int = 0
    categories_deleted: int = 0
    success: bool = True
    error_message: Optional[str] = None


class CategorySyncResponse(CategorySyncBase):
    id: int
    changes_detected: bool
    categories_added: int
    categories_modified: int
    categories_deleted: int
    success: bool
    error_message: Optional[str] = None
    synced_by: Optional[int] = None
    synced_at: datetime
    
    class Config:
        from_attributes = True


class CategorySyncStats(BaseModel):
    total_syncs: int
    successful_syncs: int
    failed_syncs: int
    last_sync_at: Optional[datetime] = None
    total_categories_added: int
    total_categories_modified: int
    total_categories_deleted: int


class CategoryImportRequest(BaseModel):
    categories: list[dict]
    replace_existing: bool = False
    validate_only: bool = False


class CategoryImportResponse(BaseModel):
    validated: bool
    validation_errors: list[str] = []
    categories_to_add: int = 0
    categories_to_update: int = 0
    categories_to_delete: int = 0
    imported: bool = False
    import_summary: Optional[str] = None


class CategoryRebuildIndexRequest(BaseModel):
    force: bool = False
    only_leaf_categories: bool = True


class CategoryRebuildIndexResponse(BaseModel):
    success: bool
    categories_indexed: int
    attributes_indexed: int = 0
    time_taken_seconds: float
    error_message: Optional[str] = None
