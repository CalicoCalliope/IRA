# Use official Node image
FROM node:20-slim

# Install system dependencies
RUN apt-get update && apt-get install -y curl netcat-openbsd && rm -rf /var/lib/apt/lists/*

# Install TypeScript globally
RUN npm install -g typescript

# Set working directory
WORKDIR /app

# Copy package.json and package-lock.json first for caching
COPY package*.json ./

# Install dependencies including devDependencies
RUN npm install --include=dev

# Copy the rest of the source code
COPY . .

# Build TypeScript AFTER copying source
RUN tsc

# Expose Coordinator port
EXPOSE 3000

# Make wait-for-services script executable
RUN chmod +x /app/wait-for-services.sh

# Start Coordinator
CMD ["/app/wait-for-services.sh", "db:5001", "embedder:5002", "ranker:5004", "llm:5003", "--", "npm", "run", "start"]