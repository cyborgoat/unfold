# Unfold AI Setup Guide

This guide will help you set up the AI-enhanced features of Unfold, including LLM integration, vector database, and knowledge graph capabilities.

## Prerequisites

### System Requirements
- Python 3.11+
- At least 4GB RAM available for AI services
- 5GB free disk space for local databases
- Java 21+ or OpenJDK 21+ (for Neo4j)

### Services Required

1. **Ollama** (for local LLM) or **OpenAI API** (for cloud LLM)
2. **Milvus Lite** (lightweight vector database - no Docker required)
3. **Neo4j Desktop** or **Neo4j Community Edition** (local installation)

## Quick Start

### 1. Install Dependencies

```bash
# Install unfold with AI dependencies
pip install -e ".[dev]"

# Or if using uv
uv pip install -e ".[dev]"
```

### 2. Install Local Services

#### Install Neo4j (Local Installation)

**Option A: Neo4j Desktop (Recommended for Development)**

1. Download Neo4j Desktop from [Neo4j Deployment Center](https://neo4j.com/deployment-center/)
2. Install and run Neo4j Desktop
3. Create a new project and database instance
4. Set password (default username: `neo4j`)
5. Install APOC plugin for graph algorithms
6. Start the database instance

**Option B: Neo4j Community Edition (Command Line)**

**macOS:**
```bash
# Install via Homebrew
brew install neo4j

# Or download directly
# Visit https://neo4j.com/deployment-center/ and download Neo4j Community Edition
# Extract and set NEO4J_HOME environment variable
```

**Linux (Ubuntu/Debian):**
```bash
# Install Java 21 if not available
sudo apt update
sudo apt install openjdk-21-jdk

# Download Neo4j Community Edition
wget https://dist.neo4j.org/neo4j-community-5.26.0-unix.tar.gz
tar -xzf neo4j-community-5.26.0-unix.tar.gz
sudo mv neo4j-community-5.26.0 /opt/neo4j

# Set environment variables
echo 'export NEO4J_HOME=/opt/neo4j' >> ~/.bashrc
echo 'export PATH=$NEO4J_HOME/bin:$PATH' >> ~/.bashrc
source ~/.bashrc

# Set initial password
neo4j-admin dbms set-initial-password password

# Start Neo4j
neo4j start
```

**Windows:**
```powershell
# Download Neo4j Community Edition from https://neo4j.com/deployment-center/
# Extract to C:\neo4j
# Set NEO4J_HOME environment variable
# Open PowerShell as Administrator and run:
cd C:\neo4j\bin
.\neo4j-admin.bat dbms set-initial-password password
.\neo4j.bat start
```

#### Milvus Lite Setup (No Installation Required)

Milvus Lite is automatically installed with the Python dependencies. It stores data locally using SQLite, so no separate database service is needed.

**Verification:**
```python
from pymilvus import MilvusClient

# Test Milvus Lite connection
client = MilvusClient("./test.db")
print("Milvus Lite is working!")
client.close()
```

### 3. Install and Start Ollama

```bash
# Install Ollama
curl -fsSL https://ollama.ai/install.sh | sh

# Start Ollama service
ollama serve

# In another terminal, pull a model
ollama pull llama3.2
```

### 4. Configure Unfold

Create a configuration file at `~/.config/unfold/config.json`:

```json
{
  "llm": {
    "provider": "ollama",
    "model": "llama3.2",
    "base_url": "http://localhost:11434",
    "temperature": 0.7,
    "max_tokens": 2048,
    "stream": true
  },
  "vector_db": {
    "host": "localhost",
    "port": "19530",
    "enabled": true,
    "embedding_model": "all-MiniLM-L6-v2",
    "use_milvus_lite": true,
    "local_db_path": "./knowledge/vector.db"
  },
  "graph_db": {
    "uri": "bolt://localhost:7687",
    "user": "neo4j", 
    "password": "password",
    "database": "unfold",
    "enabled": true
  },
  "mcp": {
    "host": "localhost",
    "port": 8000,
    "enabled": true
  },
  "ai_assistant": {
    "enabled": true,
    "streaming_response": true,
    "context_window": 20
  }
}
```

### 5. Initialize Knowledge Base

```bash
# Create knowledge directory structure
mkdir -p knowledge/{files,memory,graph}

# Index your first directory with AI features
unfold index ~/Documents --recursive

# Start the AI assistant
unfold ai
```

## Configuration Options

### LLM Configuration

#### Ollama Setup
```json
{
  "llm": {
    "provider": "ollama",
    "model": "llama3.2",
    "base_url": "http://localhost:11434"
  }
}
```

#### OpenAI Setup
```json
{
  "llm": {
    "provider": "openai",
    "model": "gpt-4",
    "base_url": "https://api.openai.com/v1",
    "api_key": "your-api-key-here"
  }
}
```

### Vector Database Configuration

```json
{
  "vector_db": {
    "host": "localhost",
    "port": "19530",
    "enabled": true,
    "use_milvus_lite": true,
    "local_db_path": "./knowledge/vector.db",
    "embedding_model": "all-MiniLM-L6-v2",
    "chunk_size": 512,
    "chunk_overlap": 50
  }
}
```

### Knowledge Graph Configuration

```json
{
  "graph_db": {
    "uri": "bolt://localhost:7687",
    "user": "neo4j",
    "password": "your-password",
    "database": "unfold",
    "enabled": true
  }
}
```

## Usage Examples

### Basic AI Assistant

```bash
# Start AI assistant
unfold ai

# Example queries:
🤖 Ask me anything: Find all Python files in the src directory
🤖 Ask me anything: What files import pandas?
🤖 Ask me anything: Show me the project structure
🤖 Ask me anything: Find files similar to main.py
```

### Command Line Options

```bash
# Use specific model
unfold ai --model llama3.1 --provider ollama

# Disable streaming
unfold ai --no-streaming

# Use OpenAI
unfold ai --provider openai --model gpt-4
```

### Advanced Features

```bash
# Check system health
unfold ai
🤖 Ask me anything: stats

# View available tools
🤖 Ask me anything: tools

# Get help
🤖 Ask me anything: help
```

## Troubleshooting

### Common Issues

#### 1. Milvus Lite Connection Failed
```bash
# Check if the vector database file exists
ls -la ./knowledge/vector.db

# Test Milvus Lite directly
python -c "from pymilvus import MilvusClient; client = MilvusClient('./test.db'); print('Milvus Lite working')"

# Clear and recreate vector database
rm -f ./knowledge/vector.db
unfold index --rebuild-vector-db
```

#### 2. Neo4j Connection Failed
```bash
# Check if Neo4j is running
# For Neo4j Desktop: Check the Desktop app
# For command line installation:
neo4j status

# Start Neo4j if not running
neo4j start

# Check Neo4j web interface
open http://localhost:7474
```

#### 3. Neo4j Authentication Failed
```bash
# Reset Neo4j password (command line)
neo4j-admin dbms set-initial-password newpassword

# Or connect via web interface (http://localhost:7474) and change password
```

#### 4. Ollama Model Not Found
```bash
# List available models
ollama list

# Pull required model
ollama pull llama3.2

# Check Ollama service
curl http://localhost:11434/api/tags
```

#### 5. Java Not Found (Neo4j)
```bash
# Install Java 21 on macOS
brew install openjdk@21

# Install Java 21 on Ubuntu/Debian
sudo apt install openjdk-21-jdk

# Check Java version
java -version
```

#### 6. Vector Database Index Failed
```bash
# Check embedding model
python -c "from sentence_transformers import SentenceTransformer; print(SentenceTransformer('all-MiniLM-L6-v2'))"

# Clear and rebuild vector index
unfold ai
🤖 Ask me anything: Please rebuild the vector database index
```

### Health Checks

```bash
# Check all services
unfold stats

# Test AI assistant
unfold ai
🤖 Ask me anything: stats
```

### Performance Tuning

#### For Large Codebases (>10k files)
```json
{
  "vector_db": {
    "use_milvus_lite": true,
    "local_db_path": "./knowledge/vector.db",
    "chunk_size": 1024,
    "chunk_overlap": 100
  },
  "indexing": {
    "indexing_batch_size": 2000
  },
  "performance": {
    "database_cache_size": 500
  }
}
```

#### For Low Memory Systems
```json
{
  "vector_db": {
    "use_milvus_lite": true,
    "local_db_path": "./knowledge/vector.db",
    "chunk_size": 256,
    "embedding_model": "all-MiniLM-L12-v2"
  },
  "llm": {
    "max_tokens": 1024
  },
  "graph_db": {
    "enabled": false
  }
}
```

## Security Considerations

### Environment Variables
```bash
# Use environment variables for sensitive data
export UNFOLD_OPENAI_API_KEY="your-key"
export UNFOLD_NEO4J_PASSWORD="your-password"
```

### Configuration
```json
{
  "llm": {
    "api_key": "${UNFOLD_OPENAI_API_KEY}"
  },
  "graph_db": {
    "password": "${UNFOLD_NEO4J_PASSWORD}"
  }
}
```

### Network Security
- Use TLS for production deployments
- Configure firewall rules for database ports
- Use authentication for all services

## Development Setup

### Running Tests
```bash
# Install test dependencies
pip install -e ".[dev]"

# Run tests
pytest tests/

# Run AI-specific tests
pytest tests/test_ai_integration.py
```

### Development Configuration
```json
{
  "ai_assistant": {
    "enabled": true,
    "streaming_response": true,
    "context_window": 10,
    "memory_retention_days": 7
  },
  "vector_db": {
    "enabled": true,
    "use_milvus_lite": true,
    "local_db_path": "./knowledge/dev_vector.db"
  },
  "graph_db": {
    "enabled": true,
    "database": "unfold_dev"
  }
}
```

## Support

For issues and questions:
1. Check the logs: `~/.local/share/unfold/logs/`
2. Verify configuration: `unfold stats`
3. Test services individually:
   - Test Milvus Lite: `python -c "from pymilvus import MilvusClient; print('OK')"`
   - Test Neo4j: Visit `http://localhost:7474` in browser
   - Test Ollama: `curl http://localhost:11434/api/tags`
4. Check service status:
   - Neo4j: `neo4j status` (if using command line)
   - Ollama: `ollama list`
5. Review this guide for common solutions

## Next Steps

Once setup is complete:
1. Index your project directories
2. Explore AI assistant capabilities
3. Configure monitoring for important paths
4. Customize the system prompt for your workflow
5. Set up automated knowledge base updates 