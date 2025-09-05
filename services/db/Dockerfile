# DB Service Dockerfile
FROM node:alpine

# Set working directory
WORKDIR /app

# Copy package files and install dependencies
COPY package*.json ./
RUN npm install --no-cache

# Copy the rest of the code
COPY . .

# Expose the service port (default 5001)
EXPOSE 5001

# Optional: copy .env (if you want env in container; can also use Compose)
# COPY .env ./

# Start the service
CMD ["npm", "run", "start"]