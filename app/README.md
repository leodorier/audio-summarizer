# Application Core (`app/`)

- `main.py`: FastAPI server, route controllers, static asset serving, and CORS middleware.
- `database.py`: SQLite database layer with connection handling, WAL mode, and parameterized queries.
- `schemas.py`: Pydantic models for API contracts and Gemini structured JSON outputs.
- `config.py`: Environment configuration and directory paths.
- `services/`:
  - `storage_manager.py`: File storage and markdown artifact generation.
  - `gemini_service.py`: Google Gemini multimodal audio transcription and extraction engine.
  - `processor.py`: End-to-end processing pipeline.
- `static/`: Single Page Application frontend (HTML5, Tailwind CSS, JavaScript).
