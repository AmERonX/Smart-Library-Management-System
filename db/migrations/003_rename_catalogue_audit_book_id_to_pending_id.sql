-- Migration: Rename catalogue_audit.book_id to pending_id for clarity
-- Date: 2025-10-09
-- Description: The book_id column in catalogue_audit actually references pending_catalogue.id,
--              not books.book_id. Renaming to pending_id to avoid confusion.
--              The actual book_id from books table is stored in the details JSON field.

-- Set search path to lms_core schema
SET search_path TO lms_core;

-- ============================================================================
-- STEP 1: Rename book_id column to pending_id
-- ============================================================================

DO $$
BEGIN
    -- Check if column book_id exists and pending_id doesn't exist
    IF EXISTS (SELECT 1 FROM information_schema.columns 
               WHERE table_schema = 'lms_core' AND table_name = 'catalogue_audit' AND column_name = 'book_id')
       AND NOT EXISTS (SELECT 1 FROM information_schema.columns 
                       WHERE table_schema = 'lms_core' AND table_name = 'catalogue_audit' AND column_name = 'pending_id') THEN
        
        ALTER TABLE catalogue_audit RENAME COLUMN book_id TO pending_id;
        RAISE NOTICE 'Renamed catalogue_audit.book_id to pending_id';
    ELSE
        RAISE NOTICE 'Column already renamed or migration already applied';
    END IF;
END$$;

-- ============================================================================
-- STEP 2: Update index name for consistency
-- ============================================================================

DO $$
BEGIN
    -- Check if old index exists
    IF EXISTS (SELECT 1 FROM pg_indexes 
               WHERE schemaname = 'lms_core' AND tablename = 'catalogue_audit' AND indexname = 'ix_catalogue_audit_book_id') THEN
        
        ALTER INDEX ix_catalogue_audit_book_id RENAME TO ix_catalogue_audit_pending_id;
        RAISE NOTICE 'Renamed index ix_catalogue_audit_book_id to ix_catalogue_audit_pending_id';
    ELSE
        RAISE NOTICE 'Index already renamed or does not exist';
    END IF;
END$$;

-- ============================================================================
-- STEP 3: Verify foreign key constraint still points to pending_catalogue.id
-- ============================================================================

-- Note: The foreign key constraint should still reference pending_catalogue.id
-- No changes needed to the constraint itself, just the column name

-- Verification query (informational only)
DO $$
DECLARE
    fk_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO fk_count
    FROM information_schema.table_constraints tc
    JOIN information_schema.key_column_usage kcu 
        ON tc.constraint_name = kcu.constraint_name
        AND tc.table_schema = kcu.table_schema
    WHERE tc.constraint_type = 'FOREIGN KEY'
        AND tc.table_schema = 'lms_core'
        AND tc.table_name = 'catalogue_audit'
        AND kcu.column_name = 'pending_id';
    
    IF fk_count > 0 THEN
        RAISE NOTICE 'Foreign key constraint verified: pending_id references pending_catalogue.id';
    ELSE
        RAISE WARNING 'Foreign key constraint not found - may need manual verification';
    END IF;
END$$;

-- ============================================================================
-- Migration complete
-- ============================================================================

DO $$
BEGIN
    RAISE NOTICE '✓ Migration 003 completed: catalogue_audit.book_id renamed to pending_id';
END$$;
