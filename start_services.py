#!/usr/bin/env python3
"""
LLM Orchestrator Service Manager

This script manages the startup and configuration of the LLM Orchestrator stack.
It handles different deployment environments, GPU configurations, and service dependencies.
"""

import os
import sys
import subprocess
import time
import argparse
import json
from pathlib import Path
from typing import Dict, List, Optional

class ServiceManager:
    def __init__(self):
        self.project_root = Path(__file__).parent
        self.env_file = self.project_root / ".env"
        self.compose_file = self.project_root / "docker-compose.yml"
        
    def load_environment(self) -> Dict[str, str]:
        """Load environment variables from .env file"""
        env_vars = {}
        if self.env_file.exists():
            with open(self.env_file, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        env_vars[key] = value
        return env_vars
    
    def check_prerequisites(self) -> bool:
        """Check if all prerequisites are met"""
        print("🔍 Checking prerequisites...")
        
        # Check Docker
        try:
            result = subprocess.run(['docker', '--version'], capture_output=True, text=True)
            if result.returncode != 0:
                print("❌ Docker is not installed or not running")
                return False
            print(f"✅ Docker: {result.stdout.strip()}")
        except FileNotFoundError:
            print("❌ Docker is not installed")
            return False
        
        # Check Docker Compose
        try:
            result = subprocess.run(['docker', 'compose', 'version'], capture_output=True, text=True)
            if result.returncode != 0:
                print("❌ Docker Compose is not available")
                return False
            print(f"✅ Docker Compose: {result.stdout.strip()}")
        except FileNotFoundError:
            print("❌ Docker Compose is not installed")
            return False
        
        # Check .env file
        if not self.env_file.exists():
            print("❌ .env file not found. Please copy .env.example to .env and configure it.")
            return False
        print("✅ Environment configuration found")
        
        return True
    
    def detect_gpu(self) -> str:
        """Detect available GPU and return appropriate profile"""
        print("🔍 Detecting GPU configuration...")
        
        # Check for NVIDIA GPU
        try:
            result = subprocess.run(['nvidia-smi'], capture_output=True, text=True)
            if result.returncode == 0:
                print("✅ NVIDIA GPU detected")
                return "nvidia"
        except FileNotFoundError:
            pass
        
        # Check for AMD GPU (basic detection)
        try:
            result = subprocess.run(['lspci'], capture_output=True, text=True)
            if 'AMD' in result.stdout and 'VGA' in result.stdout:
                print("✅ AMD GPU detected")
                return "amd"
        except FileNotFoundError:
            pass
        
        print("ℹ️ No GPU detected, using CPU mode")
        return "cpu"
    
    def generate_secrets(self) -> Dict[str, str]:
        """Generate secure random secrets for services"""
        import secrets
        import string
        
        def generate_key(length: int = 32) -> str:
            alphabet = string.ascii_letters + string.digits
            return ''.join(secrets.choice(alphabet) for _ in range(length))
        
        return {
            'POSTGRES_PASSWORD': generate_key(16),
            'NEO4J_PASSWORD': generate_key(16),
            'N8N_BASIC_AUTH_PASSWORD': generate_key(12),
            'WEBUI_SECRET_KEY': generate_key(32),
            'LANGFUSE_SECRET_KEY': f"sk-lf-{generate_key(32)}",
            'LANGFUSE_PUBLIC_KEY': f"pk-lf-{generate_key(32)}",
            'LANGFUSE_SALT': generate_key(16),
            'JWT_SECRET': generate_key(32),
            'ENCRYPTION_KEY': generate_key(32),
        }
    
    def setup_environment(self, gpu_profile: Optional[str] = None, environment: Optional[str] = None):
        """Setup environment configuration"""
        print("⚙️ Setting up environment...")
        
        env_vars = self.load_environment()
        
        # Auto-detect GPU if not specified
        if not gpu_profile:
            gpu_profile = env_vars.get('GPU_PROFILE', self.detect_gpu())
        
        # Set default environment
        if not environment:
            environment = env_vars.get('ENVIRONMENT', 'private')
        
        # Generate missing secrets
        secrets = self.generate_secrets()
        updated = False
        
        for key, value in secrets.items():
            if key not in env_vars or not env_vars[key] or env_vars[key].startswith('your_'):
                env_vars[key] = value
                updated = True
        
        # Update GPU profile
        if env_vars.get('GPU_PROFILE') != gpu_profile:
            env_vars['GPU_PROFILE'] = gpu_profile
            updated = True
        
        # Update environment
        if env_vars.get('ENVIRONMENT') != environment:
            env_vars['ENVIRONMENT'] = environment
            updated = True
        
        # Write back to .env file if updated
        if updated:
            with open(self.env_file, 'w') as f:
                f.write("# LLM Orchestrator Configuration\n")
                f.write("# Auto-generated and updated by start_services.py\n\n")
                for key, value in env_vars.items():
                    f.write(f"{key}={value}\n")
            print("✅ Environment configuration updated")
        
        return env_vars
    
    def pull_models(self, models: List[str]):
        """Pull required Ollama models"""
        print("📥 Pulling required models...")
        
        for model in models:
            print(f"  Pulling {model}...")
            try:
                result = subprocess.run([
                    'docker', 'exec', 'ollama', 'ollama', 'pull', model
                ], capture_output=True, text=True, timeout=300)
                
                if result.returncode == 0:
                    print(f"  ✅ {model} pulled successfully")
                else:
                    print(f"  ⚠️ Failed to pull {model}: {result.stderr}")
            except subprocess.TimeoutExpired:
                print(f"  ⚠️ Timeout pulling {model}")
            except Exception as e:
                print(f"  ⚠️ Error pulling {model}: {e}")
    
    def wait_for_service(self, service_name: str, port: int, timeout: int = 60):
        """Wait for a service to become available"""
        print(f"⏳ Waiting for {service_name} on port {port}...")
        
        import socket
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(1)
                result = sock.connect_ex(('localhost', port))
                sock.close()
                
                if result == 0:
                    print(f"✅ {service_name} is ready")
                    return True
            except:
                pass
            
            time.sleep(2)
        
        print(f"⚠️ {service_name} did not become ready within {timeout} seconds")
        return False
    
    def start_services(self, environment: str, gpu_profile: str):
        """Start all services in the correct order"""
        print("🚀 Starting LLM Orchestrator services...")
        
        # Prepare Docker Compose command
        compose_cmd = ['docker', 'compose']
        
        # Add profile for public deployment
        if environment == 'public':
            compose_cmd.extend(['--profile', 'public'])
        
        # Add GPU-specific compose file if needed
        if gpu_profile == 'nvidia':
            # Docker Compose will use the GPU configuration in the main file
            pass
        elif gpu_profile == 'cpu':
            # Override GPU configuration for CPU-only mode
            compose_cmd.extend(['-f', 'docker-compose.yml', '-f', 'docker-compose.cpu.yml'])
        
        # Start core infrastructure first
        print("📦 Starting core infrastructure...")
        core_services = ['supabase-db', 'qdrant', 'neo4j']
        
        for service in core_services:
            subprocess.run(compose_cmd + ['up', '-d', service], check=True)
        
        # Wait for databases to be ready
        self.wait_for_service('PostgreSQL', 5432)
        self.wait_for_service('Qdrant', 6333)
        self.wait_for_service('Neo4j', 7474)
        
        # Start Ollama
        print("🤖 Starting Ollama...")
        subprocess.run(compose_cmd + ['up', '-d', 'ollama'], check=True)
        self.wait_for_service('Ollama', 11434)
        
        # Pull default models
        default_models = ['llama3.1:8b', 'nomic-embed-text']
        self.pull_models(default_models)
        
        # Start remaining services
        print("🔧 Starting remaining services...")
        subprocess.run(compose_cmd + ['up', '-d'], check=True)
        
        # Wait for key services
        services_to_check = [
            ('AgentScope Runtime', 8080),
            ('Open WebUI', 3000),
            ('n8n', 5678),
            ('Langfuse', 3001),
        ]
        
        for service_name, port in services_to_check:
            self.wait_for_service(service_name, port)
    
    def show_status(self):
        """Show status of all services"""
        print("\n📊 Service Status:")
        print("=" * 60)
        
        services = [
            ("AgentScope Runtime", "http://localhost:8080", "Agent orchestration"),
            ("Open WebUI", "http://localhost:3000", "Chat interface"),
            ("n8n", "http://localhost:5678", "Workflow automation"),
            ("Langfuse", "http://localhost:3001", "LLM observability"),
            ("Supabase Studio", "http://localhost:8000", "Database admin"),
            ("Neo4j Browser", "http://localhost:7474", "Knowledge graph"),
            ("Qdrant Dashboard", "http://localhost:6333/dashboard", "Vector database"),
            ("SearXNG", "http://localhost:8888", "Private search"),
        ]
        
        for name, url, description in services:
            print(f"🔗 {name:20} {url:35} {description}")
        
        print("\n" + "=" * 60)
        print("🎉 LLM Orchestrator is ready!")
        print("📚 Check the README.md for usage instructions")
        print("🐛 Report issues at: https://github.com/bcdub/llm-orchestrator/issues")

def main():
    parser = argparse.ArgumentParser(description='LLM Orchestrator Service Manager')
    parser.add_argument('--environment', choices=['private', 'public', 'development', 'production'],
                       help='Deployment environment')
    parser.add_argument('--gpu', choices=['nvidia', 'amd', 'cpu', 'none'],
                       help='GPU configuration')
    parser.add_argument('--no-pull', action='store_true',
                       help='Skip pulling Docker images')
    parser.add_argument('--status-only', action='store_true',
                       help='Only show service status')
    
    args = parser.parse_args()
    
    manager = ServiceManager()
    
    if args.status_only:
        manager.show_status()
        return
    
    # Check prerequisites
    if not manager.check_prerequisites():
        sys.exit(1)
    
    # Setup environment
    env_vars = manager.setup_environment(args.gpu, args.environment)
    environment = env_vars.get('ENVIRONMENT', 'private')
    gpu_profile = env_vars.get('GPU_PROFILE', 'cpu')
    
    print(f"🎯 Environment: {environment}")
    print(f"🎮 GPU Profile: {gpu_profile}")
    
    try:
        # Pull images if not skipped
        if not args.no_pull:
            print("📥 Pulling Docker images...")
            subprocess.run(['docker', 'compose', 'pull'], check=True)
        
        # Start services
        manager.start_services(environment, gpu_profile)
        
        # Show status
        manager.show_status()
        
    except subprocess.CalledProcessError as e:
        print(f"❌ Error starting services: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n⏹️ Startup interrupted by user")
        sys.exit(1)

if __name__ == '__main__':
    main()
