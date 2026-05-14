-- Migration 003: Add categories and category_fields tables
-- Replaces JSON-file-based category storage with DB storage

CREATE TABLE IF NOT EXISTS categories (
    id INTEGER PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    slug VARCHAR(255),
    description TEXT,
    icon VARCHAR(255) DEFAULT 'fas fa-folder',
    image VARCHAR(500),
    parent_id INTEGER REFERENCES categories(id) ON DELETE SET NULL,
    sort_order INTEGER DEFAULT 0,
    is_featured INTEGER DEFAULT 0,
    is_home_cheap INTEGER DEFAULT 0,
    is_active INTEGER DEFAULT 1,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_categories_parent_id ON categories(parent_id);
CREATE INDEX IF NOT EXISTS idx_categories_is_active ON categories(is_active);

CREATE TABLE IF NOT EXISTS category_fields (
    id SERIAL PRIMARY KEY,
    category_id INTEGER NOT NULL REFERENCES categories(id) ON DELETE CASCADE,
    field_key VARCHAR(255) NOT NULL,
    field_label VARCHAR(255) NOT NULL,
    field_type VARCHAR(50) NOT NULL,
    field_options JSON,
    is_required BOOLEAN DEFAULT FALSE,
    is_featured BOOLEAN DEFAULT FALSE,
    parent_field_id INTEGER,
    parent_field_value VARCHAR(255),
    sort_order INTEGER DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_category_fields_category_id ON category_fields(category_id);
