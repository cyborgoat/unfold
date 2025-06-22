"""
Comprehensive MCP Tools for Unfold - Filesystem Agent with Analysis and Action Capabilities.

This module provides decoupled tools that can work independently or as part of the main Unfold system.
Tools are organized by category and include filesystem operations, analysis, and AI-powered insights.
"""

import os
from typing import Any

from .database import DatabaseManager
from .indexer import FileIndexer
from .searcher import FileSearcher
from .tools import (
    AnalysisTools,
    FilesystemTools,
    MemoryTools,
    SearchTools,
    SystemTools,
    VisualizationTools,
)


class UnfoldTools:
    """
    Comprehensive filesystem agent tools for MCP integration.
    
    These tools provide a complete suite of filesystem operations, analysis,
    and AI-powered insights that can work independently or as part of Unfold.
    """

    def __init__(self, config_manager=None, working_directory: str = None):
        """Initialize tools with optional services."""
        self.config_manager = config_manager
        self.working_directory = working_directory or os.getcwd()

        # Core services (always available)
        self.db_manager = None
        self.file_indexer = None
        self.file_searcher = None

        # AI services (optional)
        self.llm_service = None
        self.vector_db = None
        self.graph_service = None

        # Initialize core services
        self._init_core_services()

        # Initialize AI services if config is available
        if config_manager:
            self._init_ai_services()

        # Initialize tool modules
        self.filesystem = FilesystemTools(self.working_directory, self.file_indexer, self.db_manager)
        self.search = SearchTools(self.working_directory, self.file_searcher, self.file_indexer, self.vector_db, self.graph_service)
        self.analysis = AnalysisTools(self.working_directory, self.llm_service)
        self.system = SystemTools(self.working_directory)
        self.memory = MemoryTools(self.working_directory, self.vector_db)
        self.visualization = VisualizationTools(self.working_directory, self.graph_service)

    def _init_core_services(self):
        """Initialize core filesystem services."""
        try:
            self.db_manager = DatabaseManager()
            self.file_indexer = FileIndexer(self.db_manager)
            self.file_searcher = FileSearcher(self.db_manager)
        except Exception as e:
            print(f"Warning: Core services initialization failed: {e}")

    def _init_ai_services(self):
        """Initialize AI services if configuration is available."""
        try:
            # Vector Database
            try:
                from .vector_db import VectorDBService
                self.vector_db = VectorDBService(self.config_manager)
            except Exception:
                pass

            # Graph Service
            try:
                from .networkx_graph_service import NetworkXGraphService
                self.graph_service = NetworkXGraphService()
            except Exception:
                pass

            # LLM Service
            try:
                from .llm_service import LLMService
                self.llm_service = LLMService(config_manager=self.config_manager)
            except Exception as e:
                print(f"Failed to initialize LLM client: {e}")
                pass

        except Exception as e:
            print(f"Warning: AI services initialization failed: {e}")

    # ==================== FILESYSTEM OPERATIONS ====================

    async def list_directory(self, path: str = None, show_hidden: bool = False, recursive: bool = False) -> dict[str, Any]:
        """List directory contents with detailed information."""
        return await self.filesystem.list_directory(path, show_hidden, recursive)

    async def read_file(self, file_path: str, encoding: str = "utf-8", max_size: int = 1024*1024) -> dict[str, Any]:
        """Read file content with safety checks."""
        return await self.filesystem.read_file(file_path, encoding, max_size)

    async def write_file(self, file_path: str, content: str, encoding: str = "utf-8", backup: bool = True) -> dict[str, Any]:
        """Write content to file with optional backup."""
        return await self.filesystem.write_file(file_path, content, encoding, backup)

    async def delete_file(self, file_path: str, force: bool = False) -> dict[str, Any]:
        """Delete file or directory with safety checks."""
        return await self.filesystem.delete_file(file_path, force)

    async def create_directory(self, dir_path: str, parents: bool = True) -> dict[str, Any]:
        """Create directory with optional parent creation."""
        return await self.filesystem.create_directory(dir_path, parents)

    async def move_file(self, src_path: str, dest_path: str, overwrite: bool = False) -> dict[str, Any]:
        """Move/rename file or directory."""
        return await self.filesystem.move_file(src_path, dest_path, overwrite)

    async def copy_file(self, src_path: str, dest_path: str, overwrite: bool = False) -> dict[str, Any]:
        """Copy file or directory."""
        return await self.filesystem.copy_file(src_path, dest_path, overwrite)

    # ==================== SEARCH AND INDEXING ====================

    async def search_files(self, query: str, file_types: list[str] = None, max_results: int = 20) -> dict[str, Any]:
        """Search for files using traditional indexing."""
        return await self.search.search_files(query, file_types, max_results)

    async def semantic_search(self, query: str, max_results: int = 10) -> dict[str, Any]:
        """Perform semantic search using vector database."""
        return await self.search.semantic_search(query, max_results)

    async def index_directory(self, directory: str = None, recursive: bool = True, force_rebuild: bool = False) -> dict[str, Any]:
        """Index directory for search capabilities."""
        return await self.search.index_directory(directory, recursive, force_rebuild)

    async def get_file_relationships(self, file_path: str) -> dict[str, Any]:
        """Get file relationships from knowledge graph."""
        return await self.search.get_file_relationships(file_path)

    # ==================== AI-POWERED ANALYSIS ====================

    async def analyze_file_content(self, file_path: str) -> dict[str, Any]:
        """Analyze file content using AI."""
        return await self.analysis.analyze_file_content(file_path)

    async def suggest_file_improvements(self, file_path: str) -> dict[str, Any]:
        """Suggest improvements for a file using AI."""
        return await self.analysis.suggest_file_improvements(file_path)

    async def analyze_project_structure(self, directory: str = None) -> dict[str, Any]:
        """Analyze overall project structure and provide insights."""
        return await self.analysis.analyze_project_structure(directory)

    async def detect_code_patterns(self, directory: str = None, file_extensions: list[str] = None) -> dict[str, Any]:
        """Detect common code patterns and anti-patterns in the project."""
        return await self.analysis.detect_code_patterns(directory, file_extensions)

    # ==================== SYSTEM OPERATIONS ====================

    async def execute_command(self, command: str, working_dir: str = None, timeout: int = 30) -> dict[str, Any]:
        """Execute shell command with safety checks."""
        return await self.system.execute_command(command, working_dir, timeout)

    async def get_system_info(self) -> dict[str, Any]:
        """Get system and environment information."""
        return await self.system.get_system_info()

    async def clear_cache(self, cache_type: str = "all") -> dict[str, Any]:
        """Clear various caches and temporary data."""
        return await self.system.clear_cache(cache_type)

    async def get_environment_variables(self, filter_pattern: str = None) -> dict[str, Any]:
        """Get environment variables, optionally filtered."""
        return await self.system.get_environment_variables(filter_pattern)

    async def check_disk_space(self, path: str = None) -> dict[str, Any]:
        """Check disk space for a given path."""
        return await self.system.check_disk_space(path)

    # ==================== MEMORY OPERATIONS ====================

    async def store_memory(self, content: str, memory_type: str = "short_term", 
                          importance: float = 1.0, tags: str = "", source: str = "") -> dict[str, Any]:
        """Store information in memory with metadata."""
        return await self.memory.store_memory(content, memory_type, importance, tags, source)

    async def search_memory(self, query: str, memory_type: str = "all", max_results: int = 10) -> dict[str, Any]:
        """Search stored memories."""
        return await self.memory.search_memory(query, memory_type, max_results)

    async def get_memory_stats(self) -> dict[str, Any]:
        """Get statistics about stored memories."""
        return await self.memory.get_memory_stats()

    async def clear_memory(self, memory_type: str = None, older_than_days: int = None) -> dict[str, Any]:
        """Clear memories based on criteria."""
        return await self.memory.clear_memory(memory_type, older_than_days)

    async def summarize_conversation(self, conversation_content: str, importance: float = 1.5) -> dict[str, Any]:
        """Summarize and store conversation for long-term memory."""
        return await self.memory.summarize_conversation(conversation_content, importance)

    # ==================== VISUALIZATION ====================

    async def visualize_knowledge_graph(self) -> dict[str, Any]:
        """Display the knowledge graph in an interactive popup window."""
        return await self.visualization.visualize_knowledge_graph()

    async def export_graph_data(self, format_type: str = "json", output_path: str = None) -> dict[str, Any]:
        """Export graph data in various formats."""
        return await self.visualization.export_graph_data(format_type, output_path)

    async def generate_graph_statistics(self) -> dict[str, Any]:
        """Generate detailed statistics about the knowledge graph."""
        return await self.visualization.generate_graph_statistics()

    # ==================== TOOL REGISTRY ====================

    def get_available_tools(self) -> list[dict[str, Any]]:
        """Get list of all available tools with their descriptions."""
        tools = [
            # Filesystem Operations
            {"name": "list_directory", "category": "filesystem", "description": "List directory contents with detailed information"},
            {"name": "read_file", "category": "filesystem", "description": "Read file content with safety checks"},
            {"name": "write_file", "category": "filesystem", "description": "Write content to file with optional backup"},
            {"name": "delete_file", "category": "filesystem", "description": "Delete file or directory with safety checks"},
            {"name": "create_directory", "category": "filesystem", "description": "Create directory with optional parent creation"},
            {"name": "move_file", "category": "filesystem", "description": "Move/rename file or directory"},
            {"name": "copy_file", "category": "filesystem", "description": "Copy file or directory"},
            
            # Search and Indexing
            {"name": "search_files", "category": "search", "description": "Search for files using traditional indexing"},
            {"name": "semantic_search", "category": "search", "description": "Perform semantic search using vector database"},
            {"name": "index_directory", "category": "search", "description": "Index directory for search capabilities"},
            {"name": "get_file_relationships", "category": "search", "description": "Get file relationships from knowledge graph"},
            
            # AI-Powered Analysis
            {"name": "analyze_file_content", "category": "analysis", "description": "Analyze file content using AI"},
            {"name": "suggest_file_improvements", "category": "analysis", "description": "Suggest improvements for a file using AI"},
            {"name": "analyze_project_structure", "category": "analysis", "description": "Analyze overall project structure and provide insights"},
            {"name": "detect_code_patterns", "category": "analysis", "description": "Detect common code patterns and anti-patterns"},
            
            # System Operations
            {"name": "execute_command", "category": "system", "description": "Execute shell command with safety checks"},
            {"name": "get_system_info", "category": "system", "description": "Get system and environment information"},
            {"name": "clear_cache", "category": "system", "description": "Clear various caches and temporary data"},
            {"name": "get_environment_variables", "category": "system", "description": "Get environment variables, optionally filtered"},
            {"name": "check_disk_space", "category": "system", "description": "Check disk space for a given path"},
            
            # Memory Operations
            {"name": "store_memory", "category": "memory", "description": "Store information in memory with metadata"},
            {"name": "search_memory", "category": "memory", "description": "Search stored memories"},
            {"name": "get_memory_stats", "category": "memory", "description": "Get statistics about stored memories"},
            {"name": "clear_memory", "category": "memory", "description": "Clear memories based on criteria"},
            {"name": "summarize_conversation", "category": "memory", "description": "Summarize and store conversation for long-term memory"},
            
            # Visualization
            {"name": "visualize_knowledge_graph", "category": "visualization", "description": "Display the knowledge graph in an interactive popup window"},
            {"name": "export_graph_data", "category": "visualization", "description": "Export graph data in various formats"},
            {"name": "generate_graph_statistics", "category": "visualization", "description": "Generate detailed statistics about the knowledge graph"},
        ]
        
        return tools
