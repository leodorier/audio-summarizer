# 📖 Documentation & Architecture Specifications

## 🎯 Overview
This directory contains architectural specifications, user guides, and integration references for the **Audio Summarizer** platform.

---

## 📂 Contents
- **`ARCHITECTURE.md`**: Detailed system architecture, data flow diagrams (audio upload $\rightarrow$ storage $\rightarrow$ Gemini 2.5 Flash File API $\rightarrow$ SQLite metadata $\rightarrow$ Markdown persistence), and authentication security specifications.
- **`API.md`**: Complete REST API specifications for `/api/upload`, `/api/files`, `/api/stats`, and `/api/settings/verify-gemini`.
- **`MCP.md`**: Specifications for the FastMCP tool endpoints (`add_mp3_file`, `list_files`, `query_files`).
