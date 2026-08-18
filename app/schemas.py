from datetime import datetime
from typing import List, Optional, Any, Dict
from pydantic import BaseModel, Field, ConfigDict

class GeminiAudioExtraction(BaseModel):
    title: str = Field(description="Descriptive and concise title of the speech or conversation")
    language: str = Field(default="en", description="Detected language code (e.g. 'en', 'fr', 'es')")
    transcript: str = Field(description="Full verbatim Speech-to-Text transcript of the audio")
    executive_summary: str = Field(description="Comprehensive and dense conceptual summary of the spoken content")
    key_points: List[str] = Field(default_factory=list, description="List of primary arguments, facts, or concepts discussed")
    action_items: List[str] = Field(default_factory=list, description="Actionable takeaways, decisions, or follow-ups mentioned")
    topics: List[str] = Field(default_factory=list, description="Keywords and topic tags categorized from the audio")

class AudioRecordBase(BaseModel):
    title: str
    original_filename: str
    audio_format: str
    file_size: int
    duration_seconds: float = 0.0
    language: str = "en"
    status: str = "completed"

class AudioRecordCreate(AudioRecordBase):
    audio_file_path: str
    transcript_file_path: str
    summary_file_path: str
    raw_transcript: str
    summary_text: str
    key_points: List[str] = []
    action_items: List[str] = []
    topics: List[str] = []

class AudioRecordResponse(AudioRecordBase):
    id: int
    audio_file_path: str
    transcript_file_path: str
    summary_file_path: str
    raw_transcript: str
    summary_text: str
    key_points: List[str] = []
    action_items: List[str] = []
    topics: List[str] = []
    error_message: Optional[str] = None
    created_at: str
    updated_at: str

    model_config = ConfigDict(from_attributes=True)

class AudioRecordSummaryItem(BaseModel):
    id: int
    title: str
    original_filename: str
    audio_format: str
    file_size: int
    duration_seconds: float
    language: str
    status: str
    summary_preview: str
    key_points_count: int
    action_items_count: int
    topics: List[str]
    created_at: str

class AudioRecordListResponse(BaseModel):
    items: List[AudioRecordSummaryItem]
    total: int
    timeframe: str
    search: Optional[str] = None

class AppStatsResponse(BaseModel):
    total_files: int
    total_duration_seconds: float
    total_words_transcribed: int
    total_topics: int
    latest_processed_at: Optional[str] = None
