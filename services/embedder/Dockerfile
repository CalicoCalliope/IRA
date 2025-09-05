# Use official Python slim image
FROM python:3.11-slim
RUN apt-get update && apt-get install -y curl netcat-openbsd
RUN apt-get update && apt-get install -y curl netcat-openbsd bash

# Set working directory
WORKDIR /app

# Install system dependencies for PyTorch and FastAPI
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy only requirements first for caching
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the code
COPY . .

# Expose the service port
EXPOSE 5002

# Optional: copy .env for dev; in production, use Compose env_file
# COPY .env ./

# Start the service
CMD ["uvicorn", "src.app:app", "--host", "0.0.0.0", "--port", "5002"]
