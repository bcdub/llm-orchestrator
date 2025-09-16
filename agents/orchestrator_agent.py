"""
LLM Orchestrator Agent

This is the main orchestrator agent that handles routing, memory management,
and coordination between local and cloud models.
"""

import os
import json
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

try:
    from agentscope import Agent, Msg
    from agentscope.memory import MemoryBank
    from agentscope.models import ModelWrapperBase
except ImportError:
    # Fallback for development without AgentScope installed
    class Agent:
        def __init__(self, *args, **kwargs):
            pass
    
    class Msg:
        def __init__(self, content: str, role: str = "user"):
            self.content = content
            self.role = role
    
    class MemoryBank:
        def __init__(self, *args, **kwargs):
            self.memory = []
        
        def add(self, msg):
            self.memory.append(msg)
        
        def get_memory(self):
            return self.memory

@dataclass
class RoutingDecision:
    """Represents a routing decision for a query"""
    model: str
    reasoning: str
    confidence: float
    estimated_cost: float
    estimated_latency: float

class IntelligentRouter:
    """Intelligent model router with cost and performance optimization"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.local_models = config.get('local_models', ['llama3.1:8b'])
        self.cloud_models = config.get('cloud_models', ['gpt-4o-mini'])
        self.cost_threshold = config.get('cost_threshold', 0.001)
        self.latency_threshold = config.get('latency_threshold', 2000)
        self.quality_threshold = config.get('quality_threshold', 0.8)
        
        # Model capabilities and costs
        self.model_info = {
            'llama3.1:8b': {
                'cost_per_token': 0.0,
                'avg_latency': 50,
                'capabilities': ['general', 'reasoning'],
                'max_context': 128000
            },
            'llama3.1:70b': {
                'cost_per_token': 0.0,
                'avg_latency': 200,
                'capabilities': ['general', 'reasoning', 'complex'],
                'max_context': 128000
            },
            'codellama:13b': {
                'cost_per_token': 0.0,
                'avg_latency': 100,
                'capabilities': ['code', 'programming'],
                'max_context': 16000
            },
            'gpt-4o-mini': {
                'cost_per_token': 0.00015,
                'avg_latency': 800,
                'capabilities': ['general', 'reasoning', 'complex', 'multimodal'],
                'max_context': 128000
            },
            'gpt-4o': {
                'cost_per_token': 0.005,
                'avg_latency': 1200,
                'capabilities': ['general', 'reasoning', 'complex', 'multimodal', 'advanced'],
                'max_context': 128000
            }
        }
    
    def analyze_query_complexity(self, query: str, context: Optional[str] = None) -> Dict[str, float]:
        """Analyze query complexity and requirements"""
        query_lower = query.lower()
        
        # Complexity indicators
        complexity_score = 0.0
        
        # Length-based complexity
        if len(query) > 500:
            complexity_score += 0.2
        
        # Reasoning indicators
        reasoning_keywords = ['analyze', 'compare', 'evaluate', 'explain why', 'reasoning', 'logic']
        if any(keyword in query_lower for keyword in reasoning_keywords):
            complexity_score += 0.3
        
        # Code-related queries
        code_keywords = ['code', 'programming', 'function', 'algorithm', 'debug', 'implement']
        code_score = 0.5 if any(keyword in query_lower for keyword in code_keywords) else 0.0
        
        # Multimodal requirements
        multimodal_keywords = ['image', 'picture', 'visual', 'diagram', 'chart']
        multimodal_score = 0.8 if any(keyword in query_lower for keyword in multimodal_keywords) else 0.0
        
        # Mathematical complexity
        math_keywords = ['calculate', 'equation', 'formula', 'mathematics', 'statistics']
        math_score = 0.4 if any(keyword in query_lower for keyword in math_keywords) else 0.0
        
        return {
            'general_complexity': min(complexity_score, 1.0),
            'code_requirement': code_score,
            'multimodal_requirement': multimodal_score,
            'math_requirement': math_score
        }
    
    def route_query(self, query: str, context: Optional[str] = None, 
                   user_preferences: Optional[Dict] = None) -> RoutingDecision:
        """Route a query to the most appropriate model"""
        
        analysis = self.analyze_query_complexity(query, context)
        user_prefs = user_preferences or {}
        
        # Preference weights
        cost_weight = user_prefs.get('cost_priority', 0.7)
        speed_weight = user_prefs.get('speed_priority', 0.2)
        quality_weight = user_prefs.get('quality_priority', 0.1)
        
        best_model = None
        best_score = -1
        reasoning_parts = []
        
        for model, info in self.model_info.items():
            # Check if model is available
            if model in self.local_models or model in self.cloud_models:
                score = 0
                
                # Cost scoring (higher score for lower cost)
                cost_score = 1.0 if info['cost_per_token'] == 0 else max(0, 1 - info['cost_per_token'] * 1000)
                score += cost_score * cost_weight
                
                # Speed scoring (higher score for lower latency)
                speed_score = max(0, 1 - info['avg_latency'] / 2000)
                score += speed_score * speed_weight
                
                # Quality/capability scoring
                quality_score = 0.5  # Base quality
                
                # Boost for specific capabilities
                if analysis['code_requirement'] > 0.5 and 'code' in info['capabilities']:
                    quality_score += 0.3
                elif analysis['multimodal_requirement'] > 0.5 and 'multimodal' in info['capabilities']:
                    quality_score += 0.4
                elif analysis['general_complexity'] > 0.7 and 'complex' in info['capabilities']:
                    quality_score += 0.3
                
                score += quality_score * quality_weight
                
                if score > best_score:
                    best_score = score
                    best_model = model
                    reasoning_parts = [
                        f"Cost score: {cost_score:.2f}",
                        f"Speed score: {speed_score:.2f}",
                        f"Quality score: {quality_score:.2f}",
                        f"Total score: {score:.2f}"
                    ]
        
        if not best_model:
            best_model = self.local_models[0] if self.local_models else 'gpt-4o-mini'
            reasoning_parts = ["Fallback to default model"]
        
        model_info = self.model_info.get(best_model, {})
        
        return RoutingDecision(
            model=best_model,
            reasoning="; ".join(reasoning_parts),
            confidence=best_score,
            estimated_cost=model_info.get('cost_per_token', 0) * len(query.split()),
            estimated_latency=model_info.get('avg_latency', 1000)
        )

class MemoryManager:
    """Advanced memory management with compression and retrieval"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.memory_bank = MemoryBank()
        self.compression_threshold = config.get('compression_threshold', 10)
        self.max_memory_size = config.get('max_memory_size', 100)
    
    def add_interaction(self, query: str, response: str, metadata: Dict[str, Any]):
        """Add an interaction to memory with metadata"""
        interaction = {
            'query': query,
            'response': response,
            'timestamp': metadata.get('timestamp'),
            'model_used': metadata.get('model'),
            'cost': metadata.get('cost', 0),
            'latency': metadata.get('latency', 0)
        }
        
        self.memory_bank.add(Msg(content=json.dumps(interaction), role="memory"))
        
        # Compress memory if needed
        if len(self.memory_bank.get_memory()) > self.max_memory_size:
            self._compress_memory()
    
    def _compress_memory(self):
        """Compress old memories to save space"""
        # This is a simplified compression - in practice, you'd use
        # semantic compression with embeddings
        memory = self.memory_bank.get_memory()
        
        if len(memory) > self.compression_threshold:
            # Keep recent memories, compress older ones
            recent_memories = memory[-self.compression_threshold:]
            old_memories = memory[:-self.compression_threshold]
            
            # Create a compressed summary of old memories
            summary = self._create_summary(old_memories)
            
            # Reset memory with summary + recent memories
            self.memory_bank = MemoryBank()
            self.memory_bank.add(Msg(content=summary, role="summary"))
            
            for msg in recent_memories:
                self.memory_bank.add(msg)
    
    def _create_summary(self, memories: List) -> str:
        """Create a summary of old memories"""
        # Simplified summarization - in practice, use an LLM
        topics = set()
        total_cost = 0
        total_interactions = len(memories)
        
        for msg in memories:
            try:
                data = json.loads(msg.content)
                # Extract topics from queries (simplified)
                query_words = data.get('query', '').lower().split()
                topics.update(word for word in query_words if len(word) > 4)
                total_cost += data.get('cost', 0)
            except:
                continue
        
        summary = {
            'type': 'compressed_summary',
            'period': f"{total_interactions} interactions",
            'total_cost': total_cost,
            'main_topics': list(topics)[:10],  # Top 10 topics
            'compressed_at': 'timestamp_here'
        }
        
        return json.dumps(summary)
    
    def retrieve_relevant_context(self, query: str, max_items: int = 5) -> str:
        """Retrieve relevant context for a query"""
        # Simplified retrieval - in practice, use semantic search
        memory = self.memory_bank.get_memory()
        relevant_items = []
        
        query_words = set(query.lower().split())
        
        for msg in reversed(memory):  # Start with most recent
            try:
                if msg.role == "summary":
                    # Always include summaries
                    relevant_items.append(msg.content)
                else:
                    data = json.loads(msg.content)
                    msg_words = set(data.get('query', '').lower().split())
                    
                    # Simple word overlap scoring
                    overlap = len(query_words.intersection(msg_words))
                    if overlap > 0:
                        relevant_items.append(msg.content)
                
                if len(relevant_items) >= max_items:
                    break
            except:
                continue
        
        return "\n".join(relevant_items)

