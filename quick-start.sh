#!/bin/bash

# LLM Orchestrator Quick Start Script
# This script sets up the LLM Orchestrator with minimal configuration

set -e

echo "🚀 LLM Orchestrator Quick Start"
echo "================================"

# Check if running as root
if [[ $EUID -eq 0 ]]; then
   echo "❌ This script should not be run as root"
   exit 1
fi

# Check prerequisites
echo "🔍 Checking prerequisites..."

# Check Docker
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed. Please install Docker first."
    echo "   Visit: https://docs.docker.com/get-docker/"
    exit 1
fi

# Check Docker Compose
if ! docker compose version &> /dev/null; then
    echo "❌ Docker Compose is not available. Please install Docker Compose."
    exit 1
fi

# Check if Docker daemon is running
if ! docker info &> /dev/null; then
    echo "❌ Docker daemon is not running. Please start Docker."
    exit 1
fi

echo "✅ Prerequisites check passed"

# Create .env file if it doesn't exist
if [ ! -f .env ]; then
    echo "⚙️ Creating environment configuration..."
    cp .env.example .env
    
    # Generate secure passwords
    POSTGRES_PASSWORD=$(openssl rand -base64 32 | tr -d "=+/" | cut -c1-25)
    NEO4J_PASSWORD=$(openssl rand -base64 32 | tr -d "=+/" | cut -c1-25)
    N8N_PASSWORD=$(openssl rand -base64 32 | tr -d "=+/" | cut -c1-25)
    WEBUI_SECRET=$(openssl rand -base64 32)
    LANGFUSE_SECRET=$(openssl rand -base64 32)
    LANGFUSE_PUBLIC="pk-lf-$(openssl rand -base64 32 | tr -d "=+/" | cut -c1-25)"
    LANGFUSE_SALT=$(openssl rand -base64 16)
    JWT_SECRET=$(openssl rand -base64 32)
    ENCRYPTION_KEY=$(openssl rand -base64 32)
    
    # Update .env file with generated secrets
    sed -i "s/your_secure_postgres_password_here/$POSTGRES_PASSWORD/" .env
    sed -i "s/your_secure_neo4j_password_here/$NEO4J_PASSWORD/" .env
    sed -i "s/your_secure_n8n_password_here/$N8N_PASSWORD/" .env
    sed -i "s/your_secure_webui_secret_here/$WEBUI_SECRET/" .env
    sed -i "s/sk-lf-your_secret_key_here/$LANGFUSE_SECRET/" .env
    sed -i "s/pk-lf-your_public_key_here/$LANGFUSE_PUBLIC/" .env
    sed -i "s/your_random_salt_here/$LANGFUSE_SALT/" .env
    sed -i "s/your_jwt_secret_here/$JWT_SECRET/" .env
    sed -i "s/your_encryption_key_here/$ENCRYPTION_KEY/" .env
    
    echo "✅ Environment configuration created"
else
    echo "ℹ️ Using existing .env configuration"
fi

# Detect GPU
echo "🔍 Detecting GPU configuration..."
if command -v nvidia-smi &> /dev/null && nvidia-smi &> /dev/null; then
    echo "✅ NVIDIA GPU detected"
    GPU_PROFILE="nvidia"
elif lspci | grep -i "vga.*amd" &> /dev/null; then
    echo "✅ AMD GPU detected"
    GPU_PROFILE="amd"
else
    echo "ℹ️ No GPU detected, using CPU mode"
    GPU_PROFILE="cpu"
fi

# Update GPU profile in .env
sed -i "s/GPU_PROFILE=.*/GPU_PROFILE=$GPU_PROFILE/" .env

# Pull Docker images
echo "📥 Pulling Docker images (this may take a while)..."
docker compose pull

# Start services
echo "🚀 Starting LLM Orchestrator services..."
if [ "$GPU_PROFILE" = "cpu" ]; then
    docker compose -f docker-compose.yml -f docker-compose.cpu.yml up -d
else
    docker compose up -d
fi

# Wait for services to be ready
echo "⏳ Waiting for services to start..."
sleep 30

# Check service health
echo "🔍 Checking service health..."
services=(
    "localhost:11434|Ollama"
    "localhost:6333|Qdrant"
    "localhost:5432|PostgreSQL"
    "localhost:7474|Neo4j"
)

for service in "${services[@]}"; do
    IFS='|' read -r endpoint name <<< "$service"
    if timeout 10 bash -c "until nc -z ${endpoint/:/ }; do sleep 1; done" 2>/dev/null; then
        echo "✅ $name is ready"
    else
        echo "⚠️ $name is not responding (this is normal on first startup)"
    fi
done

# Pull default models
echo "📥 Pulling default Ollama models..."
docker exec ollama ollama pull llama3.1:8b || echo "⚠️ Failed to pull llama3.1:8b (will retry later)"
docker exec ollama ollama pull nomic-embed-text || echo "⚠️ Failed to pull nomic-embed-text (will retry later)"

# Start remaining services
echo "🔧 Starting remaining services..."
docker compose up -d

# Final health check
echo "⏳ Final health check..."
sleep 15

# Show service URLs
echo ""
echo "🎉 LLM Orchestrator is ready!"
echo "============================="
echo ""
echo "🔗 Service URLs:"
echo "   Chat Interface:     http://localhost:3000"
echo "   AgentScope Studio:  http://localhost:8080"
echo "   n8n Workflows:      http://localhost:5678"
echo "   Langfuse Monitor:   http://localhost:3001"
echo "   Database Admin:     http://localhost:8000"
echo "   Neo4j Browser:      http://localhost:7474"
echo "   Vector Database:    http://localhost:6333/dashboard"
echo "   Search Engine:      http://localhost:8888"
echo ""
echo "🔑 Default Credentials:"
echo "   n8n:        admin / (check .env file)"
echo "   Neo4j:      neo4j / (check .env file)"
echo ""
echo "📚 Next Steps:"
echo "   1. Visit http://localhost:3000 to start chatting"
echo "   2. Check the README.md for detailed usage instructions"
echo "   3. Explore the agent configuration in agents/"
echo "   4. Monitor performance at http://localhost:3001"
echo ""
echo "🐛 Troubleshooting:"
echo "   - Check logs: docker compose logs -f [service-name]"
echo "   - Restart services: docker compose restart"
echo "   - Stop all: docker compose down"
echo ""
echo "📞 Support:"
echo "   - GitHub Issues: https://github.com/bcdub/llm-orchestrator/issues"
echo "   - Documentation: https://github.com/bcdub/llm-orchestrator/wiki"
echo ""

# Save important info to a file
cat > .quick-start-info.txt << EOF
LLM Orchestrator Quick Start Information
Generated: $(date)

Service URLs:
- Chat Interface: http://localhost:3000
- AgentScope Studio: http://localhost:8080
- n8n Workflows: http://localhost:5678
- Langfuse Monitor: http://localhost:3001
- Database Admin: http://localhost:8000
- Neo4j Browser: http://localhost:7474
- Vector Database: http://localhost:6333/dashboard
- Search Engine: http://localhost:8888

GPU Profile: $GPU_PROFILE

Generated Passwords (also in .env file):
- PostgreSQL: $POSTGRES_PASSWORD
- Neo4j: $NEO4J_PASSWORD
- n8n: admin / $N8N_PASSWORD

Commands:
- View logs: docker compose logs -f
- Restart: docker compose restart
- Stop: docker compose down
- Update: git pull && docker compose pull && docker compose up -d
EOF

echo "💾 Service information saved to .quick-start-info.txt"
echo ""
echo "Happy orchestrating! 🤖✨"
