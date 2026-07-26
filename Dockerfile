FROM docker.io/library/python:3.12-slim

# Set working directory
WORKDIR /app

# Install runtime dependencies + dev dependencies
COPY requirements.txt .
COPY requirements-dev.txt .
RUN pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir -r requirements-dev.txt && \
    apt update && \
    apt install -y curl unzip ffmpeg && \
    rm -rf /var/lib/apt/lists/*

# Copy full application
COPY . /app/

RUN groupadd -g 1000 appgroup && \
    useradd -u 1000 -g appgroup -m -s /bin/bash appuser && \
    mkdir -p /app/downloads && \
    chown -R appuser:appgroup /app/

USER appuser

ENV PATH="/home/appuser/.deno/bin:${PATH}"
RUN curl -fsSL https://deno.land/install.sh | sh
