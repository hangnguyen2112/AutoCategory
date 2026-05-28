-- Migration 005: Add omni_field_id to category_fields
-- Lưu Omni's original field ID để resolve parent_field_id chính xác

ALTER TABLE category_fields
    ADD COLUMN IF NOT EXISTS omni_field_id INTEGER;

CREATE INDEX IF NOT EXISTS idx_category_fields_omni_field_id ON category_fields(omni_field_id);

COMMENT ON COLUMN category_fields.omni_field_id IS 'ID gốc của field trong hệ thống Omni (khác với local PK id)';
COMMENT ON COLUMN category_fields.parent_field_id IS 'omni_field_id của field cha, dùng để xác định conditional field';
