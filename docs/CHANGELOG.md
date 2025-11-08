# Changelog

All notable changes to this project will be documented in this file.

## [Unreleased]

### Added
- Centralized embedding dimension by introducing `EMBED_DIM = 768` in `services/vectorizer.py`.
- New AI module location under `services/ai/`.
  - `services/ai/faiss_sync.py` (migrated from `ai_services/faiss_sync.py`) now reads `EMBED_DIM` from `services/vectorizer.py`.
  - `services/ai/metadata_enhancer.py` (migrated from `ai_services/metadata_enhancer.py`).
- Setup verification now checks AI packages, keys, and artifact directories.
- Aggressive docs consolidation and link updates.

### Changed
- Updated imports to the new AI module paths:
  - `routes/search.py` now imports `from services.ai.faiss_sync import search as faiss_search`.
  - `services/embeddings.py` now imports `from services.ai import faiss_sync, metadata_enhancer`.
- Documentation refreshed:
  - SETUP_GUIDE.md includes AI keys/dirs and a Quick Reference section.
  - README.md updated with semantic search example and current project structure.
  - API_ENDPOINTS.md now contains a Frontend Integration overview.
  - WORKFLOW.md links consolidated to API_ENDPOINTS.md.

### Removed
- Legacy `ai_services/` package (hard cutover to `services/ai/`).
- Redundant docs consolidated and scheduled for deletion:
  - `docs/QUICK_REFERENCE.md` (merged into SETUP_GUIDE.md)
  - `docs/INSERTION_SERVICE_README.md` (merged into WORKFLOW.md)
  - `docs/LIBRARIAN_CONFIRMATION_README.md` (merged into WORKFLOW.md)
  - `docs/FRONTEND_INTEGRATION_GUIDE.md` (merged into API_ENDPOINTS.md)

### Notes
- Hard cutovers applied per project preference; no interim wrappers.
