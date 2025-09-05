# Use official Node image
FROM node:20-slim

# Install dependencies
RUN apt-get update && apt-get install -y curl netcat-openbsd && rm -rf /var/lib/apt/lists/*

# Set working directory to incoming (where package.json & src/ live)
WORKDIR /app/incoming

# Copy package files first for caching
COPY incoming/package*.json ./
RUN npm install

# Copy the rest of the code
COPY incoming/ ./

# Install curl for healthcheck scripts
RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*

# Expose Coordinator port
EXPOSE 3000

# Script to wait for dependencies
COPY wait-for-services.sh /wait-for-services.sh
RUN chmod +x /wait-for-services.sh

# Start Coordinator after dependencies are ready
CMD ["/wait-for-services.sh", "db:5001", "embedder:5002", "ranker:5004", "llm:5003", "--", "npm", "run", "start"]