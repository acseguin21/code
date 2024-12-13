# Builder Stage
FROM python:3.9-slim AS builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libffi-dev \
    libssl-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

# Runtime Stage
FROM python:3.9-slim

WORKDIR /app

# Install runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    libsm6 \
    libxext6 \
    libglib2.0-0 \
    libgl1-mesa-glx \
    && rm -rf /var/lib/apt/lists/*

# Copy installed packages from builder
COPY --from=builder /usr/local/lib/python3.9/site-packages /usr/local/lib/python3.9/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application code
COPY . .

# Ensure scripts are executable
RUN chmod +x /usr/local/bin/compress_videos.sh

# Set environment variables
ENV FLASK_ENV=production
ENV LOG_LEVEL=WARNING

# Expose port
EXPOSE 5000

# Define entrypoint and command
ENTRYPOINT ["sh", "-c"]
CMD ["while true; do /usr/local/bin/compress_videos.sh; sleep 3600; done"] 