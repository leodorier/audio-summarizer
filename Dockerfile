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
COPY docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh
RUN chmod +x /usr/local/bin/docker-entrypoint.sh

# Create persistent storage directories
RUN mkdir -p /app/storage/uploads /app/storage/transcripts /app/storage/summaries

# Unprivileged runtime user. uid/gid 1000 matches the typical host bind-mount
# owner (e.g. `leo`), so the ./storage and ./app bind mounts stay writable.
RUN groupadd --gid 1000 appuser \
    && useradd --uid 1000 --gid 1000 --create-home --shell /usr/sbin/nologin appuser \
    && chown -R appuser:appuser /app

EXPOSE 8000

ENV PYTHONUNBUFFERED=1

# Starts as root only to normalise ./storage ownership, then drops to appuser.
ENTRYPOINT ["/usr/local/bin/docker-entrypoint.sh"]
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
