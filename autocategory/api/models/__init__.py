"""
Database models
"""
from sqlalchemy import Column, Integer, String, Boolean, Float, DateTime, ForeignKey, Text, ARRAY, JSON
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from database import Base


class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    full_name = Column(String(255))
    role = Column(String(20), nullable=False, default="viewer", index=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    last_login_at = Column(DateTime(timezone=True))
    
    # Relationships
    api_keys = relationship("APIKey", back_populates="user", cascade="all, delete-orphan")
    request_logs = relationship("RequestLog", back_populates="user")
    training_data = relationship("TrainingData", back_populates="user", foreign_keys="TrainingData.user_id")
    
    def __repr__(self):
        return f"<User(id={self.id}, username='{self.username}', role='{self.role}')>"


class APIKey(Base):
    __tablename__ = "api_keys"
    
    id = Column(Integer, primary_key=True, index=True)
    key_hash = Column(String(255), unique=True, nullable=False, index=True)
    key_prefix = Column(String(20), nullable=False)
    name = Column(String(255), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"))
    
    environment = Column(String(20), default="production")
    
    # Rate limiting
    rate_limit_per_minute = Column(Integer, default=60)
    rate_limit_per_day = Column(Integer, default=1000)
    
    # Permissions
    can_classify = Column(Boolean, default=True)
    can_generate = Column(Boolean, default=True)
    can_admin = Column(Boolean, default=False)
    
    # Usage tracking
    total_requests = Column(Integer, default=0)
    last_used_at = Column(DateTime(timezone=True))
    
    # Metadata
    expires_at = Column(DateTime(timezone=True))
    is_active = Column(Boolean, default=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    revoked_at = Column(DateTime(timezone=True))
    
    # Relationships
    user = relationship("User", back_populates="api_keys")
    request_logs = relationship("RequestLog", back_populates="api_key")
    
    def __repr__(self):
        return f"<APIKey(id={self.id}, name='{self.name}', prefix='{self.key_prefix}')>"


class RequestLog(Base):
    __tablename__ = "request_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    api_key_id = Column(Integer, ForeignKey("api_keys.id", ondelete="SET NULL"), index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), index=True)
    
    # Request details
    endpoint = Column(String(255), nullable=False, index=True)
    method = Column(String(10), nullable=False)
    request_body = Column(Text)
    response_status = Column(Integer)
    response_time_ms = Column(Float)
    error_message = Column(Text)
    
    # Classification details
    input_title = Column(Text)
    input_description = Column(Text)
    predicted_category_id = Column(Integer)
    predicted_category_name = Column(String(255))
    predicted_category_path = Column(Text)
    confidence = Column(Float)
    decision = Column(String(50))
    llm_reason = Column(Text)  # LLM reasoning for preselect/reject
    
    # User feedback
    actual_category_id = Column(Integer)
    was_corrected = Column(Boolean, default=False, index=True)
    
    # Metadata
    ip_address = Column(String(50))
    user_agent = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    
    # Relationships
    api_key = relationship("APIKey", back_populates="request_logs")
    user = relationship("User", back_populates="request_logs")
    
    def __repr__(self):
        return f"<RequestLog(id={self.id}, endpoint='{self.endpoint}', status={self.response_status})>"


class TrainingData(Base):
    __tablename__ = "training_data"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Input
    title = Column(Text, nullable=False)
    description = Column(Text)
    price = Column(Float)
    image_urls = Column(ARRAY(Text))
    
    # Prediction
    predicted_category_id = Column(Integer)
    predicted_category_name = Column(String(255))
    predicted_category_path = Column(Text)
    predicted_confidence = Column(Float)
    predicted_decision = Column(String(50))
    
    # Ground truth
    actual_category_id = Column(Integer, nullable=False, index=True)
    actual_category_name = Column(String(255))
    actual_category_path = Column(Text)
    
    # LLM reasoning
    llm_reason = Column(Text)
    understanding_output = Column(Text)
    
    # Source
    source = Column(String(50), default="feedback", index=True)
    is_validated = Column(Boolean, default=False, index=True)
    validation_notes = Column(Text)
    
    # Quality score
    quality_score = Column(Float, index=True)
    
    # Metadata
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"))
    request_log_id = Column(Integer, ForeignKey("request_logs.id", ondelete="SET NULL"))
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    validated_at = Column(DateTime(timezone=True))
    validated_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"))
    
    # Relationships
    user = relationship("User", back_populates="training_data", foreign_keys=[user_id])
    validator = relationship("User", foreign_keys=[validated_by])
    
    def __repr__(self):
        return f"<TrainingData(id={self.id}, title='{self.title[:50]}...', category={self.actual_category_id})>"


class SystemConfig(Base):
    __tablename__ = "system_config"
    
    id = Column(Integer, primary_key=True, index=True)
    key = Column(String(255), unique=True, nullable=False, index=True)
    value = Column(Text, nullable=False)
    value_type = Column(String(50), default="string")
    description = Column(Text)
    category = Column(String(100), index=True)
    is_secret = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    updated_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    def __repr__(self):
        return f"<SystemConfig(key='{self.key}', value_type='{self.value_type}')>"


class Category(Base):
    __tablename__ = "categories"

    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)
    slug = Column(String(255))
    description = Column(Text)
    icon = Column(String(255), default="fas fa-folder")
    image = Column(String(500))
    parent_id = Column(Integer, ForeignKey("categories.id", ondelete="SET NULL"), nullable=True, index=True)
    sort_order = Column(Integer, default=0)
    is_featured = Column(Integer, default=0)
    is_home_cheap = Column(Integer, default=0)
    is_active = Column(Integer, default=1, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    fields = relationship("CategoryField", back_populates="category", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Category(id={self.id}, name='{self.name}')>"


class CategoryField(Base):
    __tablename__ = "category_fields"

    id = Column(Integer, primary_key=True)
    category_id = Column(Integer, ForeignKey("categories.id", ondelete="CASCADE"), nullable=False, index=True)
    field_key = Column(String(255), nullable=False)
    field_label = Column(String(255), nullable=False)
    field_type = Column(String(50), nullable=False)   # "select", "radio", "text"
    field_options = Column(JSON)                       # [{value, label, featured, sort_order}]
    is_required = Column(Boolean, default=False)
    is_featured = Column(Boolean, default=False)
    omni_field_id = Column(Integer, nullable=True, index=True)  # ID gốc của field trong Omni
    parent_field_id = Column(Integer, nullable=True)             # omni_field_id của field cha
    parent_field_value = Column(String(255), nullable=True)
    sort_order = Column(Integer, default=0)

    category = relationship("Category", back_populates="fields")

    def __repr__(self):
        return f"<CategoryField(id={self.id}, category_id={self.category_id}, key='{self.field_key}')>"


class CategorySyncHistory(Base):
    __tablename__ = "category_sync_history"
    
    id = Column(Integer, primary_key=True, index=True)
    source = Column(String(255))
    source_url = Column(String(500))
    sync_type = Column(String(50))
    
    # Changes detected
    changes_detected = Column(Boolean, default=False)
    categories_added = Column(Integer, default=0)
    categories_modified = Column(Integer, default=0)
    categories_deleted = Column(Integer, default=0)
    
    # Status
    success = Column(Boolean, default=True, index=True)
    error_message = Column(Text)
    duration_ms = Column(Float)
    
    # Metadata
    synced_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"))
    synced_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    
    def __repr__(self):
        return f"<CategorySyncHistory(id={self.id}, sync_type='{self.sync_type}', success={self.success})>"


class TrainingJob(Base):
    __tablename__ = "training_jobs"
    
    id = Column(Integer, primary_key=True, index=True)
    job_uuid = Column(String(36), unique=True, nullable=False)
    
    # Job details
    job_name = Column(String(255))
    model_type = Column(String(50))
    model_version = Column(String(50))
    dataset_id = Column(String(100))
    
    # Configuration
    config = Column(JSON)
    
    # Status
    status = Column(String(50), default="pending", index=True)
    progress = Column(Float, default=0.0)
    
    # Metrics
    train_samples = Column(Integer)
    val_samples = Column(Integer)
    test_samples = Column(Integer)
    accuracy = Column(Float)
    loss = Column(Float)
    
    # Timing
    started_at = Column(DateTime(timezone=True))
    completed_at = Column(DateTime(timezone=True))
    duration_seconds = Column(Integer)
    
    # Results
    model_path = Column(String(500))
    metrics = Column(JSON)
    error_message = Column(Text)
    
    # Deployment
    deployed = Column(Boolean, default=False, index=True)
    deployed_at = Column(DateTime(timezone=True))
    deployed_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"))
    
    # Metadata
    created_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"))
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    
    def __repr__(self):
        return f"<TrainingJob(id={self.id}, status='{self.status}', model_type='{self.model_type}')>"


class ModelVersion(Base):
    __tablename__ = "model_versions"
    
    id = Column(Integer, primary_key=True, index=True)
    version = Column(String(50), unique=True, nullable=False, index=True)
    model_type = Column(String(50))
    
    # Model info
    model_path = Column(String(500))
    config = Column(JSON)
    metrics = Column(JSON)
    
    # Deployment
    is_active = Column(Boolean, default=False, index=True)
    is_production = Column(Boolean, default=False, index=True)
    
    # A/B testing
    ab_test_enabled = Column(Boolean, default=False)
    ab_test_percentage = Column(Float)
    
    # Training job reference
    training_job_id = Column(Integer, ForeignKey("training_jobs.id", ondelete="SET NULL"))
    
    # Metadata
    created_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    activated_at = Column(DateTime(timezone=True))
    deactivated_at = Column(DateTime(timezone=True))
    
    def __repr__(self):
        return f"<ModelVersion(version='{self.version}', is_production={self.is_production})>"


class AuditLog(Base):
    __tablename__ = "audit_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), index=True)
    action = Column(String(100), nullable=False, index=True)
    resource_type = Column(String(100))
    resource_id = Column(String(100))
    details = Column(JSON)
    ip_address = Column(String(50))
    user_agent = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    
    def __repr__(self):
        return f"<AuditLog(id={self.id}, action='{self.action}', user_id={self.user_id})>"
