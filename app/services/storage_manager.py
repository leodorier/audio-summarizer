import re
import shutil
from datetime import datetime
from pathlib import Path
from typing import Optional, Tuple, Dict, Any
from app.config import settings
from app.schemas import GeminiAudioExtraction

def slugify(text: str) -> str:
    """Generate a clean URL-friendly filesystem slug."""
    text = text.lower().strip()
    text = re.sub(r'[^\w\s-]', '', text)
    text = re.sub(r'[\s_-]+', '-', text)
    return text.strip('-')[:80] or "audio"

def save_uploaded_audio(source_file_path: Path, original_filename: str) -> Tuple[Path, str]:
    """
    Saves an uploaded audio file into storage/uploads/ with a unique timestamped name.
    Returns (saved_path, format_extension).
    """
    ext = Path(original_filename).suffix.lower() or ".mp3"
    stem = slugify(Path(original_filename).stem)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    target_filename = f"{timestamp}_{stem}{ext}"
    target_path = settings.UPLOADS_DIR / target_filename
    
    shutil.copy2(source_file_path, target_path)
    return target_path, ext.lstrip(".")

def write_transcript_files(
    base_name: str,
    title: str,
    transcript: str,
    original_audio_name: str,
    duration_seconds: float = 0.0
) -> Tuple[Path, Path]:
    """
    Writes full verbatim transcript into both .txt and .md files in storage/transcripts/.
    """
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # 1. Plain text file
    txt_path = settings.TRANSCRIPTS_DIR / f"{base_name}_transcript.txt"
    txt_path.write_text(transcript.strip(), encoding="utf-8")
    
    # 2. Markdown file with metadata
    md_path = settings.TRANSCRIPTS_DIR / f"{base_name}_transcript.md"
    md_content = f"""---
title: "{title}"
audio_file: "{original_audio_name}"
duration_seconds: {duration_seconds}
date_transcribed: "{timestamp}"
type: transcript
---

# 🎙️ Full Transcript: {title}

**Original Audio**: `{original_audio_name}`  
**Transcribed**: {timestamp}  

---

{transcript.strip()}
"""
    md_path.write_text(md_content, encoding="utf-8")
    return txt_path, md_path

def write_summary_file(
    base_name: str,
    extraction: GeminiAudioExtraction,
    original_audio_name: str,
    duration_seconds: float = 0.0
) -> Path:
    """
    Writes the structured executive summary into storage/summaries/<base_name>_summary.md.
    """
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    summary_path = settings.SUMMARIES_DIR / f"{base_name}_summary.md"
    
    topics_formatted = ", ".join([f"`{t}`" for t in extraction.topics]) if extraction.topics else "None"
    
    key_points_block = "\n".join([f"- {p}" for p in extraction.key_points]) if extraction.key_points else "_No specific key points recorded._"
    action_items_block = "\n".join([f"- [ ] {a}" for a in extraction.action_items]) if extraction.action_items else "_No immediate action items._"
    
    content = f"""---
title: "{extraction.title}"
audio_file: "{original_audio_name}"
duration_seconds: {duration_seconds}
language: "{extraction.language}"
date_summarized: "{timestamp}"
type: summary
topics: {extraction.topics}
---

# 📋 Summary: {extraction.title}

> **Audio Reference**: `{original_audio_name}` | **Language**: `{extraction.language.upper()}` | **Date**: {timestamp}  
> **Tags**: {topics_formatted}

---

## 📌 Executive Summary

{extraction.executive_summary.strip()}

---

## 🔑 Key Points & Insights

{key_points_block}

---

## ⚡ Actionable Items & Takeaways

{action_items_block}

---

## 🔗 Related Files
- **Full Transcript**: `storage/transcripts/{base_name}_transcript.md`
- **Audio Source**: `storage/uploads/{original_audio_name}`
"""
    summary_path.write_text(content, encoding="utf-8")
    return summary_path

def delete_stored_files(audio_path: str, transcript_path: str, summary_path: str):
    """Safely removes physical storage files when a record is deleted."""
    for p_str in [audio_path, transcript_path, summary_path]:
        if p_str:
            p = Path(p_str)
            if p.exists() and p.is_file():
                try:
                    p.unlink()
                except Exception:
                    pass
            # Also check if matching .txt transcript exists
            if "_transcript.md" in p_str:
                txt_p = Path(p_str.replace("_transcript.md", "_transcript.txt"))
                if txt_p.exists() and txt_p.is_file():
                    try:
                        txt_p.unlink()
                    except Exception:
                        pass
