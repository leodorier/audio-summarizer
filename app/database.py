import sqlite3
import json
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any, Tuple
from app.config import settings
from app.schemas import AudioRecordCreate

def get_db_connection(db_path: Optional[Path] = None) -> sqlite3.Connection:
    target_path = db_path or settings.DB_PATH
    target_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(target_path), timeout=30.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode = WAL;")
    conn.execute("PRAGMA synchronous = NORMAL;")
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn

def init_db(db_path: Optional[Path] = None):
    conn = get_db_connection(db_path)
    with conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS audio_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                original_filename TEXT NOT NULL,
                audio_file_path TEXT NOT NULL,
                audio_format TEXT NOT NULL,
                file_size INTEGER NOT NULL,
                duration_seconds REAL DEFAULT 0.0,
                transcript_file_path TEXT NOT NULL,
                summary_file_path TEXT NOT NULL,
                raw_transcript TEXT NOT NULL,
                summary_text TEXT NOT NULL,
                key_points TEXT DEFAULT '[]',     -- JSON array
                action_items TEXT DEFAULT '[]',   -- JSON array
                topics TEXT DEFAULT '[]',         -- JSON array
                language TEXT DEFAULT 'en',
                status TEXT NOT NULL DEFAULT 'completed',
                error_message TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_audio_created_at ON audio_records(created_at);")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_audio_status ON audio_records(status);")
    conn.close()

def _row_to_dict(row: sqlite3.Row) -> Dict[str, Any]:
    d = dict(row)
    for json_field in ["key_points", "action_items", "topics"]:
        if isinstance(d.get(json_field), str):
            try:
                d[json_field] = json.loads(d[json_field])
            except Exception:
                d[json_field] = []
        elif d.get(json_field) is None:
            d[json_field] = []
    # Ensure created_at and updated_at are string
    if d.get("created_at") is not None:
        d["created_at"] = str(d["created_at"])
    if d.get("updated_at") is not None:
        d["updated_at"] = str(d["updated_at"])
    return d

def add_audio_record(record: AudioRecordCreate, db_path: Optional[Path] = None) -> int:
    conn = get_db_connection(db_path)
    with conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO audio_records (
                title, original_filename, audio_file_path, audio_format,
                file_size, duration_seconds, transcript_file_path,
                summary_file_path, raw_transcript, summary_text,
                key_points, action_items, topics, language, status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            record.title,
            record.original_filename,
            record.audio_file_path,
            record.audio_format,
            record.file_size,
            record.duration_seconds,
            record.transcript_file_path,
            record.summary_file_path,
            record.raw_transcript,
            record.summary_text,
            json.dumps(record.key_points, ensure_ascii=False),
            json.dumps(record.action_items, ensure_ascii=False),
            json.dumps(record.topics, ensure_ascii=False),
            record.language,
            record.status
        ))
        record_id = cursor.lastrowid
    conn.close()
    return record_id

def get_audio_record_by_id(record_id: int, db_path: Optional[Path] = None) -> Optional[Dict[str, Any]]:
    conn = get_db_connection(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM audio_records WHERE id = ?", (record_id,))
    row = cursor.fetchone()
    conn.close()
    if not row:
        return None
    return _row_to_dict(row)

def get_audio_records(
    timeframe: str = "all",
    search_query: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    db_path: Optional[Path] = None
) -> Tuple[List[Dict[str, Any]], int]:
    conn = get_db_connection(db_path)
    cursor = conn.cursor()
    
    where_clauses = ["status = 'completed'"]
    params: List[Any] = []
    
    # Timeframe filtering
    clean_tf = timeframe.lower().strip()
    if clean_tf in ["last_week", "week", "7d"]:
        where_clauses.append("datetime(created_at) >= datetime('now', '-7 days')")
    elif clean_tf in ["last_month", "month", "30d"]:
        where_clauses.append("datetime(created_at) >= datetime('now', '-30 days')")
    elif clean_tf in ["last_year", "year", "365d"]:
        where_clauses.append("datetime(created_at) >= datetime('now', '-365 days')")
    
    # Search query
    if search_query and search_query.strip():
        q = f"%{search_query.strip()}%"
        where_clauses.append("(title LIKE ? OR raw_transcript LIKE ? OR summary_text LIKE ? OR topics LIKE ?)")
        params.extend([q, q, q, q])
    
    where_str = " WHERE " + " AND ".join(where_clauses)
    
    # Count total
    cursor.execute(f"SELECT COUNT(*) FROM audio_records{where_str}", params)
    total_count = cursor.fetchone()[0]
    
    # Select records
    query = f"""
        SELECT * FROM audio_records{where_str}
        ORDER BY created_at DESC
        LIMIT ? OFFSET ?
    """
    cursor.execute(query, params + [limit, offset])
    rows = cursor.fetchall()
    conn.close()
    
    records = [_row_to_dict(r) for r in rows]
    return records, total_count

def delete_audio_record(record_id: int, db_path: Optional[Path] = None) -> Optional[Dict[str, Any]]:
    conn = get_db_connection(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM audio_records WHERE id = ?", (record_id,))
    row = cursor.fetchone()
    if not row:
        conn.close()
        return None
    record = _row_to_dict(row)
    with conn:
        conn.execute("DELETE FROM audio_records WHERE id = ?", (record_id,))
    conn.close()
    return record

def get_app_stats(db_path: Optional[Path] = None) -> Dict[str, Any]:
    conn = get_db_connection(db_path)
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT 
            COUNT(*) as total_files,
            COALESCE(SUM(duration_seconds), 0.0) as total_duration_seconds,
            MAX(created_at) as latest_processed_at
        FROM audio_records
        WHERE status = 'completed'
    """)
    row = cursor.fetchone()
    
    cursor.execute("SELECT raw_transcript, topics FROM audio_records WHERE status = 'completed'")
    all_rows = cursor.fetchall()
    conn.close()
    
    total_words = 0
    unique_topics = set()
    for r in all_rows:
        if r["raw_transcript"]:
            total_words += len(r["raw_transcript"].split())
        if r["topics"]:
            try:
                top_list = json.loads(r["topics"]) if isinstance(r["topics"], str) else r["topics"]
                for t in top_list:
                    unique_topics.add(t.strip().lower())
            except Exception:
                pass
    
    return {
        "total_files": row["total_files"] or 0,
        "total_duration_seconds": round(float(row["total_duration_seconds"] or 0.0), 2),
        "total_words_transcribed": total_words,
        "total_topics": len(unique_topics),
        "latest_processed_at": str(row["latest_processed_at"]) if row["latest_processed_at"] else None
    }
