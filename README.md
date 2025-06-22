# Unfold 🔍🤖

An AI-enhanced superfast file/folder locator written in Python that combines advanced indexing algorithms with powerful search capabilities and intelligent assistance. Unfold brings the speed and intelligence of modern search engines and AI to your local file system.

## ✨ Features

### 🤖 **AI-Powered Intelligence**
- **AI Assistant**: Interactive AI that understands your project and helps find files intelligently
- **Vector Similarity Search**: Find files by semantic content similarity using state-of-the-art embeddings
- **Knowledge Graph**: Understands relationships between files, imports, and project structure
- **Memory System**: Short-term and long-term memory for context-aware conversations
- **Graph Visualization**: Interactive popup windows showing your project's knowledge graph
- **Streaming Responses**: Real-time AI responses for immediate assistance

### 🔧 **Modular & Extensible**
- **Decoupled MCP Tools**: Use Unfold's capabilities in other applications via MCP protocol
- **Standalone MCP Server**: Run as a service for IDE autocompletion and code analysis
- **Pluggable Services**: Mix and match traditional search, vector DB, and graph services
- **Multiple Providers**: Support for Ollama, OpenAI, Milvus Lite, Neo4j, and NetworkX
- **Zero Dependencies Mode**: Core functionality works without any AI services

### 🚀 **Lightning Fast Search**
- **Inverted Indexing**: Pre-processes and indexes your files for instant search results
- **Multiple Search Algorithms**: Exact match, fuzzy matching, semantic search, and AI-powered queries
- **Intelligent Ranking**: Combines frequency, recency, relevance, and AI-enhanced scoring
- **Result Caching**: Frequently searched queries are cached for even faster access

### 🧠 **Smart Algorithms**
- **Fuzzy Matching**: Find files even with typos using Levenshtein distance and Jaro-Winkler similarity
- **Frequency & Recency (FR)**: Prioritizes recently and frequently accessed files
- **N-gram Indexing**: Enhanced partial matching capabilities
- **File Type Intelligence**: Smart bonuses for different file types based on context
- **Graph Relationships**: Understands code imports, dependencies, and file connections

### 🔄 **Real-time Monitoring**
- **File System Watching**: Automatically updates index when files change
- **AI-Enhanced Indexing**: Real-time updates to vector database and knowledge graph
- **Incremental Updates**: Only processes changed files for efficiency
- **Background Processing**: Non-intrusive monitoring that doesn't slow down your system

### 🎨 **Beautiful Interface**
- **Rich Terminal UI**: Colorful, formatted output with tables and progress bars
- **AI Chat Interface**: Natural language interaction with your file system
- **Interactive Mode**: Live search with instant results
- **Command-line Tools**: Full CLI support for automation and scripting

## 📦 Installation

### Using UV (Recommended)

```bash
# Clone the repository
git clone https://github.com/cyborgoat/unfold.git
cd unfold

# Install with UV
uv pip install -e .

# Or install dependencies manually
uv pip install -r requirements.txt
```

### Using Pip

```bash
# Clone and install
git clone https://github.com/cyborgoat/unfold.git
cd unfold
pip install -e .
```

## 🚀 Quick Start

### 1. **Install and Setup**
```bash
# Install with AI features
pip install -e ".[dev]"

# Quick setup for AI features (see AI_SETUP.md for full setup)
docker-compose up -d  # Start Milvus and Neo4j
ollama serve && ollama pull llama3.2  # Start Ollama with a model
```

### 2. **Index Your Files**
```bash
# Index your home directory with AI enhancement
unfold index ~/

# Index specific directories
unfold index ~/Documents ~/Downloads ~/Projects

# Index with options (now includes vector DB and knowledge graph)
unfold index ~/Code --hidden --recursive
```

### 3. **Start AI Assistant**
```bash
# Launch AI assistant mode
unfold ai

# Example AI interactions:
🤖 Ask me anything: Find all Python files that import pandas
🤖 Ask me anything: What's the structure of this project?
🤖 Ask me anything: Show me files similar to main.py
🤖 Ask me anything: Find configuration files in the backend folder
```

### 4. **Traditional Search (Still Available)**
```bash
# Interactive mode (default)
unfold

# Direct search
unfold search "my-project"

# Search with filters
unfold search "readme" --type .md --type .txt
unfold search "config" --files-only
```

