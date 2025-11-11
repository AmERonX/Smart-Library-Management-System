-- ============================================================================
-- SLMS DATABASE SCHEMA
-- ============================================================================
-- This schema reflects the current state after all migrations have been applied.
-- For existing databases, run migrations in order instead of recreating schema.
--
-- Migration History:
--   001_add_isbn_fields_and_core_tables.sql       - Added isbn_10, isbn_13 to books
--   002_add_isbn_fields_to_pending_catalogue.sql  - Added isbn_10, isbn_13 to pending_catalogue
--   003_rename_catalogue_audit_book_id_to_pending_id.sql - Renamed book_id to pending_id
--   004_add_unique_constraints_publishers_authors.sql - Added UNIQUE constraints
--
-- Last Updated: 2025-10-10
-- ============================================================================

-- DROP AND RECREATE SCHEMA
DROP SCHEMA IF EXISTS lms_core CASCADE;
CREATE SCHEMA lms_core;
SET search_path TO lms_core;

-- ENUM TYPES
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'user_role') THEN
        CREATE TYPE user_role AS ENUM ('student','faculty','librarian');
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'book_status') THEN
        CREATE TYPE book_status AS ENUM ('available','borrowed','reserved');
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'reservation_status') THEN
        CREATE TYPE reservation_status AS ENUM ('active','fulfilled','cancelled');
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'fine_status') THEN
        CREATE TYPE fine_status AS ENUM ('pending','paid');
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'source_type_enum') THEN
        CREATE TYPE source_type_enum AS ENUM ('title','description','keywords','toc');
    END IF;
END$$;

-- USERS TABLE
CREATE TABLE users (
    user_id       BIGSERIAL PRIMARY KEY,
    username      VARCHAR(50) UNIQUE NOT NULL,
    email         VARCHAR(100) UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    role          user_role NOT NULL,
    created_at    TIMESTAMP DEFAULT NOW(),
    updated_at    TIMESTAMP DEFAULT NOW()
);

-- AUTHORS TABLE
CREATE TABLE authors (
    author_id   BIGSERIAL PRIMARY KEY,
    full_name   TEXT UNIQUE NOT NULL,  -- UNIQUE constraint added via migration 004
    bio         TEXT
);

-- PUBLISHERS TABLE
CREATE TABLE publishers (
    publisher_id BIGSERIAL PRIMARY KEY,
    name         TEXT UNIQUE NOT NULL  -- UNIQUE constraint added via migration 004
);

-- CATEGORIES TABLE
CREATE TABLE categories (
    category_id      BIGSERIAL PRIMARY KEY,
    name             TEXT NOT NULL 
);

-- BOOKS TABLE
CREATE TABLE books (
    book_id          BIGSERIAL PRIMARY KEY,
    title            TEXT NOT NULL,
    isbn             VARCHAR(20) UNIQUE,  -- Legacy ISBN field (backward compatibility)
    isbn_10          VARCHAR(10) UNIQUE,  -- ISBN-10 format (added via migration 001)
    isbn_13          VARCHAR(13) UNIQUE,  -- ISBN-13 format, canonical identifier (added via migration 001)
    publisher_id     BIGINT REFERENCES publishers(publisher_id),
    publication_year INT,
    edition         VARCHAR(50),
    total_copies     INT DEFAULT 1,
    available_copies INT DEFAULT 1,
    status           book_status DEFAULT 'available',
    cover_url        TEXT,
    -- page_count     INT,  -- Commented for future: AI comparisons/recommendations
    created_at       TIMESTAMP DEFAULT NOW(),
    updated_at       TIMESTAMP DEFAULT NOW(),
    CHECK (available_copies <= total_copies AND available_copies >= 0)
);

-- Comments for books table columns (added via migration 001)
COMMENT ON COLUMN books.isbn IS 'Legacy ISBN field (kept for backward compatibility)';
COMMENT ON COLUMN books.isbn_10 IS 'ISBN-10 format (10 digits)';
COMMENT ON COLUMN books.isbn_13 IS 'ISBN-13 format (13 digits, canonical identifier)';

-- BOOK_AUTHORS TABLE
CREATE TABLE book_authors (
    book_id   BIGINT REFERENCES books(book_id) ON DELETE CASCADE,
    author_id BIGINT REFERENCES authors(author_id) ON DELETE CASCADE,
    PRIMARY KEY(book_id, author_id)
);

-- BOOK_CATEGORIES TABLE
CREATE TABLE book_categories (
    book_id     BIGINT REFERENCES books(book_id) ON DELETE CASCADE,
    category_id BIGINT REFERENCES categories(category_id) ON DELETE CASCADE,
    PRIMARY KEY(book_id, category_id)
);

