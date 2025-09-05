# Use official Node image
FROM node:alpine

# Set working directory
WORKDIR /app

# Copy package files first for caching
COPY package*.json ./
RUN npm install

# Copy the rest of the code
COPY . .

# Install curl for healthcheck scripts
RUN apk add --no-cache curl

# Expose Coordinator port
EXPOSE 3000

# Script to wait for dependencies
COPY wait-for-services.sh /wait-for-services.sh
RUN chmod +x /wait-for-services.sh

# Start Coordinator after dependencies are ready
CMD ["/wait-for-services.sh", "db:5001", "embedder:5002", "ranker:5004", "llm:5003", "--", "npm", "run", "start"]
