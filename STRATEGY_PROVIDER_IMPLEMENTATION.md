# Strategy Provider Implementation Summary
## Switching Concept for AI Strategy Generation

**Created by Mrityunjay Pandey, AIMarketer Pvt. Ltd.**

---

## Overview

The MAi platform now supports a **provider switching mechanism** for strategy generation, allowing you to easily switch between different AI providers:

- **Ollama** (Local deployment) - Recommended to start
- **OpenAI** (API-based) - For production

---

## Architecture

### Provider Abstraction Layer

```
StrategyAI Service
    │
    ├── StrategyProviderFactory
    │       │
    │       ├── OllamaStrategyProvider (Local)
    │       └── OpenAIStrategyProvider (API)
    │
    └── Strategy Generation Endpoint
```

### Key Components

1. **`services/shared/strategy_providers.py`**
   - Abstract `StrategyProvider` interface
   - `OllamaStrategyProvider` implementation
   - `OpenAIStrategyProvider` implementation
   - `StrategyProviderFactory` for provider selection

2. **Updated `services/strategy_ai_service/main.py`**
   - Uses provider factory to get appropriate provider
   - Generates strategy using selected provider
   - Returns provider info in response

---

## How It Works

### 1. Provider Selection

The system selects a provider based on:

1. **`STRATEGY_PROVIDER` environment variable**:
   - `ollama` → Use Ollama
   - `openai` → Use OpenAI
   - `auto` → Auto-detect (tries Ollama first, then OpenAI)

2. **Availability Check**:
   - Checks if Ollama is running (for local)
   - Checks if OpenAI API key is configured (for API)

3. **Fallback Mechanism**:
   - If selected provider unavailable → tries other provider
   - If both unavailable → uses config-based fallback

### 2. Strategy Generation Flow

```
User Request
    ↓
StrategyAI Service
    ↓
Provider Factory → Select Provider
    ↓
Ollama/OpenAI → Generate Strategy
    ↓
Parse Response → Format Strategy
    ↓
Return to User (with provider info)
```

---

## Configuration

### Environment Variables

```bash
# Provider Selection
STRATEGY_PROVIDER=ollama  # or 'openai' or 'auto'

# Ollama Configuration
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_STRATEGY_MODEL=llama2
OLLAMA_TIMEOUT=120

# OpenAI Configuration
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4
OPENAI_MAX_TOKENS=2000
OPENAI_BASE_URL=https://api.openai.com/v1
```

### Docker Compose

Ollama service is included with profile:

```bash
# Start Ollama
docker-compose --profile ollama up ollama -d

# Pull model
docker exec -it ollama ollama pull llama2
```

---

## API Endpoints

### Generate Strategy

```bash
POST /api/strategy/generate
Authorization: Bearer <token>
Content-Type: application/json

{
  "business_profile": {
    "business_name": "Tech Solutions",
    "industry": "technology",
    "company_size": "Medium",
    "geography": "North America",
    "marketing_goals": ["Lead Generation"]
  }
}
```

**Response includes provider info:**
```json
{
  "success": true,
  "strategy": {
    ...
    "provider_info": {
      "provider": "ollama",
      "model": "llama2"
    }
  }
}
```

### Check Available Providers

```bash
GET /api/strategy/providers
Authorization: Bearer <token>
```

**Response:**
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

## Switching Providers

### Method 1: Environment Variable

1. Update `.env`:
   ```bash
   STRATEGY_PROVIDER=openai  # or ollama
   ```

2. Restart service:
   ```bash
   docker-compose restart strategy_ai_service
   ```

### Method 2: Runtime Detection

The system automatically detects available providers and uses the best one based on:
- Provider preference (`STRATEGY_PROVIDER`)
- Provider availability
- Fallback chain

---

## Benefits

### ✅ Flexibility
- Easy switching between providers
- No code changes required
- Runtime provider selection

### ✅ Privacy (Ollama)
- 100% local processing
- No data sent to external APIs
- Complete data privacy

### ✅ Cost-Effective (Ollama)
- Free to use
- No API costs
- Unlimited usage

### ✅ Production Ready (OpenAI)
- Reliable API
- Fast response times
- Enterprise-grade

### ✅ Fallback Support
- Automatic fallback if provider unavailable
- Config-based fallback as last resort
- No service interruption

---

## Implementation Details

### Provider Interface

```python
class StrategyProvider(ABC):
    @abstractmethod
    async def generate_strategy(
        self,
        business_profile: Dict[str, Any],
        additional_context: Optional[str] = None
    ) -> Dict[str, Any]:
        pass
    
    @abstractmethod
    def is_available(self) -> bool:
        pass
```

### Factory Pattern

```python
provider = StrategyProviderFactory.create_provider()
strategy = await provider.generate_strategy(business_profile)
```

### Error Handling

- Provider unavailable → Try next provider
- API errors → Fallback to config-based
- Network errors → Retry with fallback

---

## Testing

### Test Ollama Provider

```bash
# 1. Start Ollama
docker-compose --profile ollama up ollama -d

# 2. Pull model
docker exec -it ollama ollama pull llama2

# 3. Set provider
export STRATEGY_PROVIDER=ollama

# 4. Test
curl -X POST "http://localhost:8000/api/strategy/generate" \
  -H "Authorization: Bearer TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"business_profile": {...}}'
```

### Test OpenAI Provider

```bash
# 1. Set API key
export OPENAI_API_KEY=sk-...

# 2. Set provider
export STRATEGY_PROVIDER=openai

# 3. Test
curl -X POST "http://localhost:8000/api/strategy/generate" \
  -H "Authorization: Bearer TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"business_profile": {...}}'
```

---

## Future Extensibility

The provider abstraction makes it easy to add more providers:

1. **Anthropic Claude**
2. **Google Gemini**
3. **Azure OpenAI**
4. **Custom Models**
5. **Hugging Face Models**

Just implement the `StrategyProvider` interface!

---

## Files Modified/Created

### New Files
- `services/shared/strategy_providers.py` - Provider abstraction
- `docs/STRATEGY_PROVIDER_SETUP.md` - Setup guide
- `scripts/setup_ollama.sh` - Ollama setup (Linux/Mac)
- `scripts/setup_ollama.ps1` - Ollama setup (Windows)

### Modified Files
- `services/strategy_ai_service/main.py` - Uses provider factory
- `docker-compose.yml` - Added Ollama service
- `env.example` - Added provider configuration
- `QUICK_START.md` - Updated with Ollama setup

---

## Next Steps

1. **Start with Ollama** (local, free, private)
2. **Test strategy generation** with your business profiles
3. **Switch to OpenAI** when ready for production
4. **Monitor provider performance** and costs
5. **Add more providers** as needed

---

**Created by Mrityunjay Pandey, AIMarketer Pvt. Ltd.**