class OrchestratorAgent(Agent):
    """Main orchestrator agent that coordinates the entire system"""
    
    def __init__(self, name: str = "orchestrator", config: Optional[Dict] = None):
        self.config = config or {}
        self.router = IntelligentRouter(self.config.get('routing', {}))
        self.memory_manager = MemoryManager(self.config.get('memory', {}))
        
        # Initialize with a simple model config for AgentScope
        model_config = {
            "model_type": "ollama",
            "model_name": "llama3.1:8b",
            "api_url": "http://localhost:11434"
        }
        
        super().__init__(name=name, model_config=model_config)
    
    def reply(self, x: Msg) -> Msg:
        """Process a message and return a response"""
        import time
        start_time = time.time()
        
        # Extract query
        query = x.content if hasattr(x, 'content') else str(x)
        
        # Get relevant context from memory
        context = self.memory_manager.retrieve_relevant_context(query)
        
        # Route the query
        routing_decision = self.router.route_query(query, context)
        
        # Execute the query (simplified - in practice, call the actual model)
        response = self._execute_query(query, routing_decision, context)
        
        # Calculate metrics
        end_time = time.time()
        latency = (end_time - start_time) * 1000  # Convert to milliseconds
        
        # Store interaction in memory
        metadata = {
            'timestamp': start_time,
            'model': routing_decision.model,
            'cost': routing_decision.estimated_cost,
            'latency': latency,
            'routing_reasoning': routing_decision.reasoning
        }
        
        self.memory_manager.add_interaction(query, response, metadata)
        
        # Create response message
        response_msg = Msg(content=response, role="assistant")
        response_msg.metadata = metadata
        
        return response_msg
    
    def _execute_query(self, query: str, routing_decision: RoutingDecision, context: str) -> str:
        """Execute the query using the selected model"""
        # This is a placeholder - in practice, you'd call the actual model
        # through Ollama API, OpenAI API, etc.
        
        model_name = routing_decision.model
        
        # Construct the prompt with context
        prompt = f"""Context from previous interactions:
{context}

User query: {query}

Please provide a helpful response."""
        
        # Simulate model response (replace with actual model calls)
        response = f"""[Routed to {model_name}]

This is a simulated response to: {query}

Routing reasoning: {routing_decision.reasoning}
Estimated cost: ${routing_decision.estimated_cost:.4f}
Estimated latency: {routing_decision.estimated_latency}ms

In a real implementation, this would be the actual model response."""
        
        return response
    
    def get_stats(self) -> Dict[str, Any]:
        """Get orchestrator statistics"""
        memory = self.memory_manager.memory_bank.get_memory()
        
        total_interactions = 0
        total_cost = 0
        model_usage = {}
        
        for msg in memory:
            try:
                if msg.role == "memory":
                    data = json.loads(msg.content)
                    total_interactions += 1
                    total_cost += data.get('cost', 0)
                    
                    model = data.get('model_used', 'unknown')
                    model_usage[model] = model_usage.get(model, 0) + 1
            except:
                continue
        
        return {
            'total_interactions': total_interactions,
            'total_cost': total_cost,
            'model_usage': model_usage,
            'memory_size': len(memory),
            'available_models': {
                'local': self.router.local_models,
                'cloud': self.router.cloud_models
            }
        }

