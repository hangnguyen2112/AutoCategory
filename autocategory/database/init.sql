-- AutoCategory Database Schema
-- Version: 1.0.0
-- Created: 2026-05-06

-- Enable extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Users table
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    full_name VARCHAR(255),
    role VARCHAR(20) NOT NULL DEFAULT 'viewer',  -- admin, developer, viewer
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_login_at TIMESTAMP,
    
    CONSTRAINT check_role CHECK (role IN ('admin', 'developer', 'viewer'))
);

-- Create index on email for faster lookups
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_username ON users(username);
CREATE INDEX idx_users_role ON users(role);

-- API Keys table
CREATE TABLE IF NOT EXISTS api_keys (
    id SERIAL PRIMARY KEY,
    key_hash VARCHAR(255) UNIQUE NOT NULL,
    key_prefix VARCHAR(20) NOT NULL,  -- First 8 chars for display (sk_live_...)
    name VARCHAR(255) NOT NULL,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    
    -- Environment
    environment VARCHAR(20) DEFAULT 'production',  -- production, development, test
    
    -- Rate limiting
    rate_limit_per_minute INTEGER DEFAULT 60,
    rate_limit_per_day INTEGER DEFAULT 1000,
    
    -- Permissions
    can_classify BOOLEAN DEFAULT TRUE,
    can_generate BOOLEAN DEFAULT TRUE,
    can_admin BOOLEAN DEFAULT FALSE,
    
    -- Usage tracking
    total_requests INTEGER DEFAULT 0,
    last_used_at TIMESTAMP,
    
    -- Metadata
    expires_at TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    revoked_at TIMESTAMP,
    
    CONSTRAINT check_environment CHECK (environment IN ('production', 'development', 'test'))
);

-- Create indexes for API key lookups
CREATE INDEX idx_api_keys_key_hash ON api_keys(key_hash);
CREATE INDEX idx_api_keys_user_id ON api_keys(user_id);
CREATE INDEX idx_api_keys_is_active ON api_keys(is_active);

