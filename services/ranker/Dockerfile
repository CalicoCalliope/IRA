# Use official Python slim image
FROM python:3.11-slim
RUN apt-get update && apt-get install -y curl netcat-openbsd
RUN apt-get update && apt-get install -y curl netcat-openbsd bash

# Set working directory
WORKDIR /app

# Copy requirements first for caching
COPY requirements.txt ./ 
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the code
COPY app ./app
COPY src ./src

# Expose service port
EXPOSE 5004

# Start the FastAPI service with Uvicorn
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "5004"]