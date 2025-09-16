# LLM Orchestrator: Local-First AI Agent Platform

A production-ready, local-first LLM orchestration platform combining AgentScope's sophisticated multi-agent capabilities with a comprehensive local AI infrastructure. Features intelligent model routing, advanced memory management, and cost-optimized cloud fallback.

## 🚀 Features

- **🤖 Multi-Agent Orchestration**: Built on AgentScope for sophisticated agent workflows
- **💰 Cost Optimization**: RouteLLM integration for 85% cost reduction through intelligent routing
- **🧠 Advanced Memory**: Mem0 integration with 26% better accuracy than OpenAI Memory
- **🏠 Local-First**: Complete local deployment with optional cloud fallback
- **📊 Comprehensive Observability**: Langfuse integration for monitoring and optimization
- **🔧 Production-Ready**: Docker Compose orchestration with sandboxed execution
- **🌐 Complete Stack**: Ollama, Supabase, Qdrant, Neo4j, n8n, and more

## 🏗️ Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   AgentScope    │    │   RouteLLM      │    │     Mem0        │
│  Orchestration  │◄──►│   Routing       │◄──►│    Memory       │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Local AI Infrastructure                      │
│  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐   │
│  │ Ollama  │ │Supabase │ │ Qdrant  │ │ Neo4j   │ │   n8n   │   │
│  └─────────┘ └─────────┘ └─────────┘ └─────────┘ └─────────┘   │
└─────────────────────────────────────────────────────────────────┘
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Open WebUI    │    │    Langfuse     │    │     Caddy       │
│   Interface     │    │  Observability  │    │   Reverse Proxy │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## 🛠️ Quick Start

### Prerequisites

- Docker and Docker Compose
- NVIDIA GPU (recommended) or CPU-only mode
- 16GB+ RAM (32GB+ recommended)
- 50GB+ free disk space

### 1. Clone and Setup

```bash
git clone https://github.com/bcdub/llm-orchestrator.git
cd llm-orchestrator
cp .env.example .env
```

### 2. Configure Environment

Edit `.env` file with your settings:

```bash
# Basic Configuration
COMPOSE_PROJECT_NAME=llm-orchestrator
ENVIRONMENT=private  # or 'public' for cloud deployment

# GPU Configuration
GPU_PROFILE=nvidia  # nvidia, amd, cpu, or none

# Model Configuration
DEFAULT_LOCAL_MODEL=llama3.1:8b
DEFAULT_CLOUD_MODEL=gpt-4o-mini

# API Keys (optional for cloud fallback)
OPENAI_API_KEY=your_openai_key_here
ANTHROPIC_API_KEY=your_anthropic_key_here
```

### 3. Deploy the Stack

```bash
# Start all services
python start_services.py

# Or manually with Docker Compose
docker-compose up -d
```

### 4. Access Services

- **Open WebUI**: http://localhost:3000 (Chat interface)
- **AgentScope Studio**: http://localhost:8080 (Agent development)
- **n8n Workflows**: http://localhost:5678 (Automation)
- **Langfuse**: http://localhost:3001 (Observability)
- **Supabase**: http://localhost:8000 (Database admin)

## 📋 Services Overview

| Service | Port | Purpose | Status |
|---------|------|---------|--------|
| **AgentScope Runtime** | 8080 | Agent orchestration and execution | ✅ |
| **Ollama** | 11434 | Local LLM serving | ✅ |
| **Open WebUI** | 3000 | Chat interface | ✅ |
| **Supabase** | 8000 | Database and vector store | ✅ |
| **Qdrant** | 6333 | High-performance vector DB | ✅ |
| **Neo4j** | 7474 | Knowledge graph database | ✅ |
| **n8n** | 5678 | Workflow automation | ✅ |
| **Langfuse** | 3001 | LLM observability | ✅ |
| **SearXNG** | 8888 | Private search engine | ✅ |
| **Caddy** | 80/443 | Reverse proxy (public mode) | ✅ |

## 🧠 Memory System

The platform includes a sophisticated multi-level memory system:

### Memory Layers
- **User Memory**: Long-term user preferences and context
- **Session Memory**: Conversation-specific context
- **Agent Memory**: Agent-specific knowledge and state

### Storage Backends
- **Qdrant**: High-performance vector similarity search
- **Supabase**: Structured data and metadata
- **Neo4j**: Complex relationship modeling

