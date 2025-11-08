-- Migration: Add UNIQUE constraints to publishers.name and authors.full_name
-- Date: 2025-10-10
-- Description: The insertion service uses ON CONFLICT (name) DO NOTHING for upsert semantics,
--              which requires a unique constraint. This migration adds the missing constraints.

-- Set search path to lms_core schema
SET search_path TO lms_core;

-- ============================================================================
-- STEP 1: Add UNIQUE constraint to publishers.name
-- ============================================================================

DO $$
BEGIN
    -- Check if constraint doesn't already exist
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint 
        WHERE conname = 'publishers_name_key' 
        AND connamespace = 'lms_core'::regnamespace
    ) THEN
        -- Add unique constraint
        ALTER TABLE publishers ADD CONSTRAINT publishers_name_key UNIQUE (name);
        RAISE NOTICE 'Added UNIQUE constraint to publishers.name';
    ELSE
        RAISE NOTICE 'UNIQUE constraint on publishers.name already exists';
    END IF;
END$$;

-- ============================================================================
-- STEP 2: Add UNIQUE constraint to authors.full_name
-- ============================================================================

DO $$
BEGIN
    -- Check if constraint doesn't already exist
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint 
        WHERE conname = 'authors_full_name_key' 
        AND connamespace = 'lms_core'::regnamespace
    ) THEN
        -- Add unique constraint
        ALTER TABLE authors ADD CONSTRAINT authors_full_name_key UNIQUE (full_name);
        RAISE NOTICE 'Added UNIQUE constraint to authors.full_name';
    ELSE
        RAISE NOTICE 'UNIQUE constraint on authors.full_name already exists';
    END IF;
END$$;

-- ============================================================================
-- STEP 3: Verify constraints
-- ============================================================================

DO $$
DECLARE
    publisher_constraint_count INTEGER;
    author_constraint_count INTEGER;
BEGIN
    -- Check publishers constraint
    SELECT COUNT(*) INTO publisher_constraint_count
    FROM pg_constraint 
    WHERE conname = 'publishers_name_key' 
    AND connamespace = 'lms_core'::regnamespace;
    
    -- Check authors constraint
    SELECT COUNT(*) INTO author_constraint_count
    FROM pg_constraint 
    WHERE conname = 'authors_full_name_key' 
    AND connamespace = 'lms_core'::regnamespace;
    
    IF publisher_constraint_count > 0 AND author_constraint_count > 0 THEN
        RAISE NOTICE 'Migration 004 completed: UNIQUE constraints verified on publishers.name and authors.full_name';
    ELSE
        RAISE WARNING 'Migration 004 incomplete: Some constraints may be missing';
    END IF;
END$$;

-- ============================================================================
-- ROLLBACK INSTRUCTIONS (if needed)
-- ============================================================================

-- To rollback this migration:
-- ALTER TABLE lms_core.publishers DROP CONSTRAINT IF EXISTS publishers_name_key;
-- ALTER TABLE lms_core.authors DROP CONSTRAINT IF EXISTS authors_full_name_key;
