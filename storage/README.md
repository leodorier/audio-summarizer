# Storage Directory Layout

This directory houses all persistent application data, generated files, and databases:

- `uploads/`: Original uploaded speech audio files (`.mp3`, `.wav`, `.m4a`, etc.).
- `transcripts/`: Verbatim speech transcripts generated per audio in `.txt` and `.md` formats.
- `summaries/`: Markdown executive summaries (`.md`) formatted with frontmatter, key takeaways, action items, and topic tags.
- `audio_summarizer.db`: SQLite database file with WAL journal.
