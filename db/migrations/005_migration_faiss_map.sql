-- Migration: Add enhanced_metadata to books and create FAISS mapping table
-- Date: 2025-11-07

SET search_path TO lms_core;

-- Add enhanced_metadata JSONB column to books if not exists
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_schema = 'lms_core' AND table_name = 'books' AND column_name = 'enhanced_metadata'
    ) THEN
        ALTER TABLE books ADD COLUMN enhanced_metadata JSONB NULL;
    END IF;
END$$;

-- Create book_faiss_map table for FAISS ID mappings (one per book per vector_type)
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.tables 
        WHERE table_schema = 'lms_core' AND table_name = 'book_faiss_map'
    ) THEN
        CREATE TABLE book_faiss_map (
            id SERIAL PRIMARY KEY,
            book_id BIGINT NOT NULL REFERENCES books(book_id) ON DELETE CASCADE,
            vector_type TEXT NOT NULL CHECK (vector_type IN ('identity','topical')),
            faiss_id BIGINT GENERATED ALWAYS AS (id) STORED NOT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now()
        );
    END IF;
END$$;

-- Indexes and uniqueness
CREATE INDEX IF NOT EXISTS idx_book_faiss_map_type ON book_faiss_map(vector_type);
CREATE INDEX IF NOT EXISTS idx_book_faiss_map_book_id ON book_faiss_map(book_id);
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 
        FROM pg_constraint 
        WHERE conname = 'uq_book_faiss_map' AND conrelid = 'book_faiss_map'::regclass
    ) THEN
        ALTER TABLE book_faiss_map ADD CONSTRAINT uq_book_faiss_map UNIQUE (book_id, vector_type);
    END IF;
END$$;
