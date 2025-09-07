# DB Service Dockerfile
FROM node:20-slim

# Install required system packages
RUN apt-get update && apt-get install -y curl netcat-openbsd && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy package files and install dependencies
COPY package*.json ./

# Install dependencies and TypeScript globally
RUN npm install --no-cache \
    && npm install -g typescript

# Copy the rest of the code
COPY . .

# Compile TypeScript
RUN tsc

# Expose the service port (default 5001)
EXPOSE 5001

# Start the service
CMD ["npm", "run", "start"]