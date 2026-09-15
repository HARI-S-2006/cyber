# Backend Dockerfile for Cyber Threat Visualizer
FROM python:3.11-slim

# Install system dependencies for packet capture
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpcap-dev \
    tcpdump \
    net-tools \
    iproute2 \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create models directory
RUN mkdir -p /app/ml/models

# Expose API port
EXPOSE 8000

# Environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app

# Run as non-root user for security (but packet capture needs privileges)
# We'll run as root for packet capture but you can adjust for production
USER root

# Default command
CMD ["python", "-m", "api.main"]