### 5. **Real-time Monitoring**
```bash
# Monitor directories for changes (now includes AI indexing)
unfold monitor ~/Documents ~/Projects

# Run as background daemon
unfold monitor ~/Code --daemon
```

## 📋 Usage Examples

### AI Assistant Mode
```bash
$ unfold ai --workdir ~/my-project

🤖 Unfold AI Assistant
Working Directory: /home/user/my-project
Services: ✓ LLM (Ollama) ✓ Vector DB (Milvus Lite) ✓ Knowledge Graph (NetworkX)
Available tools: search_files, semantic_search, visualize_knowledge_graph, store_memory, search_memory

🤖 Ask me anything: Show me the knowledge graph

✓ Knowledge graph displayed with 156 nodes and 203 edges

🤖 Ask me anything: Find files related to authentication

📊 Semantic Search Results:
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━┓
┃ File Path                                                        ┃ Content Preview                                                  ┃ Score  ┃
┡━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━┩
│ src/auth/authentication.py                                      │ class AuthenticationManager: def login(self, username, password │ 0.89   │
│ src/middleware/auth_middleware.py                               │ JWT token validation and user authentication middleware...        │ 0.85   │
│ tests/test_auth.py                                              │ Unit tests for authentication system with mock users...          │ 0.78   │
└──────────────────────────────────────────────────────────────────┴──────────────────────────────────────────────────────────────────┴────────┘

🤖 Ask me anything: Store this: "Authentication uses JWT tokens, main file is src/auth/authentication.py"

✓ Stored long_term memory (importance: 0.8, tags: [])

🤖 Ask me anything: What do you remember about authentication?

📝 Memory Search Results:
- Authentication uses JWT tokens, main file is src/auth/authentication.py (similarity: 0.95)
```

### Interactive Search Mode
```bash
$ unfold

🔍 Search: python
┏━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━┳━━━━━━━━━━┳━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ Score  ┃ Name                 ┃ Type   ┃ Size     ┃ Match      ┃ Path                                        ┃
┡━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━╇━━━━━━━━━━╇━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┩
│ 98.5   │ python              │ FILE   │ 2.1 MB   │ exact      │ /usr/bin/python                             │
│ 89.2   │ python3             │ FILE   │ 2.1 MB   │ starts_with│ /usr/bin/python3                            │
│ 78.1   │ my_python_script.py │ .py    │ 1.2 KB   │ contains   │ ~/Documents/scripts/my_python_script.py     │
│ 67.8   │ requirements.txt    │ .txt   │ 245 B    │ fuzzy_high │ ~/Projects/python-app/requirements.txt     │
└────────┴──────────────────────┴────────┴──────────┴────────────┴─────────────────────────────────────────────┘

Found 4 results
```

### Command-line Search
```bash
# Search for Python files
$ unfold search "test" --type .py
$ unfold search "config" --dirs-only
$ unfold search "readme" --limit 10

# Recent and frequent files
$ unfold search --recent
$ unfold search --frequent
```

### Advanced Features
```bash
# View statistics
$ unfold stats

# Clear search cache
$ unfold clear --cache-only

# Rebuild entire index
$ unfold index ~/Documents --rebuild
```

## ⚙️ Configuration

Unfold stores configuration in your system's config directory:
- **macOS**: `~/Library/Application Support/unfold/config.json`
- **Linux**: `~/.config/unfold/config.json`
- **Windows**: `%APPDATA%\unfold\config.json`

### Example Configuration
```json
{
  "indexing": {
    "index_hidden_files": false,
    "index_directories": true,
    "excluded_extensions": [".tmp", ".log", ".cache"],
    "excluded_paths": [".git", "node_modules", "__pycache__"],
    "watch_paths": ["~/Documents", "~/Projects"]
  },
  "search": {
    "enable_fuzzy_matching": true,
    "fuzzy_threshold": 0.6,
    "max_results": 50,
    "cache_results": true
  },
  "llm": {
    "provider": "ollama",
    "model": "llama3.2",
    "base_url": "http://localhost:11434"
  },
  "vector_db": {
    "enabled": true,
    "use_milvus_lite": true,
    "local_db_path": "./knowledge/vector.db",
    "embedding_model": "Qwen/Qwen3-Embedding-0.6B"
  },
  "graph_db": {
    "enabled": true,
    "provider": "networkx",
    "local_db_path": "./knowledge/graph.json"
  },
  "mcp": {
    "enabled": true,
    "working_directory": null
  }
}
```