-- Request logs table
CREATE TABLE IF NOT EXISTS request_logs (
    id SERIAL PRIMARY KEY,
    api_key_id INTEGER REFERENCES api_keys(id) ON DELETE SET NULL,
    user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    
    -- Request details
    endpoint VARCHAR(255) NOT NULL,
    method VARCHAR(10) NOT NULL,
    request_body TEXT,
    response_status INTEGER,
    response_time_ms FLOAT,
    error_message TEXT,
    
    -- Classification details (if classify endpoint)
    input_title TEXT,
    input_description TEXT,
    predicted_category_id INTEGER,
    predicted_category_name VARCHAR(255),
    predicted_category_path TEXT,
    confidence FLOAT,
    decision VARCHAR(50),
    
    -- User feedback (if corrected)
    actual_category_id INTEGER,
    was_corrected BOOLEAN DEFAULT FALSE,
    
    -- Metadata
    ip_address VARCHAR(50),
    user_agent TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for log queries
CREATE INDEX idx_request_logs_api_key_id ON request_logs(api_key_id);
CREATE INDEX idx_request_logs_user_id ON request_logs(user_id);
CREATE INDEX idx_request_logs_endpoint ON request_logs(endpoint);
CREATE INDEX idx_request_logs_created_at ON request_logs(created_at);
CREATE INDEX idx_request_logs_was_corrected ON request_logs(was_corrected);

-- Training data table
CREATE TABLE IF NOT EXISTS training_data (
    id SERIAL PRIMARY KEY,
    
    -- Input
    title TEXT NOT NULL,
    description TEXT,
    price FLOAT,
    image_urls TEXT[],
    
    -- Prediction
    predicted_category_id INTEGER,
    predicted_category_name VARCHAR(255),
    predicted_category_path TEXT,
    predicted_confidence FLOAT,
    predicted_decision VARCHAR(50),
    
    -- Ground truth
    actual_category_id INTEGER NOT NULL,
    actual_category_name VARCHAR(255),
    actual_category_path TEXT,
    
    -- LLM reasoning (for improving model)
    llm_reason TEXT,
    understanding_output TEXT,
    
    -- Source
    source VARCHAR(50) DEFAULT 'feedback',  -- feedback, manual, import, generated
    is_validated BOOLEAN DEFAULT FALSE,
    validation_notes TEXT,
    
    -- Quality score (for filtering)
    quality_score FLOAT,  -- 0.0-1.0
    
    -- Metadata
    user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    request_log_id INTEGER REFERENCES request_logs(id) ON DELETE SET NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    validated_at TIMESTAMP,
    validated_by INTEGER REFERENCES users(id) ON DELETE SET NULL,
    
    CONSTRAINT check_source CHECK (source IN ('feedback', 'manual', 'import', 'generated'))
);

-- Create indexes for training data queries
CREATE INDEX idx_training_data_actual_category_id ON training_data(actual_category_id);
CREATE INDEX idx_training_data_is_validated ON training_data(is_validated);
CREATE INDEX idx_training_data_source ON training_data(source);
CREATE INDEX idx_training_data_created_at ON training_data(created_at);
CREATE INDEX idx_training_data_quality_score ON training_data(quality_score);

-- System config table
CREATE TABLE IF NOT EXISTS system_config (
    id SERIAL PRIMARY KEY,
    key VARCHAR(255) UNIQUE NOT NULL,
    value TEXT NOT NULL,
    value_type VARCHAR(50) DEFAULT 'string',  -- string, int, float, bool, json
    description TEXT,
    category VARCHAR(100),  -- llm, embeddings, classification, system, external
    is_secret BOOLEAN DEFAULT FALSE,  -- Hide value in UI
    is_active BOOLEAN DEFAULT TRUE,
    updated_by INTEGER REFERENCES users(id) ON DELETE SET NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT check_value_type CHECK (value_type IN ('string', 'int', 'float', 'bool', 'json'))
);

-- Create index on config key
CREATE INDEX idx_system_config_key ON system_config(key);
CREATE INDEX idx_system_config_category ON system_config(category);

-- Category sync history table
CREATE TABLE IF NOT EXISTS category_sync_history (
    id SERIAL PRIMARY KEY,
    source VARCHAR(255),
    source_url VARCHAR(500),
    sync_type VARCHAR(50),  -- manual, webhook, scheduled
    
    -- Changes detected
    changes_detected BOOLEAN DEFAULT FALSE,
    categories_added INTEGER DEFAULT 0,
    categories_modified INTEGER DEFAULT 0,
    categories_deleted INTEGER DEFAULT 0,
    
    -- Status
    success BOOLEAN DEFAULT TRUE,
    error_message TEXT,
    duration_ms FLOAT,
    
    -- Metadata
    synced_by INTEGER REFERENCES users(id) ON DELETE SET NULL,
    synced_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT check_sync_type CHECK (sync_type IN ('manual', 'webhook', 'scheduled'))
);

-- Create index on sync history
CREATE INDEX idx_category_sync_synced_at ON category_sync_history(synced_at);
CREATE INDEX idx_category_sync_success ON category_sync_history(success);

-- Training jobs table
CREATE TABLE IF NOT EXISTS training_jobs (
    id SERIAL PRIMARY KEY,
    job_uuid UUID DEFAULT uuid_generate_v4() UNIQUE,
    
    -- Job details
    job_name VARCHAR(255),
    model_type VARCHAR(50),  -- embeddings, llm_finetune
    model_version VARCHAR(50),
    dataset_id VARCHAR(100),
    
    -- Configuration
    config JSONB,
    
    -- Status
    status VARCHAR(50) DEFAULT 'pending',  -- pending, running, completed, failed, cancelled
    progress FLOAT DEFAULT 0.0,  -- 0.0 to 1.0
    
    -- Metrics
    train_samples INTEGER,
    val_samples INTEGER,
    test_samples INTEGER,
    accuracy FLOAT,
    loss FLOAT,
    
    -- Timing
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    duration_seconds INTEGER,
    
    -- Results
    model_path VARCHAR(500),
    metrics JSONB,
    error_message TEXT,
    
    -- Deployment
    deployed BOOLEAN DEFAULT FALSE,
    deployed_at TIMESTAMP,
    deployed_by INTEGER REFERENCES users(id) ON DELETE SET NULL,
    
    -- Metadata
    created_by INTEGER REFERENCES users(id) ON DELETE SET NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT check_status CHECK (status IN ('pending', 'running', 'completed', 'failed', 'cancelled')),
    CONSTRAINT check_model_type CHECK (model_type IN ('embeddings', 'llm_finetune'))
);

-- Create indexes for training jobs
CREATE INDEX idx_training_jobs_status ON training_jobs(status);
CREATE INDEX idx_training_jobs_created_at ON training_jobs(created_at);
CREATE INDEX idx_training_jobs_deployed ON training_jobs(deployed);

-- Model versions table
CREATE TABLE IF NOT EXISTS model_versions (
    id SERIAL PRIMARY KEY,
    version VARCHAR(50) UNIQUE NOT NULL,
    model_type VARCHAR(50),
    
    -- Model info
    model_path VARCHAR(500),
    config JSONB,
    metrics JSONB,
    
    -- Deployment
    is_active BOOLEAN DEFAULT FALSE,
    is_production BOOLEAN DEFAULT FALSE,
    
    -- A/B testing
    ab_test_enabled BOOLEAN DEFAULT FALSE,
    ab_test_percentage FLOAT,  -- 0.0 to 1.0
    
    -- Training job reference
    training_job_id INTEGER REFERENCES training_jobs(id) ON DELETE SET NULL,
    
    -- Metadata
    created_by INTEGER REFERENCES users(id) ON DELETE SET NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    activated_at TIMESTAMP,
    deactivated_at TIMESTAMP,
    
    CONSTRAINT check_model_type CHECK (model_type IN ('embeddings', 'llm_finetune'))
);

-- Create indexes for model versions
CREATE INDEX idx_model_versions_version ON model_versions(version);
CREATE INDEX idx_model_versions_is_active ON model_versions(is_active);
CREATE INDEX idx_model_versions_is_production ON model_versions(is_production);

-- Audit logs table (for security and compliance)
CREATE TABLE IF NOT EXISTS audit_logs (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    action VARCHAR(100) NOT NULL,
    resource_type VARCHAR(100),
    resource_id VARCHAR(100),
    details JSONB,
    ip_address VARCHAR(50),
    user_agent TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for audit logs
CREATE INDEX idx_audit_logs_user_id ON audit_logs(user_id);
CREATE INDEX idx_audit_logs_action ON audit_logs(action);
CREATE INDEX idx_audit_logs_created_at ON audit_logs(created_at);

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger to auto-update updated_at
CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_system_config_updated_at BEFORE UPDATE ON system_config
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Insert default admin user (password: admin123 - CHANGE IN PRODUCTION!)
-- Password hash for 'admin123' using bcrypt
INSERT INTO users (username, email, password_hash, full_name, role, is_active)
VALUES (
    'admin',
    'admin@autocategory.example',
    '$2a$12$hzMnl55X7qzSDgDkmgBJ2eEQPti3iNMQLDTrQx3X7QOxski3U/fzy',  -- bcrypt hash of 'admin123'
    'System Administrator',
    'admin',
    TRUE
) ON CONFLICT (username) DO NOTHING;

-- Insert default system configurations
INSERT INTO system_config (key, value, value_type, description, category, is_secret) VALUES
('llm.model_name', 'gemma4-e4b', 'string', 'LLM model name', 'llm', FALSE),
('llm.base_url', 'http://llama-server:8080/v1', 'string', 'LLM server base URL', 'llm', FALSE),
('llm.temperature', '0.1', 'float', 'LLM temperature', 'llm', FALSE),
('llm.max_tokens', '512', 'int', 'LLM max tokens', 'llm', FALSE),
('llm.timeout', '30', 'int', 'LLM timeout in seconds', 'llm', FALSE),

('embeddings.model_name', 'Alibaba-NLP/gte-multilingual-base', 'string', 'Embedding model name', 'embeddings', FALSE),
('embeddings.base_url', 'local://sentence-transformers', 'string', 'Sentence Transformers provider (local)', 'embeddings', FALSE),

('qdrant.host', 'qdrant', 'string', 'Qdrant host', 'qdrant', FALSE),
('qdrant.port', '6333', 'int', 'Qdrant port', 'qdrant', FALSE),
('qdrant.collection_name', 'categories', 'string', 'Qdrant collection name', 'qdrant', FALSE),

('classification.threshold_auto_assign', '0.90', 'float', 'Confidence threshold for auto assign', 'classification', FALSE),
('classification.threshold_preselect', '0.75', 'float', 'Confidence threshold for preselect', 'classification', FALSE),
('classification.threshold_suggest_top3', '0.55', 'float', 'Confidence threshold for suggest top 3', 'classification', FALSE),

('features.enable_image_generation', 'true', 'bool', 'Enable image-to-text generation', 'features', FALSE),
('features.enable_training', 'true', 'bool', 'Enable training pipeline', 'features', FALSE),

('rate_limit.default_per_minute', '60', 'int', 'Default rate limit per minute', 'rate_limit', FALSE),
('rate_limit.default_per_day', '1000', 'int', 'Default rate limit per day', 'rate_limit', FALSE),

('system.log_level', 'INFO', 'string', 'System log level', 'system', FALSE),
('system.data_retention_days', '90', 'int', 'Days to retain logs', 'system', FALSE)

ON CONFLICT (key) DO NOTHING;

-- Create a view for easy access to active API keys
CREATE OR REPLACE VIEW active_api_keys AS
SELECT 
    ak.id,
    ak.key_prefix,
    ak.name,
    ak.environment,
    ak.rate_limit_per_minute,
    ak.rate_limit_per_day,
    ak.total_requests,
    ak.last_used_at,
    u.username,
    u.email
FROM api_keys ak
JOIN users u ON ak.user_id = u.id
WHERE ak.is_active = TRUE
  AND (ak.expires_at IS NULL OR ak.expires_at > CURRENT_TIMESTAMP);

-- Create a view for training data statistics
CREATE OR REPLACE VIEW training_data_stats AS
SELECT 
    actual_category_id,
    actual_category_name,
    COUNT(*) as total_samples,
    SUM(CASE WHEN is_validated THEN 1 ELSE 0 END) as validated_samples,
    AVG(CASE WHEN predicted_confidence IS NOT NULL THEN predicted_confidence END) as avg_confidence,
    SUM(CASE WHEN actual_category_id != predicted_category_id THEN 1 ELSE 0 END) as correction_count
FROM training_data
GROUP BY actual_category_id, actual_category_name;

-- Create a view for daily request statistics
CREATE OR REPLACE VIEW daily_request_stats AS
SELECT 
    DATE(created_at) as date,
    endpoint,
    COUNT(*) as total_requests,
    AVG(response_time_ms) as avg_response_time,
    SUM(CASE WHEN response_status >= 200 AND response_status < 300 THEN 1 ELSE 0 END) as success_count,
    SUM(CASE WHEN response_status >= 400 THEN 1 ELSE 0 END) as error_count,
    AVG(CASE WHEN confidence IS NOT NULL THEN confidence END) as avg_confidence
FROM request_logs
GROUP BY DATE(created_at), endpoint
ORDER BY date DESC, endpoint;

-- Grant permissions (adjust as needed)
-- GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO autocategory;
-- GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO autocategory;

-- Vacuum and analyze
VACUUM ANALYZE;

-- Success message
DO $$
BEGIN
    RAISE NOTICE 'AutoCategory database schema initialized successfully!';
    RAISE NOTICE 'Default admin user created: username=admin, password=admin123 (CHANGE THIS!)';
END $$;