# Example usage and testing
if __name__ == "__main__":
    # Configuration
    config = {
        'routing': {
            'local_models': ['llama3.1:8b', 'codellama:13b'],
            'cloud_models': ['gpt-4o-mini', 'gpt-4o'],
            'cost_threshold': 0.001,
            'latency_threshold': 2000
        },
        'memory': {
            'compression_threshold': 10,
            'max_memory_size': 50
        }
    }
    
    # Create orchestrator
    orchestrator = OrchestratorAgent("main_orchestrator", config)
    
    # Test queries
    test_queries = [
        "What is the capital of France?",
        "Write a Python function to calculate fibonacci numbers",
        "Analyze the pros and cons of renewable energy",
        "Debug this code: def hello(): print('Hello World')"
    ]
    
    print("🤖 LLM Orchestrator Agent Test")
    print("=" * 50)
    
    for i, query in enumerate(test_queries, 1):
        print(f"\n📝 Query {i}: {query}")
        
        # Create message
        msg = Msg(content=query, role="user")
        
        # Get response
        response = orchestrator.reply(msg)
        
        print(f"🤖 Response: {response.content}")
        
        if hasattr(response, 'metadata'):
            metadata = response.metadata
            print(f"📊 Model: {metadata['model']}")
            print(f"💰 Cost: ${metadata['cost']:.4f}")
            print(f"⏱️ Latency: {metadata['latency']:.1f}ms")
    
    # Show statistics
    print(f"\n📈 Orchestrator Statistics:")
    stats = orchestrator.get_stats()
    for key, value in stats.items():
        print(f"  {key}: {value}")
