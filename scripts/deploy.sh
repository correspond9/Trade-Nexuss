#!/bin/bash

# Deployment script for Broking Terminal V2 Backend
set -e

echo "🚀 Starting deployment of Broking Terminal V2 Backend..."

# Check if environment file exists
if [ ! -f .env ]; then
    echo "❌ Error: .env file not found. Please create it from .env.example"
    exit 1
fi

# Pull latest changes
echo "📥 Pulling latest changes..."
git pull origin main

# Build and run with Docker Compose
echo "🐳 Building Docker containers..."
docker-compose -f docker-compose.prod.yml build

# Stop existing containers
echo "🛑 Stopping existing containers..."
docker-compose -f docker-compose.prod.yml down

# Start new containers
echo "▶️ Starting new containers..."
docker-compose -f docker-compose.prod.yml up -d

# Wait for health check
echo "🏥 Waiting for health check..."
sleep 30

# Check health
if curl -f http://localhost:8000/health; then
    echo "✅ Deployment successful!"
    echo "🌐 API is available at: http://localhost:8000"
    echo "📚 Documentation at: http://localhost:8000/docs"
else
    echo "❌ Health check failed. Check logs:"
    docker-compose -f docker-compose.prod.yml logs backend
    exit 1
fi

echo "🎉 Deployment completed successfully!"
