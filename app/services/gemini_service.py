import os
import time
import mimetypes
from pathlib import Path
from typing import Optional, Dict, Any
from google import genai
from google.genai import types
from app.config import settings
from app.schemas import GeminiAudioExtraction

AUDIO_MIME_TYPES = {
    ".mp3": "audio/mp3",
    ".wav": "audio/wav",
    ".m4a": "audio/m4a",
    ".ogg": "audio/ogg",
    ".flac": "audio/flac",
    ".aac": "audio/aac",
    ".wma": "audio/x-ms-wma",
    ".webm": "audio/webm",
}

GEMINI_STT_AND_SUMMARY_PROMPT = """
You are an expert Speech-to-Text transcription and executive intelligence summarization engine.

Analyze the provided audio recording carefully and perform two core tasks:

1. **Speech-to-Text (STT) Transcription**:
   - Provide a complete, highly accurate, and verbatim transcription of all spoken dialogue, speech, lectures, or conversations.
   - Format into clean, logical paragraphs. Do not truncate or skip sentences.
   - Preserve natural speaker flow and context.

2. **Executive Summarization & Knowledge Distillation**:
   - Formulate a clear, concise, and descriptive **title**.
   - Detect the primary **language** (ISO code e.g. 'en', 'fr', 'es', 'de').
   - Write an **executive_summary**: A dense, substantive, 2–4 paragraph conceptual synthesis of the core topics, arguments, context, and outcomes discussed in the audio.
   - Extract **key_points**: A structured list of the most critical ideas, concepts, findings, or arguments.
   - Extract **action_items**: Any concrete action items, next steps, instructions, decisions, or follow-ups mentioned (return empty list if purely informational).
   - Categorize **topics**: 3 to 7 relevant tags/keywords representing the subject matter.

Output must strictly conform to the JSON schema.
"""

def get_gemini_client(api_key: Optional[str] = None) -> genai.Client:
    key = api_key or settings.GEMINI_API_KEY or os.environ.get("GEMINI_API_KEY")
    if not key:
        raise ValueError("Gemini API Key is not configured. Please set GEMINI_API_KEY in .env or pass it explicitly.")
    return genai.Client(api_key=key)

def get_audio_mime_type(file_path: Path) -> str:
    ext = file_path.suffix.lower()
    return AUDIO_MIME_TYPES.get(ext, mimetypes.guess_type(str(file_path))[0] or "audio/mp3")

def transcribe_and_summarize_audio(
    audio_path: Path,
    custom_title: Optional[str] = None,
    api_key: Optional[str] = None,
    model_name: Optional[str] = None
) -> GeminiAudioExtraction:
    """
    Uploads audio to Gemini File API, extracts full verbatim transcription and structured summary,
    then cleans up the temporary file on Google servers.
    """
    if not audio_path.exists():
        raise FileNotFoundError(f"Audio file not found: {audio_path}")
    
    client = get_gemini_client(api_key)
    mime_type = get_audio_mime_type(audio_path)
    model = model_name or settings.GEMINI_MODEL
    
    # 1. Upload audio to Gemini File API
    remote_file = client.files.upload(
        file=str(audio_path),
        mime_type=mime_type
    )
    
    try:
        # Wait until file is processed if necessary (for large audio)
        while remote_file.state and remote_file.state.name == "PROCESSING":
            time.sleep(1.5)
            remote_file = client.files.get(name=remote_file.name)
        
        if remote_file.state and remote_file.state.name == "FAILED":
            raise RuntimeError(f"Gemini failed to process audio file: {remote_file.error}")
        
        prompt = GEMINI_STT_AND_SUMMARY_PROMPT
        if custom_title:
            prompt += f"\nNote: The user suggested the following topic/title context: '{custom_title}'."
        
        # 2. Generate structured transcription & summary
        response = client.models.generate_content(
            model=model,
            contents=[
                remote_file,
                prompt
            ],
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=GeminiAudioExtraction,
                temperature=0.2,
            )
        )
        
        result_json = response.text
        extraction = GeminiAudioExtraction.model_validate_json(result_json)
        
        if custom_title and (not extraction.title or extraction.title == "Untitled"):
            extraction.title = custom_title
            
        return extraction

    finally:
        # 3. Cleanup remote file from Gemini File API
        try:
            client.files.delete(name=remote_file.name)
        except Exception:
            pass
