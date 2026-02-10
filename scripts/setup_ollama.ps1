# PowerShell script for Ollama setup on Windows
# Created by Mrityunjay Pandey, AIMarketer Pvt. Ltd.

Write-Host "🚀 Setting up Ollama for MAi Strategy Provider..." -ForegroundColor Cyan

# Check if Docker is running
try {
    docker info | Out-Null
} catch {
    Write-Host "❌ Docker is not running. Please start Docker first." -ForegroundColor Red
    exit 1
}

# Start Ollama service
Write-Host "📦 Starting Ollama service..." -ForegroundColor Yellow
docker-compose --profile ollama up ollama -d

# Wait for Ollama to be ready
Write-Host "⏳ Waiting for Ollama to be ready..." -ForegroundColor Yellow
Start-Sleep -Seconds 5

# Check if Ollama is accessible
try {
    $response = Invoke-WebRequest -Uri "http://localhost:11434/api/tags" -UseBasicParsing -TimeoutSec 5
    Write-Host "✅ Ollama is running!" -ForegroundColor Green
} catch {
    Write-Host "⚠️  Ollama might still be starting. Please wait a moment." -ForegroundColor Yellow
    Start-Sleep -Seconds 5
}

# Pull default model
$model = if ($env:OLLAMA_STRATEGY_MODEL) { $env:OLLAMA_STRATEGY_MODEL } else { "llama2" }
Write-Host "📥 Pulling model: $model" -ForegroundColor Yellow
Write-Host "   This may take a few minutes depending on your internet connection..." -ForegroundColor Gray
docker exec -it ollama ollama pull $model

# Verify model is available
Write-Host "🔍 Verifying model availability..." -ForegroundColor Yellow
docker exec -it ollama ollama list

Write-Host ""
Write-Host "✅ Ollama setup complete!" -ForegroundColor Green
Write-Host ""
Write-Host "📝 Next steps:" -ForegroundColor Cyan
Write-Host "   1. Set STRATEGY_PROVIDER=ollama in your .env file"
Write-Host "   2. Restart strategy_ai_service: docker-compose restart strategy_ai_service"
Write-Host "   3. Test with: Invoke-WebRequest http://localhost:8000/api/strategy/providers"
Write-Host ""
Write-Host "📚 Available models:" -ForegroundColor Cyan
Write-Host "   - llama2 (default)"
Write-Host "   - mistral (faster)"
Write-Host "   - codellama (technical)"
Write-Host ""
Write-Host "   Pull more models with: docker exec -it ollama ollama pull <model-name>"