### Memory Features
- **Semantic Compression**: 90% token reduction
- **Intelligent Retrieval**: Context-aware memory access
- **Cross-Session Persistence**: Maintain context across conversations

## 🎯 Intelligent Routing

RouteLLM integration provides cost-optimized model selection:

### Routing Strategies
- **Performance-based**: Route based on query complexity
- **Cost-optimized**: Minimize cloud API usage
- **Latency-optimized**: Prioritize response speed
- **Quality-optimized**: Route for best accuracy

### Supported Models

#### Local Models (via Ollama)
- Llama 3.1 (8B, 70B)
- Mistral 7B
- CodeLlama
- Phi-3
- Custom fine-tuned models

#### Cloud Models (Fallback)
- OpenAI GPT-4o, GPT-4o-mini
- Anthropic Claude 3.5 Sonnet
- Google Gemini Pro
- Cohere Command R+

## 🔧 Development

### Adding Custom Agents

```python
# agents/custom_agent.py
from agentscope import Agent
from agentscope.memory import MemoryBank

class CustomAgent(Agent):
    def __init__(self, name, model_config, memory_config):
        super().__init__(name=name, model_config=model_config)
        self.memory = MemoryBank(config=memory_config)
    
    def reply(self, x):
        # Custom agent logic
        context = self.memory.retrieve(x.content)
        response = self.model(x.content, context=context)
        self.memory.add(x.content, response)
        return response
```

### Custom Routing Logic

```python
# routing/custom_router.py
from routellm import Router

class CustomRouter(Router):
    def route(self, query, context=None):
        # Implement custom routing logic
        if self.is_complex_reasoning(query):
            return "gpt-4o"
        elif self.requires_code_generation(query):
            return "codellama:13b"
        else:
            return "llama3.1:8b"
```

### Workflow Integration

Create custom n8n workflows in the `workflows/` directory and they'll be automatically imported.

## 📊 Monitoring & Observability

### Langfuse Integration
- **Trace Analysis**: Complete request/response tracking
- **Performance Metrics**: Latency, cost, and accuracy monitoring
- **Model Comparison**: A/B testing different routing strategies

### Custom Metrics
- **Cost Tracking**: Real-time API usage and costs
- **Performance Monitoring**: Response times and throughput
- **Quality Metrics**: User satisfaction and accuracy scores

### Health Checks
```bash
# Check service health
docker-compose ps

# View logs
docker-compose logs -f agentscope-runtime

# Monitor resource usage
docker stats
```

## 🚀 Deployment

### Local Development
```bash
# Development mode with hot reloading
ENVIRONMENT=development docker-compose up -d
```

### Production Deployment
```bash
# Production mode with optimizations
ENVIRONMENT=production docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

### Cloud Deployment
```bash
# Public mode with Caddy reverse proxy
ENVIRONMENT=public python start_services.py
```

## 🔒 Security

- **Sandboxed Execution**: AgentScope Runtime provides isolated agent execution
- **Environment Isolation**: Separate development and production environments
- **API Key Management**: Secure credential handling via environment variables
- **Network Security**: Configurable firewall rules and reverse proxy

## 📈 Performance Optimization

### Hardware Recommendations

#### Minimum Requirements
- **CPU**: 8 cores
- **RAM**: 16GB
- **GPU**: 8GB VRAM (optional)
- **Storage**: 50GB SSD

#### Recommended Configuration
- **CPU**: 16+ cores
- **RAM**: 32GB+
- **GPU**: 24GB+ VRAM (RTX 4090, A100)
- **Storage**: 200GB+ NVMe SSD

### Optimization Tips
- Use GPU acceleration for local models
- Configure memory limits for each service
- Enable model caching for faster startup
- Use SSD storage for vector databases

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## 📄 License

This project is licensed under the Apache 2.0 License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- **AgentScope**: Multi-agent orchestration framework
- **Local AI Packaged**: Infrastructure inspiration
- **RouteLLM**: Intelligent model routing
- **Mem0**: Advanced memory management
- **Ollama**: Local LLM serving
- **Supabase**: Database and vector store
- **Langfuse**: LLM observability

## 📞 Support

- **Issues**: [GitHub Issues](https://github.com/bcdub/llm-orchestrator/issues)
- **Discussions**: [GitHub Discussions](https://github.com/bcdub/llm-orchestrator/discussions)
- **Documentation**: [Wiki](https://github.com/bcdub/llm-orchestrator/wiki)

---

**Built with ❤️ for the local AI community**
