-- Migration 004: Seed SystemConfig entries for LM Studio / LLM provider settings
-- These serve as documentation and can be edited via Admin Dashboard → Configuration

INSERT INTO system_config (key, value, value_type, description, category, is_secret, is_active)
VALUES
    ('llm.provider',
     'llama',
     'string',
     'LLM provider đang sử dụng. "llama" = llama.cpp server (Docker), "lm_studio" = LM Studio trên host machine.',
     'llm',
     false,
     true),

    ('llm.lm_studio_base_url',
     'http://host.docker.internal:11434',
     'string',
     'Base URL của LM Studio API. Mặc định: http://host.docker.internal:11434 (từ Docker container đến host).',
     'llm',
     false,
     true),

    ('llm.lm_studio_model',
     'google/gemma-4-e4b',
     'string',
     'Tên model dùng trong LM Studio (phải khớp với model đã load trong LM Studio).',
     'llm',
     false,
     true),

    ('llm.llama_base_url',
     'http://llama-server:8080',
     'string',
     'Base URL của llama.cpp server (Docker service name). Chỉ cần thay đổi nếu port/host khác mặc định.',
     'llm',
     false,
     true),

    ('llm.llama_model',
     'gemma4-e4b',
     'string',
     'Tên model truyền vào llama.cpp server API.',
     'llm',
     false,
     true)

ON CONFLICT (key) DO NOTHING;
