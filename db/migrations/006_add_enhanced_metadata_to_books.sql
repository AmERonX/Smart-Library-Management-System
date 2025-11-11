-- Migration 006: Add enhanced_metadata column to books table
-- This column stores AI-enhanced metadata as JSONB for flexibility

-- Add enhanced_metadata column to books table
ALTER TABLE lms_core.books 
ADD COLUMN IF NOT EXISTS enhanced_metadata JSONB;

-- Add comment to document the column
COMMENT ON COLUMN lms_core.books.enhanced_metadata IS 'AI-enhanced metadata (keywords, categories, description, etc.) stored as JSONB';

