"""
Unfold - AI-Enhanced superfast file/folder locator with advanced indexing, search algorithms, and intelligent assistance.

This package provides high-performance file system indexing and searching capabilities
with support for fuzzy matching, real-time monitoring, intelligent ranking, and AI-powered assistance.

Features:
- Lightning-fast file indexing with inverted indexes
- Advanced search algorithms (exact, fuzzy, semantic, vector similarity)
- Real-time file system monitoring with AI services integration
- Knowledge graph for understanding file relationships
- Vector database for semantic content search
- AI assistant with LLM integration (Ollama/OpenAI)
- MCP protocol for tool integration
- Frequency and recency-based ranking
- Rich terminal UI with colorful output
- Extensible architecture for custom search providers
"""

__version__ = "0.2.0"
__author__ = "Cyborgoat"

# Import core components conditionally
try:
    from .core.database import DatabaseManager
    __all__ = ["DatabaseManager"]
except ImportError:
    __all__ = []

try:
    from .core.indexer import FileIndexer
    __all__.append("FileIndexer")
except ImportError:
    pass

try:
    from .core.searcher import FileSearcher
    __all__.append("FileSearcher")
except ImportError:
    pass

# Import AI components conditionally
try:
    from .core.llm_service import LLMService
    __all__.append("LLMService")
except ImportError:
    pass

try:
    from .core.vector_db import VectorDBService
    __all__.append("VectorDBService")
except ImportError:
    pass

try:
    from .core.networkx_graph_service import NetworkXGraphService
    __all__.append("NetworkXGraphService")
except ImportError:
    pass

# Note: GraphRAGService (Neo4j) import is conditional and only done when needed
# to avoid connection attempts during module import

try:
    from .core.mcp_service import UnfoldMCPService
    __all__.append("UnfoldMCPService")
except ImportError:
    pass

try:
    from .utils.config import ConfigManager
    __all__.append("ConfigManager")
except ImportError:
    pass