## 🏗️ Architecture

### Modular Design

```
unfold/
├── core/
│   ├── database.py              # SQLite database management
│   ├── indexer.py              # File system indexing
│   ├── searcher.py             # Search algorithms and ranking
│   ├── vector_db.py            # Vector database (Milvus/Milvus Lite)
│   ├── networkx_graph_service.py # Knowledge graph (NetworkX)
│   ├── llm_service.py          # LLM integration (Ollama/OpenAI)
│   ├── mcp_service.py          # MCP protocol service
│   └── mcp_tools.py            # Decoupled tools for reuse
├── utils/
│   └── config.py               # Configuration management
├── cli.py                      # Command-line interface
├── mcp_server.py              # Standalone MCP server
└── knowledge/                  # AI knowledge storage
    ├── files/                  # Vector embeddings
    ├── memory/                 # Conversation memory
    ├── graph/                  # Knowledge graph data
    └── sessions/               # Session logs
```

### Tool Decoupling

The new `UnfoldTools` class provides decoupled access to all functionality:

```python
from unfold.core.mcp_tools import UnfoldTools

# Create tools instance
tools = UnfoldTools(
    searcher=searcher,
    vector_db=vector_db,
    graph_service=graph_service,
    working_directory="/path/to/project"
)

# Use in any application
results = await tools.semantic_search("authentication code")
await tools.visualize_knowledge_graph()
await tools.store_memory("Important project info", "long_term")
```

### Key Algorithms

1. **Inverted Indexing**: Maps keywords to files for O(1) lookup
2. **Fuzzy Matching**: Multiple similarity algorithms with configurable thresholds
3. **FR Scoring**: Frequency × Recency with time decay functions
4. **Incremental Updates**: Real-time file system monitoring with efficient updates

## 🔧 Development

### Setup Development Environment
```bash
# Clone repository
git clone https://github.com/cyborgoat/unfold.git
cd unfold

# Install development dependencies
uv pip install -e ".[dev]"

# Run tests
pytest

# Format code
black unfold/
flake8 unfold/

# Type checking
mypy unfold/
```

### Running Tests
```bash
# All tests
pytest

# With coverage
pytest --cov=unfold --cov-report=html

# Specific test categories
pytest tests/test_indexer.py
pytest tests/test_searcher.py
```

## 📊 Performance

- **Indexing Speed**: ~10,000 files per second (SSD)
- **Search Latency**: <10ms for most queries
- **Memory Usage**: ~50MB for 100,000 indexed files
- **Database Size**: ~1KB per 100 indexed files

### Benchmarks
```
File Count    | Index Time | Search Time | Memory Usage
------------- | ---------- | ----------- | ------------
1,000         | 0.1s       | <1ms        | 15MB
10,000        | 1.2s       | 2ms         | 25MB
100,000       | 12s        | 5ms         | 50MB
1,000,000     | 2min       | 8ms         | 180MB
```

## 🤝 Contributing

We welcome contributions! Please see our [Contributing Guide](CONTRIBUTING.md) for details.

### Areas for Contribution
- **Algorithm Improvements**: Better ranking, faster indexing
- **UI/UX**: Enhanced terminal interface, GUI development
- **Platform Support**: Windows optimization, mobile interfaces
- **Documentation**: Examples, tutorials, API docs

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- **Algorithms**: Inspired by academic research in information retrieval
- **Libraries**: Built on excellent Python packages like `watchdog`, `click`, and `rich`
- **Community**: Thanks to all contributors and users providing feedback

## 🔗 Related Projects

- [Alfred](https://www.alfredapp.com/) - macOS productivity app
- [Everything](https://www.voidtools.com/) - Windows file search
- [fzf](https://github.com/junegunn/fzf) - Command-line fuzzy finder
- [ripgrep](https://github.com/BurntSushi/ripgrep) - Fast text search

---

**Made with ❤️ for developers who value speed and precision in file management.**
