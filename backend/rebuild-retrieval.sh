#!/bin/bash
# Rebuild Retrieval Service with Pinecone Support

echo "🔄 Rebuilding Retrieval Service..."

# Navigate to backend directory
cd "$(dirname "$0")"

# Stop existing container
echo "Stopping retrieval-service..."
docker compose stop retrieval-service

# Rebuild with new dependencies
echo "Building image with Pinecone support..."
docker compose build retrieval-service

# Start service
echo "Starting retrieval-service..."
docker compose up -d retrieval-service

# Wait for startup
sleep 10

# Check health
echo "Checking service health..."
curl -s http://localhost:8007/health | python3 -m json.tool

echo "✅ Retrieval service rebuild complete!"
echo "📊 Check logs: docker compose logs -f retrieval-service"
