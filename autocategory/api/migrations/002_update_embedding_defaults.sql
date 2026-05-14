-- Update legacy embedding defaults from Ollama/nomic to local sentence-transformers Alibaba GTE

UPDATE system_config
SET value = 'Alibaba-NLP/gte-multilingual-base',
    description = 'Embedding model name',
    category = 'embeddings',
    value_type = 'string',
    is_secret = FALSE,
    is_active = TRUE,
    updated_at = NOW()
WHERE key = 'embeddings.model_name';

UPDATE system_config
SET value = 'local://sentence-transformers',
    description = 'Sentence Transformers provider (local)',
    category = 'embeddings',
    value_type = 'string',
    is_secret = FALSE,
    is_active = TRUE,
    updated_at = NOW()
WHERE key = 'embeddings.base_url';

INSERT INTO system_config (key, value, value_type, description, category, is_secret, is_active)
SELECT 'embeddings.model_name', 'Alibaba-NLP/gte-multilingual-base', 'string', 'Embedding model name', 'embeddings', FALSE, TRUE
WHERE NOT EXISTS (SELECT 1 FROM system_config WHERE key = 'embeddings.model_name');

INSERT INTO system_config (key, value, value_type, description, category, is_secret, is_active)
SELECT 'embeddings.base_url', 'local://sentence-transformers', 'string', 'Sentence Transformers provider (local)', 'embeddings', FALSE, TRUE
WHERE NOT EXISTS (SELECT 1 FROM system_config WHERE key = 'embeddings.base_url');
