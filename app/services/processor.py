import os
from pathlib import Path
from typing import Optional, Dict, Any, Tuple
from mutagen import File as MutagenFile
from app.config import settings
from app.schemas import AudioRecordCreate, AudioRecordResponse, GeminiAudioExtraction
from app.database import add_audio_record, get_audio_record_by_id
from app.services.storage_manager import (
    slugify, save_uploaded_audio, write_transcript_files,
    write_summary_file, delete_stored_files
)
from app.services.gemini_service import transcribe_and_summarize_audio

def extract_audio_duration(file_path: Path) -> float:
    """Extracts duration of audio file in seconds using mutagen."""
    try:
        audio = MutagenFile(str(file_path))
        if audio and audio.info and hasattr(audio.info, "length"):
            return float(audio.info.length)
    except Exception:
        pass
    return 0.0

def process_audio_file(
    source_audio_path: Path,
    original_filename: Optional[str] = None,
    custom_title: Optional[str] = None,
    api_key: Optional[str] = None,
    model_name: Optional[str] = None,
    db_path: Optional[Path] = None
) -> Dict[str, Any]:
    """
    Main ingestion pipeline:
    1. Validates and saves audio file into storage/uploads/
    2. Extracts audio duration and file size
    3. Runs Gemini STT and structured summarization
    4. Writes transcript files (.txt, .md) and summary file (.md)
    5. Saves full record into SQLite database
    """
    if not source_audio_path.exists():
        raise FileNotFoundError(f"Source audio not found: {source_audio_path}")
    
    orig_name = original_filename or source_audio_path.name
    file_size = source_audio_path.stat().st_size
    duration = extract_audio_duration(source_audio_path)
    
    # 1. Save to permanent storage uploads directory
    saved_audio_path, audio_ext = save_uploaded_audio(source_audio_path, orig_name)
    
    try:
        # 2. Call Gemini for transcription & summarization
        extraction: GeminiAudioExtraction = transcribe_and_summarize_audio(
            audio_path=saved_audio_path,
            custom_title=custom_title,
            api_key=api_key,
            model_name=model_name
        )
        
        # 3. Generate base name for outputs
        clean_title_slug = slugify(extraction.title or Path(orig_name).stem)
        base_name = f"{saved_audio_path.stem}_{clean_title_slug}"[:100]
        
        # 4. Write transcript files (.txt & .md) and summary file (.md)
        txt_path, md_transcript_path = write_transcript_files(
            base_name=base_name,
            title=extraction.title,
            transcript=extraction.transcript,
            original_audio_name=saved_audio_path.name,
            duration_seconds=duration
        )
        
        summary_path = write_summary_file(
            base_name=base_name,
            extraction=extraction,
            original_audio_name=saved_audio_path.name,
            duration_seconds=duration
        )
        
        # 5. Insert record into database
        record_create = AudioRecordCreate(
            title=extraction.title,
            original_filename=orig_name,
            audio_file_path=str(saved_audio_path),
            audio_format=audio_ext,
            file_size=file_size,
            duration_seconds=duration,
            transcript_file_path=str(md_transcript_path),
            summary_file_path=str(summary_path),
            raw_transcript=extraction.transcript,
            summary_text=extraction.executive_summary,
            key_points=extraction.key_points,
            action_items=extraction.action_items,
            topics=extraction.topics,
            language=extraction.language,
            status="completed"
        )
        
        record_id = add_audio_record(record_create, db_path=db_path)
        record = get_audio_record_by_id(record_id, db_path=db_path)
        return record

    except Exception as e:
        # If processing fails, cleanup the uploaded file if needed
        if saved_audio_path.exists():
            try:
                saved_audio_path.unlink()
            except Exception:
                pass
        raise e
