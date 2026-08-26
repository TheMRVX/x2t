FROM python:3.12-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    DEBIAN_FRONTEND=noninteractive

LABEL org.opencontainers.image.source="https://github.com/TheMRVX/x2t" \
      org.opencontainers.image.description="High-performance, multi-media downloader engine for Twitter / X posts" \
      org.opencontainers.image.licenses="AGPL-3.0-or-later"

# Install system dependencies (FFmpeg for media processing, gcc/build-essential for tgcrypto C-extensions)
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        ffmpeg \
        curl \
        build-essential \
        python3-dev && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy project files and install package in editable mode
COPY . .
RUN pip install --no-cache-dir -e .

# Create directory for database and temp media
RUN mkdir -p /app/data /app/downloads/temp_bot

# Default command to run the Telegram Bot
CMD ["python", "-m", "x2t.bot.main"]
