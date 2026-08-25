FROM python:3.12-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    DEBIAN_FRONTEND=noninteractive

# Install system dependencies (FFmpeg is required for HLS stream handling)
RUN apt-get update && \
    apt-get install -y --no-install-recommends ffmpeg curl && \
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
