# MAi by AIMarketer - Backend Setup & Usage Guide

**Created by Mrityunjay Pandey, AIMarketer Pvt. Ltd.**

## Overview

This is the backend API for MAi by AIMarketer, an AI-powered B2B Digital Marketing Platform. The backend provides comprehensive APIs for business profiling, AI-driven marketing strategy generation, lead scraping and enrichment, multi-channel campaign management, and analytics.

The active backend is the microservice stack fronted by the API Gateway. The API Gateway (port 8000) is the canonical entry point for all backend requests.

Legacy monolith files (`mai-backend-main.py`, `mai-backend-modules.py`) are deprecated and kept for reference only.

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- Docker & Docker Compose
- Git

### Installation

1. **Clone the repository**
   ```bash
   git clone <your-repo-url>
   cd mai-aimarketer-backend
   ```

2. **Set up environment variables**
   ```bash
   cp .env.example .env
   # Edit .env file with your API keys and configuration
   ```

3. **Using Docker Compose (Recommended)**
   ```bash
   docker-compose up --build
   ```

4. **Or Manual Installation**
   ```bash
   # Create virtual environment
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   
   # Install dependencies
   pip install -r requirements.txt
   
   # Start services manually
   # PostgreSQL, MongoDB, Redis must be running
   uvicorn main:app --reload --host 0.0.0.0 --port 8000
   ```

## 📚 API Documentation

Once the server is running, access the interactive API documentation:

### Gateway Routing Map (Canonical Entry Point)

| Gateway path | Service | Internal service route |
|---|---|---|
| `/api/auth/*` | Auth Service | `/api/auth/*` |
| `/api/admin/*` | Auth Service | `/api/admin/*` |
| `/api/licensing/*` | Licensing Service | `/api/licensing/*` |
| `/api/strategy/*` | StrategyAI Service | `/api/strategy/*` |
| `/api/leads/*` | Lead Enrichment Service | `/api/leads/*` |
| `/api/enrichment/*` | Lead Enrichment Service | `/api/enrichment/*` |
| `/api/campaigns/*` | Campaign Planner Service | `/api/campaigns/*` |
| `/api/analytics/*` | Analytics Service | `/api/analytics/*` |

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **Health Check**: http://localhost:8000/api/health

## 🏗️ Architecture

### Core Components

- **FastAPI**: Modern Python web framework for building APIs
- **PostgreSQL**: Primary database for structured data
- **MongoDB**: Document storage for templates and unstructured data
- **Redis**: Caching and task queue broker
- **Celery**: Background task processing
- **Docker**: Containerized deployment

### Modules

1. **Business Profile Module** (`/api/business-profile`)
   - Store and manage business information
   - Industry classification and goal tracking

2. **AI Strategy Generator** (`/api/generate-strategy`)
   - AI-powered marketing strategy recommendations
   - Channel optimization and budget allocation

3. **Lead Scraper** (`/api/scrape-leads`)
   - Google Maps business data extraction
   - Asynchronous processing with status tracking

4. **Data Enrichment** (`/api/upload-customers`)
   - Customer data enhancement via third-party APIs
   - Email, phone, and social media discovery

5. **Campaign Management** (`/api/create-campaign`)
   - Multi-channel campaign creation and scheduling
   - Social media, email, and WhatsApp integration

6. **Analytics & Reporting** (`/api/campaign-metrics`)
   - Performance tracking and ROI analysis
   - Downloadable reports and insights

7. **Template Library** (`/api/templates`)
   - Pre-built campaign templates
   - Industry-specific content

## 🔧 Configuration

### Environment Variables

Key environment variables to configure:

```bash
# API Keys (Required)
OPENAI_API_KEY=your-openai-key
SENDGRID_API_KEY=your-sendgrid-key
CLEARBIT_API_KEY=your-clearbit-key

# Database URLs
DATABASE_URL=postgresql://user:pass@localhost:5432/db
MONGODB_URI=mongodb://localhost:27017/templates
REDIS_URL=redis://localhost:6379/0

# Security
JWT_SECRET_KEY=your-secret-key
SECRET_KEY=your-app-secret
```

### Third-Party Integrations

The platform integrates with various services:

- **OpenAI GPT**: AI strategy generation
- **Clearbit/Hunter.io**: Data enrichment
- **SendGrid**: Email campaigns  
- **Facebook/LinkedIn APIs**: Social media posting
- **WhatsApp Business API**: WhatsApp campaigns

## 🧪 Testing

Run the test suite:

```bash
# Using pytest
pytest tests/

# With coverage
pytest --cov=app tests/

# Specific test file
pytest tests/test_business_profile.py
```

## 📊 Monitoring

### Application Monitoring

- **Health Check**: `/api/health`
- **Celery Flower**: http://localhost:5555 (task monitoring)
- **pgAdmin**: http://localhost:5050 (database admin)

### Logging

Logs are structured using `structlog` and can be configured via `LOG_LEVEL` environment variable.

## 🚀 Deployment

### Production Deployment

1. **Update environment variables**
   ```bash
   DEBUG=False
   DATABASE_URL=your-production-db-url
   CORS_ORIGINS=["https://yourdomain.com"]
   ```

2. **Deploy using Docker**
   ```bash
   docker-compose -f docker-compose.prod.yml up -d
   ```

3. **Or deploy to cloud platforms**
   - AWS ECS/Fargate
   - Google Cloud Run
   - Azure Container Instances
   - Kubernetes

### Security Considerations

- Use environment variables for all secrets
- Enable HTTPS in production
- Configure CORS appropriately
- Implement rate limiting
- Use secure JWT secret keys
- Regular security updates

## 🔄 Background Tasks

The application uses Celery for background processing:

- **Lead Scraping**: Asynchronous Google Maps data extraction
- **Data Enrichment**: Batch processing of customer data
- **Campaign Deployment**: Scheduled campaign execution
- **Analytics Updates**: Periodic metrics collection

Monitor tasks using Celery Flower: http://localhost:5555

## 📝 API Usage Examples

### 1. Create Business Profile

```bash
curl -X POST "http://localhost:8000/api/business-profile" \
  -H "Authorization: Bearer your-jwt-token" \
  -H "Content-Type: application/json" \
  -d '{
    "business_name": "Tech Solutions Inc",
    "industry": "Technology",
    "company_size": "Medium",
    "geography": "North America",
    "marketing_goals": ["Lead Generation", "Brand Awareness"]
  }'
```

### 2. Generate Marketing Strategy

```bash
curl -X POST "http://localhost:8000/api/generate-strategy" \
  -H "Authorization: Bearer your-jwt-token" \
  -H "Content-Type: application/json" \
  -d '{
    "business_profile": {
      "business_name": "Tech Solutions Inc",
      "industry": "Technology",
      "company_size": "Medium",
      "geography": "North America",
      "marketing_goals": ["Lead Generation"]
    }
  }'
```

### 3. Start Lead Scraping

```bash
curl -X POST "http://localhost:8000/api/scrape-leads" \
  -H "Authorization: Bearer your-jwt-token" \
  -H "Content-Type: application/json" \
  -d '{
    "location": "San Francisco, CA",
    "business_type": "Software Company",
    "max_results": 100
  }'
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

This project is proprietary software created by **Mrityunjay Pandey, AIMarketer Pvt. Ltd.**

## 🆘 Support

For technical support or questions:

- **Email**: support@aimarketer.com
- **Documentation**: Check the `/docs` endpoint
- **Issues**: Create GitHub issues for bugs

---

**MAi by AIMarketer** - Empowering B2B Marketing with AI

*Created by Mrityunjay Pandey, AIMarketer Pvt. Ltd.*
