-- ============================================================================
-- Migration 007: Replace 'faculty' role with 'admin' role
-- ============================================================================
-- This migration:
-- 1. Adds 'admin' to the user_role ENUM
-- 2. Updates all existing 'faculty' users to 'admin'
-- 3. Removes 'faculty' from the ENUM (if possible, otherwise it remains unused)
-- ============================================================================

-- Step 1: Add 'admin' to the ENUM type
DO $$
BEGIN
    -- Check if 'admin' already exists in the ENUM
    IF NOT EXISTS (
        SELECT 1 FROM pg_enum 
        WHERE enumlabel = 'admin' 
        AND enumtypid = (SELECT oid FROM pg_type WHERE typname = 'user_role')
    ) THEN
        -- Add 'admin' to the ENUM
        ALTER TYPE lms_core.user_role ADD VALUE IF NOT EXISTS 'admin';
    END IF;
END $$;

-- Step 2: Update all existing 'faculty' users to 'admin'
UPDATE lms_core.users 
SET role = 'admin'::lms_core.user_role 
WHERE role = 'faculty'::lms_core.user_role;

-- Note: PostgreSQL does not support removing ENUM values directly.
-- The 'faculty' value will remain in the ENUM but unused.
-- Alternatively, we could recreate the ENUM type, but that's more complex.
-- For now, we'll just ensure 'admin' is used going forward.

COMMENT ON TYPE lms_core.user_role IS 'User roles: student, admin (replaces faculty), librarian';

