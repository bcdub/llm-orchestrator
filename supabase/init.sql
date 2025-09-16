-- LLM Orchestrator Database Initialization
-- This script sets up the necessary tables and extensions for the LLM Orchestrator

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "vector";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- Create schemas
CREATE SCHEMA IF NOT EXISTS orchestrator;
CREATE SCHEMA IF NOT EXISTS memory;
CREATE SCHEMA IF NOT EXISTS analytics;

-- Set search path
SET search_path TO orchestrator, memory, analytics, public;

-- Users and sessions table
CREATE TABLE IF NOT EXISTS orchestrator.users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email VARCHAR(255) UNIQUE NOT NULL,
    name VARCHAR(255),
    preferences JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS orchestrator.sessions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES orchestrator.users(id) ON DELETE CASCADE,
    title VARCHAR(255),
    context JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Conversations and messages
CREATE TABLE IF NOT EXISTS orchestrator.conversations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id UUID REFERENCES orchestrator.sessions(id) ON DELETE CASCADE,
    user_id UUID REFERENCES orchestrator.users(id) ON DELETE CASCADE,
    title VARCHAR(255),
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS orchestrator.messages (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    conversation_id UUID REFERENCES orchestrator.conversations(id) ON DELETE CASCADE,
    role VARCHAR(50) NOT NULL CHECK (role IN ('user', 'assistant', 'system')),
    content TEXT NOT NULL,
    metadata JSONB DEFAULT '{}',
    model_used VARCHAR(100),
    tokens_used INTEGER,
    cost DECIMAL(10, 6),
    latency_ms INTEGER,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Memory system tables
CREATE TABLE IF NOT EXISTS memory.user_memories (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES orchestrator.users(id) ON DELETE CASCADE,
    memory_type VARCHAR(50) NOT NULL,
    content TEXT NOT NULL,
    embedding vector(1536), -- OpenAI embedding dimension
    metadata JSONB DEFAULT '{}',
    importance_score FLOAT DEFAULT 0.5,
    access_count INTEGER DEFAULT 0,
    last_accessed TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS memory.session_memories (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id UUID REFERENCES orchestrator.sessions(id) ON DELETE CASCADE,
    content TEXT NOT NULL,
    embedding vector(1536),
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS memory.agent_memories (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    agent_name VARCHAR(100) NOT NULL,
    memory_type VARCHAR(50) NOT NULL,
    content TEXT NOT NULL,
    embedding vector(1536),
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Model and routing analytics
CREATE TABLE IF NOT EXISTS analytics.model_usage (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    model_name VARCHAR(100) NOT NULL,
    user_id UUID REFERENCES orchestrator.users(id),
    session_id UUID REFERENCES orchestrator.sessions(id),
    query_type VARCHAR(50),
    tokens_input INTEGER,
    tokens_output INTEGER,
    cost DECIMAL(10, 6),
    latency_ms INTEGER,
    success BOOLEAN DEFAULT TRUE,
    error_message TEXT,
    routing_reason TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS analytics.routing_decisions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    query_hash VARCHAR(64) NOT NULL,
    selected_model VARCHAR(100) NOT NULL,
    alternative_models JSONB,
    routing_score FLOAT,
    reasoning TEXT,
    user_feedback INTEGER CHECK (user_feedback BETWEEN 1 AND 5),
    actual_cost DECIMAL(10, 6),
    actual_latency_ms INTEGER,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Performance metrics
CREATE TABLE IF NOT EXISTS analytics.performance_metrics (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    metric_name VARCHAR(100) NOT NULL,
    metric_value FLOAT NOT NULL,
    metric_unit VARCHAR(20),
    tags JSONB DEFAULT '{}',
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Workflow and automation tables
CREATE TABLE IF NOT EXISTS orchestrator.workflows (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    description TEXT,
    definition JSONB NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    created_by UUID REFERENCES orchestrator.users(id),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS orchestrator.workflow_executions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    workflow_id UUID REFERENCES orchestrator.workflows(id) ON DELETE CASCADE,
    status VARCHAR(50) NOT NULL CHECK (status IN ('pending', 'running', 'completed', 'failed')),
    input_data JSONB,
    output_data JSONB,
    error_message TEXT,
    started_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    completed_at TIMESTAMP WITH TIME ZONE
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_messages_conversation_id ON orchestrator.messages(conversation_id);
CREATE INDEX IF NOT EXISTS idx_messages_created_at ON orchestrator.messages(created_at);
CREATE INDEX IF NOT EXISTS idx_messages_model_used ON orchestrator.messages(model_used);

CREATE INDEX IF NOT EXISTS idx_user_memories_user_id ON memory.user_memories(user_id);
CREATE INDEX IF NOT EXISTS idx_user_memories_type ON memory.user_memories(memory_type);
CREATE INDEX IF NOT EXISTS idx_user_memories_importance ON memory.user_memories(importance_score DESC);

CREATE INDEX IF NOT EXISTS idx_session_memories_session_id ON memory.session_memories(session_id);

CREATE INDEX IF NOT EXISTS idx_agent_memories_agent_name ON memory.agent_memories(agent_name);
CREATE INDEX IF NOT EXISTS idx_agent_memories_type ON memory.agent_memories(memory_type);

CREATE INDEX IF NOT EXISTS idx_model_usage_model_name ON analytics.model_usage(model_name);
CREATE INDEX IF NOT EXISTS idx_model_usage_created_at ON analytics.model_usage(created_at);
CREATE INDEX IF NOT EXISTS idx_model_usage_user_id ON analytics.model_usage(user_id);

CREATE INDEX IF NOT EXISTS idx_routing_decisions_model ON analytics.routing_decisions(selected_model);
CREATE INDEX IF NOT EXISTS idx_routing_decisions_created_at ON analytics.routing_decisions(created_at);

CREATE INDEX IF NOT EXISTS idx_performance_metrics_name ON analytics.performance_metrics(metric_name);
CREATE INDEX IF NOT EXISTS idx_performance_metrics_timestamp ON analytics.performance_metrics(timestamp);

-- Vector similarity search indexes
CREATE INDEX IF NOT EXISTS idx_user_memories_embedding ON memory.user_memories USING ivfflat (embedding vector_cosine_ops);
CREATE INDEX IF NOT EXISTS idx_session_memories_embedding ON memory.session_memories USING ivfflat (embedding vector_cosine_ops);
CREATE INDEX IF NOT EXISTS idx_agent_memories_embedding ON memory.agent_memories USING ivfflat (embedding vector_cosine_ops);

-- Full-text search indexes
CREATE INDEX IF NOT EXISTS idx_user_memories_content_fts ON memory.user_memories USING gin(to_tsvector('english', content));
CREATE INDEX IF NOT EXISTS idx_messages_content_fts ON orchestrator.messages USING gin(to_tsvector('english', content));

-- Create functions for common operations
CREATE OR REPLACE FUNCTION memory.search_similar_memories(
    query_embedding vector(1536),
    similarity_threshold float DEFAULT 0.7,
    max_results integer DEFAULT 10
)
RETURNS TABLE (
    id UUID,
    content TEXT,
    similarity FLOAT,
    metadata JSONB
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        um.id,
        um.content,
        1 - (um.embedding <=> query_embedding) as similarity,
        um.metadata
    FROM memory.user_memories um
    WHERE 1 - (um.embedding <=> query_embedding) > similarity_threshold
    ORDER BY um.embedding <=> query_embedding
    LIMIT max_results;
END;
$$ LANGUAGE plpgsql;

-- Function to update memory access statistics
CREATE OR REPLACE FUNCTION memory.update_memory_access(memory_id UUID)
RETURNS void AS $$
BEGIN
    UPDATE memory.user_memories 
    SET 
        access_count = access_count + 1,
        last_accessed = NOW()
    WHERE id = memory_id;
END;
$$ LANGUAGE plpgsql;

-- Function to calculate user interaction statistics
CREATE OR REPLACE FUNCTION analytics.get_user_stats(user_uuid UUID)
RETURNS TABLE (
    total_messages INTEGER,
    total_cost DECIMAL,
    avg_latency FLOAT,
    favorite_model VARCHAR,
    total_sessions INTEGER
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        COUNT(m.id)::INTEGER as total_messages,
        COALESCE(SUM(m.cost), 0) as total_cost,
        COALESCE(AVG(m.latency_ms), 0) as avg_latency,
        (
            SELECT model_used 
            FROM orchestrator.messages 
            WHERE conversation_id IN (
                SELECT id FROM orchestrator.conversations WHERE user_id = user_uuid
            )
            GROUP BY model_used 
            ORDER BY COUNT(*) DESC 
            LIMIT 1
        ) as favorite_model,
        (
            SELECT COUNT(DISTINCT s.id)::INTEGER 
            FROM orchestrator.sessions s 
            WHERE s.user_id = user_uuid
        ) as total_sessions
    FROM orchestrator.messages m
    JOIN orchestrator.conversations c ON m.conversation_id = c.id
    WHERE c.user_id = user_uuid;
END;
$$ LANGUAGE plpgsql;

-- Create triggers for updated_at timestamps
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON orchestrator.users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_sessions_updated_at BEFORE UPDATE ON orchestrator.sessions
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_conversations_updated_at BEFORE UPDATE ON orchestrator.conversations
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_user_memories_updated_at BEFORE UPDATE ON memory.user_memories
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_agent_memories_updated_at BEFORE UPDATE ON memory.agent_memories
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_workflows_updated_at BEFORE UPDATE ON orchestrator.workflows
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Insert default data
INSERT INTO orchestrator.users (email, name, preferences) VALUES 
('admin@localhost', 'Administrator', '{"theme": "dark", "default_model": "llama3.1:8b"}')
ON CONFLICT (email) DO NOTHING;

-- Create database for n8n
CREATE DATABASE n8n;

-- Create database for Langfuse
CREATE DATABASE langfuse;

-- Grant permissions
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA orchestrator TO postgres;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA memory TO postgres;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA analytics TO postgres;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA orchestrator TO postgres;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA memory TO postgres;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA analytics TO postgres;
