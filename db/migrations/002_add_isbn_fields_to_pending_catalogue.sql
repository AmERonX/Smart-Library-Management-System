-- Migration: Add isbn_10 and isbn_13 fields to pending_catalogue table
-- Date: 2025-10-09
-- Purpose: Support dual ISBN format in pending catalogue for better metadata tracking

BEGIN;

-- Add isbn_10 and isbn_13 columns to pending_catalogue
ALTER TABLE lms_core.pending_catalogue
ADD COLUMN IF NOT EXISTS isbn_10 VARCHAR(10),
ADD COLUMN IF NOT EXISTS isbn_13 VARCHAR(13);

-- Create indexes for faster lookups
CREATE INDEX IF NOT EXISTS idx_pending_catalogue_isbn_10 ON lms_core.pending_catalogue(isbn_10);
CREATE INDEX IF NOT EXISTS idx_pending_catalogue_isbn_13 ON lms_core.pending_catalogue(isbn_13);

-- Add comments
COMMENT ON COLUMN lms_core.pending_catalogue.isbn_10 IS 'ISBN-10 format (10 digits)';
COMMENT ON COLUMN lms_core.pending_catalogue.isbn_13 IS 'ISBN-13 format (13 digits, canonical)';

COMMIT;

-- Verification query
SELECT column_name, data_type, character_maximum_length
FROM information_schema.columns
WHERE table_schema = 'lms_core'
  AND table_name = 'pending_catalogue'
  AND column_name IN ('isbn', 'isbn_10', 'isbn_13');
