-- Migration: Add ISBN-10/ISBN-13 fields to books table and create core library tables
-- Phase-1: Book Insertion Service
-- Date: 2025-10-08
-- Description: Extends books table with isbn_10 and isbn_13 fields, adds indexes,
--              and ensures compatibility with existing isbn field for backward compatibility.

-- Set search path to lms_core schema
SET search_path TO lms_core;

-- ============================================================================
-- STEP 1: Add new ISBN fields to existing books table (if it exists)
-- ============================================================================

-- Add isbn_10 column (nullable, indexed)
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'lms_core' AND table_name = 'books') THEN
        -- Check if column doesn't already exist
        IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                       WHERE table_schema = 'lms_core' AND table_name = 'books' AND column_name = 'isbn_10') THEN
            ALTER TABLE books ADD COLUMN isbn_10 VARCHAR(10);
            RAISE NOTICE 'Added isbn_10 column to books table';
        ELSE
            RAISE NOTICE 'isbn_10 column already exists in books table';
        END IF;
    END IF;
END$$;

-- Add isbn_13 column (nullable, unique, indexed)
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'lms_core' AND table_name = 'books') THEN
        -- Check if column doesn't already exist
        IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                       WHERE table_schema = 'lms_core' AND table_name = 'books' AND column_name = 'isbn_13') THEN
            ALTER TABLE books ADD COLUMN isbn_13 VARCHAR(13);
            RAISE NOTICE 'Added isbn_13 column to books table';
        ELSE
            RAISE NOTICE 'isbn_13 column already exists in books table';
        END IF;
    END IF;
END$$;

-- ============================================================================
-- STEP 2: Create indexes for ISBN fields
-- ============================================================================

-- Index on isbn_10 for fast lookups
CREATE INDEX IF NOT EXISTS idx_books_isbn_10 ON books(isbn_10);

-- Unique index on isbn_13 (canonical identifier)
CREATE UNIQUE INDEX IF NOT EXISTS idx_books_isbn_13 ON books(isbn_13);

-- ============================================================================
-- STEP 3: Migrate existing ISBN data (if books table has data)
-- ============================================================================

-- Populate isbn_10 and isbn_13 from existing isbn field
-- This assumes existing isbn field contains either ISBN-10 or ISBN-13
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'lms_core' AND table_name = 'books') THEN
        -- Update isbn_10 for 10-digit ISBNs
        UPDATE books
        SET isbn_10 = isbn
        WHERE isbn IS NOT NULL 
          AND LENGTH(REPLACE(REPLACE(isbn, '-', ''), ' ', '')) = 10
          AND isbn_10 IS NULL;
        
        -- Update isbn_13 for 13-digit ISBNs
        UPDATE books
        SET isbn_13 = isbn
        WHERE isbn IS NOT NULL 
          AND LENGTH(REPLACE(REPLACE(isbn, '-', ''), ' ', '')) = 13
          AND isbn_13 IS NULL;
        
        RAISE NOTICE 'Migrated existing ISBN data to isbn_10 and isbn_13 fields';
    END IF;
END$$;

-- ============================================================================
-- STEP 4: Add comment to existing books table columns
-- ============================================================================

DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'lms_core' AND table_name = 'books') THEN
        COMMENT ON COLUMN books.isbn_10 IS 'ISBN-10 format (10 digits)';
        COMMENT ON COLUMN books.isbn_13 IS 'ISBN-13 format (13 digits, canonical identifier)';
        COMMENT ON COLUMN books.isbn IS 'Legacy ISBN field (kept for backward compatibility)';
        RAISE NOTICE 'Added comments to ISBN columns';
    END IF;
END$$;

-- ============================================================================
-- VERIFICATION QUERIES (commented out - uncomment to verify migration)
-- ============================================================================

-- Check if columns exist
-- SELECT column_name, data_type, character_maximum_length, is_nullable
-- FROM information_schema.columns
-- WHERE table_schema = 'lms_core' AND table_name = 'books'
-- AND column_name IN ('isbn', 'isbn_10', 'isbn_13')
-- ORDER BY ordinal_position;

-- Check indexes
-- SELECT indexname, indexdef
-- FROM pg_indexes
-- WHERE schemaname = 'lms_core' AND tablename = 'books'
-- AND indexname LIKE '%isbn%';

-- ============================================================================
-- ROLLBACK INSTRUCTIONS (if needed)
-- ============================================================================

-- To rollback this migration:
-- DROP INDEX IF EXISTS lms_core.idx_books_isbn_10;
-- DROP INDEX IF EXISTS lms_core.idx_books_isbn_13;
-- ALTER TABLE lms_core.books DROP COLUMN IF EXISTS isbn_10;
-- ALTER TABLE lms_core.books DROP COLUMN IF EXISTS isbn_13;
