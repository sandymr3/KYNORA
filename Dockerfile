# Use a stable Python version that matches local environment to avoid pydantic-core build issues
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies needed by some Python packages
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       build-essential \
       gcc \
       libffi-dev \
       libssl-dev \
       pkg-config \
       git \
       curl \
       ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Copy only requirements first to leverage Docker layer caching
COPY requirements.txt /app/requirements.txt

# Upgrade pip and install dependencies
RUN python -m pip install --upgrade pip setuptools wheel
RUN pip install --no-cache-dir -r /app/requirements.txt

# Copy application source
COPY . /app

# Expose port and set default environment
ENV PORT=8000
EXPOSE 8000

# Default command uses environment PORT (Railway will set $PORT)
CMD ["sh", "-c", "uvicorn main:app --host=0.0.0.0 --port=${PORT:-8000} --workers 1 --timeout-keep-alive 120"]
