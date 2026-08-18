import os
import shutil
import tempfile
from pathlib import Path
from typing import Optional, List
from contextlib import asynccontextmanager

from fastapi import (
    FastAPI, UploadFile, File, Form, HTTPException, Query,
    BackgroundTasks, status
)
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import (
    init_db, get_audio_records, get_audio_record_by_id,
    delete_audio_record, get_app_stats
)
from app.schemas import (
    AudioRecordResponse, AudioRecordListResponse, AudioRecordSummaryItem,
    AppStatsResponse
)
from app.services.processor import process_audio_file
from app.services.storage_manager import delete_stored_files

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize SQLite database on startup
    init_db()
    yield

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Speech-to-Text Transcription and Executive Knowledge Summarization Engine",
    lifespan=lifespan
)

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API Endpoints
@app.get("/api/health")
def health_check():
    return {
        "status": "healthy",
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "environment": settings.ENVIRONMENT
    }

@app.get("/api/stats", response_model=AppStatsResponse)
def get_stats():
    return get_app_stats()

@app.post("/api/upload", response_model=AudioRecordResponse, status_code=status.HTTP_201_CREATED)
async def upload_audio(
    file: UploadFile = File(...),
    title: Optional[str] = Form(None),
    api_key: Optional[str] = Form(None),
    model: Optional[str] = Form(None)
):
    """
    Upload an audio file (MP3, WAV, M4A, OGG, FLAC, AAC) for transcription and summarization.
    """
    filename = file.filename or "recording.mp3"
    ext = Path(filename).suffix.lower()
    allowed_exts = {".mp3", ".wav", ".m4a", ".ogg", ".flac", ".aac", ".wma", ".webm"}
    if ext not in allowed_exts:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported audio format '{ext}'. Allowed formats: {', '.join(sorted(allowed_exts))}"
        )
    
    # Save temporary file to disk for processing
    with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp:
        shutil.copyfileobj(file.file, tmp)
        tmp_path = Path(tmp.name)
    
    try:
        record = process_audio_file(
            source_audio_path=tmp_path,
            original_filename=filename,
            custom_title=title,
            api_key=api_key,
            model_name=model
        )
        return record
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Processing failed: {str(e)}")
    finally:
        if tmp_path.exists():
            tmp_path.unlink()

@app.get("/api/files", response_model=AudioRecordListResponse)
def list_audio_files(
    timeframe: str = Query("all", description="Filter by timeframe: 'all', 'last_week', 'last_month', 'last_year'"),
    search: Optional[str] = Query(None, description="Search query in title, transcript, summary, or topics"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0)
):
    """Retrieve list of processed audio records with timeframe filtering and search."""
    records, total = get_audio_records(
        timeframe=timeframe,
        search_query=search,
        limit=limit,
        offset=offset
    )
    
    items = []
    for r in records:
        summary = r.get("summary_text") or ""
        preview = (summary[:200] + "...") if len(summary) > 200 else summary
        items.append(AudioRecordSummaryItem(
            id=r["id"],
            title=r["title"],
            original_filename=r["original_filename"],
            audio_format=r["audio_format"],
            file_size=r["file_size"],
            duration_seconds=r["duration_seconds"],
            language=r.get("language", "en"),
            status=r["status"],
            summary_preview=preview,
            key_points_count=len(r.get("key_points", [])),
            action_items_count=len(r.get("action_items", [])),
            topics=r.get("topics", []),
            created_at=r["created_at"]
        ))
    
    return AudioRecordListResponse(
        items=items,
        total=total,
        timeframe=timeframe,
        search=search
    )

@app.get("/api/files/{record_id}", response_model=AudioRecordResponse)
def get_audio_record(record_id: int):
    """Retrieve full details of a specific audio record."""
    record = get_audio_record_by_id(record_id)
    if not record:
        raise HTTPException(status_code=404, detail="Audio record not found")
    return record

@app.get("/api/files/{record_id}/audio")
def stream_audio(record_id: int):
    """Stream or download the original audio file."""
    record = get_audio_record_by_id(record_id)
    if not record:
        raise HTTPException(status_code=404, detail="Audio record not found")
    
    audio_path = Path(record["audio_file_path"])
    if not audio_path.exists():
        raise HTTPException(status_code=404, detail="Audio file not found on disk")
    
    return FileResponse(
        path=str(audio_path),
        filename=record["original_filename"]
    )

@app.get("/api/files/{record_id}/transcript")
def download_transcript(record_id: int, format: str = Query("md", enum=["md", "txt"])):
    """Download the verbatim transcript as Markdown or plain text."""
    record = get_audio_record_by_id(record_id)
    if not record:
        raise HTTPException(status_code=404, detail="Audio record not found")
    
    transcript_path = Path(record["transcript_file_path"])
    if format == "txt":
        txt_path = transcript_path.parent / transcript_path.name.replace("_transcript.md", "_transcript.txt")
        if txt_path.exists():
            transcript_path = txt_path
    
    if not transcript_path.exists():
        raise HTTPException(status_code=404, detail="Transcript file not found on disk")
    
    return FileResponse(
        path=str(transcript_path),
        filename=transcript_path.name,
        media_type="text/markdown" if format == "md" else "text/plain"
    )

@app.get("/api/files/{record_id}/summary")
def download_summary(record_id: int):
    """Download the structured summary Markdown file."""
    record = get_audio_record_by_id(record_id)
    if not record:
        raise HTTPException(status_code=404, detail="Audio record not found")
    
    summary_path = Path(record["summary_file_path"])
    if not summary_path.exists():
        raise HTTPException(status_code=404, detail="Summary file not found on disk")
    
    return FileResponse(
        path=str(summary_path),
        filename=summary_path.name,
        media_type="text/markdown"
    )

@app.delete("/api/files/{record_id}", status_code=status.HTTP_200_OK)
def delete_file(record_id: int):
    """Delete audio record from database and delete storage files from disk."""
    record = delete_audio_record(record_id)
    if not record:
        raise HTTPException(status_code=404, detail="Audio record not found")
    
    delete_stored_files(
        audio_path=record.get("audio_file_path", ""),
        transcript_path=record.get("transcript_file_path", ""),
        summary_path=record.get("summary_file_path", "")
    )
    return {"message": f"Successfully deleted record #{record_id} and its associated files"}

# Mount Static Web UI
static_dir = settings.PROJECT_ROOT / "app" / "static"
if static_dir.exists():
    app.mount("/", StaticFiles(directory=str(static_dir), html=True), name="static")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host=settings.HOST, port=settings.PORT, reload=True)
