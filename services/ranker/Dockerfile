# Use official Python slim image
FROM python:alpine

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