-- BORROW RECORDS TABLE
CREATE TABLE borrow_records (
    borrow_id   BIGSERIAL PRIMARY KEY,
    user_id     BIGINT REFERENCES users(user_id) ON DELETE CASCADE,
    book_id     BIGINT REFERENCES books(book_id) ON DELETE CASCADE,
    borrow_date TIMESTAMP DEFAULT NOW(),
    due_date    TIMESTAMP NOT NULL,
    return_date TIMESTAMP,
    CHECK (due_date > borrow_date)
);

-- RESERVATIONS TABLE
CREATE TABLE reservations (
    reservation_id  BIGSERIAL PRIMARY KEY,
    user_id         BIGINT REFERENCES users(user_id) ON DELETE CASCADE,
    book_id         BIGINT REFERENCES books(book_id) ON DELETE CASCADE,
    reservation_date TIMESTAMP DEFAULT NOW(),
    expiry_date     TIMESTAMP,
    status          reservation_status DEFAULT 'active'
);

-- FINES TABLE
CREATE TABLE fines (
    fine_id    BIGSERIAL PRIMARY KEY,
    borrow_id  BIGINT UNIQUE REFERENCES borrow_records(borrow_id) ON DELETE CASCADE,
    user_id    BIGINT REFERENCES users(user_id) ON DELETE CASCADE,
    amount     DECIMAL(10,2) NOT NULL,
    issue_date TIMESTAMP DEFAULT NOW(),
    paid_date  TIMESTAMP,
    status     fine_status DEFAULT 'pending'
);

-- BOOK_METADATA TABLE
CREATE TABLE book_metadata (
    book_id     BIGINT PRIMARY KEY REFERENCES books(book_id) ON DELETE CASCADE,
    description TEXT,
    toc         TEXT,
    keywords    TEXT[]
);

-- PENDING_CATALOGUE TABLE (Librarian Confirmation Workflow)
CREATE TABLE pending_catalogue (
    id              SERIAL PRIMARY KEY,
    isbn            VARCHAR(20),  -- Legacy ISBN field (backward compatibility)
    isbn_10         VARCHAR(10),  -- ISBN-10 format (added via migration 002)
    isbn_13         VARCHAR(13),  -- ISBN-13 format, canonical identifier (added via migration 002)
    title           TEXT NOT NULL,
    authors         JSONB,
    total_copies    INT NOT NULL DEFAULT 1,
    raw_metadata    JSONB,
    output_json     JSONB,
    status          VARCHAR(30) NOT NULL DEFAULT 'pending',
    created_at      TIMESTAMP DEFAULT NOW(),
    updated_at      TIMESTAMP,
    CHECK (total_copies >= 1)
);

-- Comments for pending_catalogue table columns (added via migration 002)
COMMENT ON COLUMN pending_catalogue.isbn IS 'Legacy ISBN field (backward compatibility)';
COMMENT ON COLUMN pending_catalogue.isbn_10 IS 'ISBN-10 format (10 digits)';
COMMENT ON COLUMN pending_catalogue.isbn_13 IS 'ISBN-13 format (13 digits, canonical identifier)';

-- CATALOGUE_AUDIT TABLE (Audit Logging for Traceability)
CREATE TABLE catalogue_audit (
    id          SERIAL PRIMARY KEY,
    pending_id  INT NOT NULL REFERENCES pending_catalogue(id) ON DELETE CASCADE,  -- Renamed from book_id via migration 003
    action      VARCHAR(50) NOT NULL,
    source      VARCHAR(50) NOT NULL,
    details     TEXT,
    timestamp   TIMESTAMP DEFAULT NOW()
);

-- BOOK_EMBEDDINGS TABLE (Commented for future: AI vector search)
-- CREATE EXTENSION IF NOT EXISTS vector;
-- CREATE TABLE book_embeddings (
--     embedding_id  BIGSERIAL PRIMARY KEY,
--     book_id       BIGINT REFERENCES books(book_id) ON DELETE CASCADE,
--     embedding     VECTOR(384),
--     source_type   source_type_enum,
--     created_at    TIMESTAMP DEFAULT NOW()
-- );

-- REVIEWS TABLE (Commented for future: AI recommendations via ratings)
-- CREATE TABLE reviews (
--     review_id    BIGSERIAL PRIMARY KEY,
--     user_id      BIGINT REFERENCES users(user_id) ON DELETE CASCADE,
--     book_id      BIGINT REFERENCES books(book_id) ON DELETE CASCADE,
--     rating       INT CHECK (rating BETWEEN 1 AND 5),
--     comment      TEXT,
--     created_at   TIMESTAMP DEFAULT NOW()
-- );



