# Use Node 20 slim for fewer vulnerabilities
FROM node:alpine

# Set working directory
WORKDIR /app

# Copy package files first for caching
COPY package*.json ./
RUN npm install --no-cache

# Copy the rest of the source code
COPY . .

# Expose the port defined in .env (default 3000)
EXPOSE 3000

# Optional: copy .env if you want it inside container
# COPY .env ./

# Start the service
CMD ["npm", "run", "start"]