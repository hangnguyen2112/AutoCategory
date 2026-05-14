-- Migration: Add llm_reason column to request_logs table
-- Created: 2026-05-07
-- Purpose: Store LLM reasoning for preselect/reject decisions

-- Add llm_reason column
ALTER TABLE request_logs ADD COLUMN IF NOT EXISTS llm_reason TEXT;

-- Create index for better query performance
CREATE INDEX IF NOT EXISTS idx_request_logs_llm_reason ON request_logs USING gin(to_tsvector('english', llm_reason));

-- Optional: Update existing rows (if needed)
-- UPDATE request_logs SET llm_reason = '' WHERE llm_reason IS NULL;
