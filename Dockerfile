FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim

# Install ffmpeg and system utilities
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install dependencies using uv
COPY requirements.txt .
RUN uv pip install --system --no-cache -r requirements.txt

# Copy application source
COPY app/ ./app/
COPY mcp/ ./mcp/

# Create persistent storage directories
RUN mkdir -p /app/storage/uploads /app/storage/transcripts /app/storage/summaries

EXPOSE 8000

ENV PYTHONUNBUFFERED=1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
