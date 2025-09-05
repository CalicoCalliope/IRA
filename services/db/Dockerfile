# DB Service Dockerfile
FROM node:20-slim
RUN apt-get update && apt-get install -y curl netcat-openbsd && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy package files and install dependencies
COPY package*.json ./
RUN npm install --no-cache

# Copy the rest of the code
COPY . .

# Compile TypeScript
RUN npm run build

# Expose the service port (default 5001)
EXPOSE 5001

# Start the service
CMD ["npm", "run", "start"]