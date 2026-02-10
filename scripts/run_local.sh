#!/bin/bash
# Bash script to run all services locally without Docker
# Created by Mrityunjay Pandey, AIMarketer Pvt. Ltd.

echo "🚀 Starting MAi Services Locally (Without Docker)..."
echo ""

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "⚠️  Virtual environment not found. Creating..."
    python3 -m venv venv
    echo "✅ Virtual environment created"
    echo "📦 Installing dependencies..."
    source venv/bin/activate
    pip install -r requirements.txt
fi

# Activate virtual environment
echo "🔌 Activating virtual environment..."
source venv/bin/activate

# Check if .env exists
if [ ! -f ".env" ]; then
    echo "⚠️  .env file not found. Creating from env.example..."
    cp env.example .env
    echo "✅ .env file created. Please update it with your configuration."
fi

# Check if database is accessible
echo "🔍 Checking database connection..."
DB_URL=${DATABASE_URL:-"postgresql://mai_user:mai_password@postgres:5432/mai_db"}
echo "   Database URL: $DB_URL"

# Export environment variables
export DATABASE_URL=$DB_URL

# Start services in background
echo ""
echo "📡 Starting services..."
echo ""

cd services/auth_service && uvicorn main:app --reload --port 8001 > /dev/null 2>&1 &
echo "   ✅ Auth Service starting on port 8001"
sleep 1

cd ../licensing_service && uvicorn main:app --reload --port 8002 > /dev/null 2>&1 &
echo "   ✅ Licensing Service starting on port 8002"
sleep 1

cd ../strategy_ai_service && uvicorn main:app --reload --port 8003 > /dev/null 2>&1 &
echo "   ✅ StrategyAI Service starting on port 8003"
sleep 1

cd ../lead_enrichment_service && uvicorn main:app --reload --port 8004 > /dev/null 2>&1 &
echo "   ✅ Lead Enrichment Service starting on port 8004"
sleep 1

cd ../campaign_planner_service && uvicorn main:app --reload --port 8005 > /dev/null 2>&1 &
echo "   ✅ Campaign Planner Service starting on port 8005"
sleep 1

cd ../analytics_service && uvicorn main:app --reload --port 8006 > /dev/null 2>&1 &
echo "   ✅ Analytics Service starting on port 8006"
sleep 1

cd ../../api_gateway && uvicorn main:app --reload --port 8000 > /dev/null 2>&1 &
echo "   ✅ API Gateway starting on port 8000"
sleep 1

echo ""
echo "✅ All services started!"
echo ""
echo "📝 Service URLs:"
echo "   API Gateway:      http://localhost:8000"
echo "   Auth Service:     http://localhost:8001/docs"
echo "   Licensing:        http://localhost:8002/docs"
echo "   StrategyAI:       http://localhost:8003/docs"
echo "   Lead Enrichment:  http://localhost:8004/docs"
echo "   Campaign Planner: http://localhost:8005/docs"
echo "   Analytics:        http://localhost:8006/docs"
echo ""
echo "⚠️  Make sure PostgreSQL, MongoDB, and Redis are running!"
echo ""
echo "Press Ctrl+C to stop all services"

# Wait for interrupt
trap "echo ''; echo '🛑 Stopping all services...'; pkill -f 'uvicorn main:app'; echo '✅ All services stopped'; exit" INT

# Keep script running
wait
