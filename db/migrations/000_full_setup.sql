-- Master migration runner: executes all numbered migrations in order.
-- Usage:
--   psql -h localhost -p 5432 -U postgres -d slms -f db/migrations/000_full_setup.sql

\set ON_ERROR_STOP on

\echo '------------------------------------------------------------'
\echo '* Rebuilding base schema from Schema/db_files.sql'
\ir ../Schema/db_files.sql

\echo '------------------------------------------------------------'
\echo '* Running 001_add_isbn_fields_and_core_tables.sql'
\ir 001_add_isbn_fields_and_core_tables.sql

\echo '------------------------------------------------------------'
\echo '* Running 002_add_isbn_fields_to_pending_catalogue.sql'
\ir 002_add_isbn_fields_to_pending_catalogue.sql

\echo '------------------------------------------------------------'
\echo '* Running 003_rename_catalogue_audit_book_id_to_pending_id.sql'
\ir 003_rename_catalogue_audit_book_id_to_pending_id.sql

\echo '------------------------------------------------------------'
\echo '* Running 004_add_unique_constraints_publishers_authors.sql'
\ir 004_add_unique_constraints_publishers_authors.sql

\echo '------------------------------------------------------------'
\echo '* Running 005_migration_faiss_map.sql'
\ir 005_migration_faiss_map.sql

\echo '------------------------------------------------------------'
\echo '* Running 006_add_enhanced_metadata_to_books.sql'
\ir 006_add_enhanced_metadata_to_books.sql

\echo '------------------------------------------------------------'
\echo '* Running 007_replace_faculty_with_admin.sql'
\ir 007_replace_faculty_with_admin.sql

\echo '------------------------------------------------------------'
\echo '* All migrations completed successfully.'

