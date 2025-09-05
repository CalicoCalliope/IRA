# Use official Python slim image
FROM python:alpine

# Set working directory
WORKDIR /app

# Copy requirements first (for caching)
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy app code
COPY app ./app
COPY src ./src

# Expose LLM service port
EXPOSE 5003

# Start FastAPI using Uvicorn
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "5003"]