-- INDEXES
CREATE INDEX idx_books_publisher ON books(publisher_id);
CREATE INDEX idx_books_isbn_10 ON books(isbn_10); 
CREATE UNIQUE INDEX idx_books_isbn_13 ON books(isbn_13);  
CREATE INDEX idx_borrow_user ON borrow_records(user_id);
CREATE INDEX idx_borrow_book ON borrow_records(book_id);
CREATE INDEX idx_reserve_user ON reservations(user_id);
CREATE INDEX idx_reserve_book ON reservations(book_id);
CREATE INDEX idx_pending_catalogue_status ON pending_catalogue(status);
CREATE INDEX idx_pending_catalogue_isbn ON pending_catalogue(isbn);
CREATE INDEX idx_pending_catalogue_isbn_10 ON pending_catalogue(isbn_10); 
CREATE INDEX idx_pending_catalogue_isbn_13 ON pending_catalogue(isbn_13);  
CREATE INDEX idx_catalogue_audit_pending_id ON catalogue_audit(pending_id);  -- Renamed from book_id via migration 003
CREATE INDEX idx_catalogue_audit_action ON catalogue_audit(action);
CREATE INDEX idx_catalogue_audit_timestamp ON catalogue_audit(timestamp);
--CREATE INDEX idx_embeddings_book ON book_embeddings(book_id);  -- For commented embeddings table
CREATE UNIQUE INDEX idx_active_reservations ON reservations(user_id, book_id) WHERE status = 'active';


-- VIEWS
CREATE VIEW active_borrows AS
SELECT b.borrow_id, u.username, bk.title, b.borrow_date, b.due_date
FROM borrow_records b
JOIN users u ON b.user_id = u.user_id
JOIN books bk ON b.book_id = bk.book_id
WHERE b.return_date IS NULL;

CREATE VIEW available_books AS
SELECT bk.book_id, bk.title, bk.publication_year
FROM books bk
WHERE bk.status = 'available';


-- TRIGGER FUNCTION FOR AUTOMATIC FINE CREATION
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


-- TRIGGER ON BORROW_RECORDS
CREATE TRIGGER borrow_return_trigger
AFTER UPDATE OF return_date ON borrow_records
FOR EACH ROW
EXECUTE FUNCTION auto_fine_trigger();


-- TRIGGER FUNCTION FOR UPDATED_AT
CREATE OR REPLACE FUNCTION update_timestamp() RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;


-- TRIGGERS FOR UPDATED_AT
CREATE TRIGGER update_users_ts
BEFORE UPDATE ON users
FOR EACH ROW
EXECUTE FUNCTION update_timestamp();

CREATE TRIGGER update_books_ts
BEFORE UPDATE ON books
FOR EACH ROW
EXECUTE FUNCTION update_timestamp();




-- TRIGGER FUNCTION FOR BOOK STATUS CONSISTENCY
CREATE OR REPLACE FUNCTION update_book_status() RETURNS TRIGGER AS $$
BEGIN
    NEW.status = CASE
        WHEN NEW.available_copies > 0 THEN 'available'
        WHEN EXISTS (SELECT 1 FROM reservations WHERE book_id = NEW.book_id AND status = 'active') THEN 'reserved'
        ELSE 'borrowed'
    END;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;


-- TRIGGER FOR BOOK STATUS
CREATE TRIGGER book_status_trigger
BEFORE UPDATE OF available_copies ON books
FOR EACH ROW
EXECUTE FUNCTION update_book_status();


-- STORED PROCEDURE FOR CONCURRENCY-CONTROLLED BORROWING
CREATE OR REPLACE FUNCTION borrow_book(p_user_id BIGINT, p_book_id BIGINT, p_due_date TIMESTAMP)
RETURNS BOOLEAN AS $$
DECLARE
    v_available_copies INT;
BEGIN
    -- Lock the book row to prevent concurrent updates
    SELECT available_copies INTO v_available_copies
    FROM books
    WHERE book_id = p_book_id FOR UPDATE;

    IF v_available_copies > 0 THEN
        -- Update available copies
        UPDATE books
        SET available_copies = available_copies - 1,
            status = CASE WHEN available_copies = 1 THEN 'borrowed' ELSE status END
        WHERE book_id = p_book_id;

        -- Insert borrow record
        INSERT INTO borrow_records (user_id, book_id, borrow_date, due_date, return_date)
        VALUES (p_user_id, p_book_id, NOW(), p_due_date, NULL);

        RETURN TRUE;
    ELSE
        -- Book not available, add to reservations
        INSERT INTO reservations (user_id, book_id, reservation_date, status)
        VALUES (p_user_id, p_book_id, NOW(), 'active');
        RETURN FALSE;
    END IF;
EXCEPTION
    WHEN OTHERS THEN
        RAISE NOTICE 'Error borrowing book: %', SQLERRM;
        RETURN FALSE;
END;
$$ LANGUAGE plpgsql;


