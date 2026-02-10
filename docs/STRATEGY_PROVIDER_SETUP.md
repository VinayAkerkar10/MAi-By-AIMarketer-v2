# Strategy Provider Configuration Guide
## Switching Between Ollama (Local) and OpenAI (API)

**Created by Mrityunjay Pandey, AIMarketer Pvt. Ltd.**

---

## Overview

The MAi StrategyAI service supports multiple AI providers through a provider switching mechanism. You can easily switch between:

- **Ollama** (Local deployment - recommended to start)
- **OpenAI** (API-based - for production)

---

## Provider Selection

The system uses the `STRATEGY_PROVIDER` environment variable to determine which provider to use:

- `ollama` - Use Ollama (local)
- `openai` - Use OpenAI API
- `auto` - Auto-detect (tries Ollama first, then OpenAI)

---

## Setup: Ollama (Local)

### 1. Install Ollama

**Option A: Docker (Recommended)**

```bash
# Start Ollama service
docker-compose --profile ollama up ollama -d

# Pull a model (e.g., llama2)
docker exec -it ollama ollama pull llama2

# Or pull other models
docker exec -it ollama ollama pull mistral
docker exec -it ollama ollama pull codellama
```

**Option B: Native Installation**

```bash
# Linux/Mac
curl -fsSL https://ollama.ai/install.sh | sh

# Windows
# Download from https://ollama.ai/download
```

### 2. Configure Environment

Add to your `.env` file:

```bash
STRATEGY_PROVIDER=ollama
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_STRATEGY_MODEL=llama2
OLLAMA_TIMEOUT=120
```

### 3. Verify Ollama is Running

```bash
# Check if Ollama is accessible
curl http://localhost:11434/api/tags

# Should return list of available models
```

### 4. Test Strategy Generation

```bash
curl -X POST "http://localhost:8000/api/strategy/generate" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "business_profile": {
      "business_name": "Test Company",
      "industry": "technology",
      "company_size": "Medium",
      "geography": "North America",
      "marketing_goals": ["Lead Generation"]
    }
  }'
```

---

## Setup: OpenAI (API)

### 1. Get OpenAI API Key

1. Sign up at https://platform.openai.com
2. Create an API key
3. Add credits to your account

### 2. Configure Environment

Add to your `.env` file:

```bash
STRATEGY_PROVIDER=openai
OPENAI_API_KEY=sk-your-api-key-here
OPENAI_MODEL=gpt-4
OPENAI_MAX_TOKENS=2000
```

### 3. Install OpenAI Library

```bash
pip install openai
```

Or it's already in `requirements.txt`.

### 4. Test Strategy Generation

Same API call as above - the system will automatically use OpenAI.

---

## Switching Providers

### Method 1: Environment Variable

Change `STRATEGY_PROVIDER` in `.env`:

```bash
# Switch to Ollama
STRATEGY_PROVIDER=ollama

# Switch to OpenAI
STRATEGY_PROVIDER=openai

# Auto-detect (tries Ollama first, then OpenAI)
STRATEGY_PROVIDER=auto
```

Restart the service:

```bash
docker-compose restart strategy_ai_service
```

### Method 2: Runtime Check

Check available providers:

```bash
curl -X GET "http://localhost:8000/api/strategy/providers" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

Response:
```json
{
  "success": true,
  "available_providers": ["ollama", "openai"],
  "current_provider": "ollama",
  "provider_info": {
    "ollama": {
      "type": "local",
      "base_url": "http://localhost:11434",
      "model": "llama2"
    },
    "openai": {
      "type": "api",
      "model": "gpt-4",
      "configured": true
    }
  }
}
```

---

## Recommended Models

### Ollama Models

- **llama2** - General purpose, good balance
- **mistral** - Fast and efficient
- **codellama** - Good for technical content
- **llama2:13b** - Larger, more capable (requires more RAM)

Pull models:
```bash
docker exec -it ollama ollama pull llama2
docker exec -it ollama ollama pull mistral
```

### OpenAI Models

- **gpt-4** - Most capable, best quality
- **gpt-3.5-turbo** - Faster, cheaper, good quality
- **gpt-4-turbo** - Latest, improved performance

---

## Provider Comparison

| Feature | Ollama (Local) | OpenAI (API) |
|---------|---------------|--------------|
| **Cost** | Free | Pay per use |
| **Privacy** | 100% Private | Data sent to API |
| **Speed** | Depends on hardware | Fast (cloud) |
| **Setup** | Requires local install | Just API key |
| **Offline** | ✅ Works offline | ❌ Requires internet |
| **Custom Models** | ✅ Can use custom | ❌ Fixed models |
| **Best For** | Development, privacy | Production, scale |

---

## Troubleshooting

### Ollama Not Available

```bash
# Check if Ollama is running
docker ps | grep ollama

# Check Ollama logs
docker logs ollama

# Test Ollama directly
curl http://localhost:11434/api/tags
```

### OpenAI API Errors

```bash
# Verify API key is set
echo $OPENAI_API_KEY

# Test API key
curl https://api.openai.com/v1/models \
  -H "Authorization: Bearer $OPENAI_API_KEY"
```

### Provider Fallback

If the selected provider is unavailable, the system will:
1. Try the selected provider
2. Fall back to the other provider if available
3. Use config-based fallback if both fail

---

## Advanced Configuration

### Custom Ollama Models

```bash
# Use a different model
OLLAMA_STRATEGY_MODEL=mistral

# Use a specific version
OLLAMA_STRATEGY_MODEL=llama2:13b
```

### Custom OpenAI Base URL

For using OpenAI-compatible APIs (e.g., Azure OpenAI, local proxies):

```bash
OPENAI_BASE_URL=https://your-custom-endpoint.com/v1
```

### Timeout Configuration

```bash
# Increase timeout for slower models
OLLAMA_TIMEOUT=300
```

---

## Production Recommendations

1. **Development**: Use Ollama (local, free, private)
2. **Staging**: Use Ollama or OpenAI (test both)
3. **Production**: 
   - Use OpenAI for reliability and speed
   - Or use Ollama on dedicated GPU server for privacy
   - Consider both with fallback mechanism

---

## Example: Using Both Providers

You can configure the system to try OpenAI first, fallback to Ollama:

```bash
STRATEGY_PROVIDER=auto
OPENAI_API_KEY=sk-...
OLLAMA_BASE_URL=http://localhost:11434
```

The system will:
1. Try OpenAI if API key is set
2. Fallback to Ollama if OpenAI fails
3. Use config-based fallback if both fail

---

**Created by Mrityunjay Pandey, AIMarketer Pvt. Ltd.**
