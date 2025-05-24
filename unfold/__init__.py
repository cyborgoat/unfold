"""
Unfold - A superfast file/folder locator with advanced search algorithms.
"""

__version__ = "0.1.0"
__author__ = "Your Name"

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