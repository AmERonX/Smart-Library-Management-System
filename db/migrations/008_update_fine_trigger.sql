-- Migration: Update fine calculation trigger for better accuracy and duplicate prevention
-- Date: 2025-11-10
-- Description: Improves auto_fine_trigger() to use calendar days calculation and prevent duplicate fines

SET search_path TO lms_core;

-- Update the trigger function
CREATE OR REPLACE FUNCTION auto_fine_trigger() RETURNS TRIGGER AS $$
BEGIN
    -- Only calculate fine if the book is returned and it's overdue, and no fine exists yet
    IF NEW.return_date IS NOT NULL 
       AND NEW.due_date < NEW.return_date 
       AND NOT EXISTS (
           SELECT 1 FROM lms_core.fines WHERE borrow_id = NEW.borrow_id
       ) THEN
        -- Calculate fine based on full calendar days overdue (more accurate than EXTRACT)
        -- Use GREATEST to ensure at least 1 day fine for any overdue return
        INSERT INTO lms_core.fines(borrow_id, user_id, amount, status)
        VALUES (
            NEW.borrow_id,
            NEW.user_id, 
            GREATEST(1, (NEW.return_date::date - NEW.due_date::date)) * 1.00, -- At least 1 day, calculate full calendar days
            'pending'
        );
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

