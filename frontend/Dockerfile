# Frontend Dockerfile for Cyber Threat Visualizer
FROM node:20-alpine

WORKDIR /app

# Copy package files
COPY package*.json ./

# Install dependencies
RUN npm ci

# Copy source code
COPY . .

# Build for production
RUN npm run build

# Expose port
EXPOSE 3000

# Start development server (for production, use a proper web server like nginx)
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]