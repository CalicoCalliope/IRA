# Use official Python slim image
FROM python:alpine

# Set working directory
WORKDIR /app

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
CMD ["python", "src/app.py"]