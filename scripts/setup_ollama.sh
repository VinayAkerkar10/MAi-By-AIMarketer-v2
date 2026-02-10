#!/bin/bash
# Setup script for Ollama
# Created by Mrityunjay Pandey, AIMarketer Pvt. Ltd.

echo "🚀 Setting up Ollama for MAi Strategy Provider..."

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker is not running. Please start Docker first."
    exit 1
fi

# Start Ollama service
echo "📦 Starting Ollama service..."
docker-compose --profile ollama up ollama -d

# Wait for Ollama to be ready
echo "⏳ Waiting for Ollama to be ready..."
sleep 5

# Check if Ollama is accessible
if curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
    echo "✅ Ollama is running!"
else
    echo "⚠️  Ollama might still be starting. Please wait a moment."
    sleep 5
fi

# Pull default model
MODEL=${OLLAMA_STRATEGY_MODEL:-llama2}
echo "📥 Pulling model: $MODEL"
echo "   This may take a few minutes depending on your internet connection..."
docker exec -it ollama ollama pull $MODEL

# Verify model is available
echo "🔍 Verifying model availability..."
docker exec -it ollama ollama list

echo ""
echo "✅ Ollama setup complete!"
echo ""
echo "📝 Next steps:"
echo "   1. Set STRATEGY_PROVIDER=ollama in your .env file"
echo "   2. Restart strategy_ai_service: docker-compose restart strategy_ai_service"
echo "   3. Test with: curl http://localhost:8000/api/strategy/providers"
echo ""
echo "📚 Available models:"
echo "   - llama2 (default)"
echo "   - mistral (faster)"
echo "   - codellama (technical)"
echo ""
echo "   Pull more models with: docker exec -it ollama ollama pull <model-name>"
