import pytest
from datetime import datetime, timedelta
from app.database import (
    init_db, add_audio_record, get_audio_record_by_id,
    get_audio_records, delete_audio_record, get_app_stats,
    get_db_connection
)
from app.schemas import AudioRecordCreate

def test_db_init_and_crud(temp_storage):
    db_path = temp_storage["db"]
    
    # 1. Create a test record
    record = AudioRecordCreate(
        title="Weekly Engineering Sync",
        original_filename="sync_2026.mp3",
        audio_file_path=str(temp_storage["uploads"] / "sync.mp3"),
        audio_format="mp3",
        file_size=102400,
        duration_seconds=120.5,
        transcript_file_path=str(temp_storage["transcripts"] / "sync_transcript.md"),
        summary_file_path=str(temp_storage["summaries"] / "sync_summary.md"),
        raw_transcript="We reviewed the sprint tasks and deployment roadmap.",
        summary_text="Sprint review covered roadmap deliverables.",
        key_points=["Shipped v1.0", "Passed test suite"],
        action_items=["Deploy to VPS"],
        topics=["engineering", "roadmap"],
        language="en",
        status="completed"
    )
    
    rec_id = add_audio_record(record, db_path=db_path)
    assert rec_id > 0
    
    # 2. Retrieve by ID
    fetched = get_audio_record_by_id(rec_id, db_path=db_path)
    assert fetched is not None
    assert fetched["title"] == "Weekly Engineering Sync"
    assert fetched["duration_seconds"] == 120.5
    assert len(fetched["key_points"]) == 2
    assert "roadmap" in fetched["topics"]
    
    # 3. Test stats
    stats = get_app_stats(db_path=db_path)
    assert stats["total_files"] == 1
    assert stats["total_duration_seconds"] == 120.5
    assert stats["total_topics"] == 2
    
    # 4. Delete record
    deleted = delete_audio_record(rec_id, db_path=db_path)
    assert deleted is not None
    assert get_audio_record_by_id(rec_id, db_path=db_path) is None

def test_timeframe_filtering(temp_storage):
    db_path = temp_storage["db"]
    
    # Insert 3 records with different simulated timestamps
    conn = get_db_connection(db_path)
    now = datetime.now()
    
    # Record 1: Today
    add_audio_record(AudioRecordCreate(
        title="Today's Meeting", original_filename="today.mp3", audio_file_path="a", audio_format="mp3",
        file_size=100, duration_seconds=60, transcript_file_path="b", summary_file_path="c",
        raw_transcript="Today discussion", summary_text="Today summary", language="en"
    ), db_path=db_path)
    
    # Record 2: 15 days ago (in last_month and last_year, not in last_week)
    rec2_id = add_audio_record(AudioRecordCreate(
        title="Two Weeks Ago", original_filename="past.mp3", audio_file_path="a", audio_format="mp3",
        file_size=100, duration_seconds=60, transcript_file_path="b", summary_file_path="c",
        raw_transcript="Past discussion", summary_text="Past summary", language="en"
    ), db_path=db_path)
    past_15d = (now - timedelta(days=15)).strftime("%Y-%m-%d %H:%M:%S")
    with conn:
        conn.execute("UPDATE audio_records SET created_at = ? WHERE id = ?", (past_15d, rec2_id))

    # Record 3: 60 days ago (in last_year, not in last_month or last_week)
    rec3_id = add_audio_record(AudioRecordCreate(
        title="Two Months Ago", original_filename="old.mp3", audio_file_path="a", audio_format="mp3",
        file_size=100, duration_seconds=60, transcript_file_path="b", summary_file_path="c",
        raw_transcript="Old discussion", summary_text="Old summary", language="en"
    ), db_path=db_path)
    past_60d = (now - timedelta(days=60)).strftime("%Y-%m-%d %H:%M:%S")
    with conn:
        conn.execute("UPDATE audio_records SET created_at = ? WHERE id = ?", (past_60d, rec3_id))
    conn.close()

    # Query all
    records_all, count_all = get_audio_records(timeframe="all", db_path=db_path)
    assert count_all == 3
    
    # Query last_week (should only be today's record)
    records_week, count_week = get_audio_records(timeframe="last_week", db_path=db_path)
    assert count_week == 1
    assert records_week[0]["title"] == "Today's Meeting"
    
    # Query last_month (should be today + 15 days ago)
    records_month, count_month = get_audio_records(timeframe="last_month", db_path=db_path)
    assert count_month == 2
    
    # Query last_year (should be all 3)
    records_year, count_year = get_audio_records(timeframe="last_year", db_path=db_path)
    assert count_year == 3
    
    # Query search keyword
    records_search, count_search = get_audio_records(search_query="Old", db_path=db_path)
    assert count_search == 1
    assert records_search[0]["title"] == "Two Months Ago"
