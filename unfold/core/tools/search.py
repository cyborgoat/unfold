"""
Search and indexing tools for MCP integration.
"""

import os
from datetime import datetime
from pathlib import Path
from typing import Any


class SearchTools:
    """Tools for search and indexing operations."""

    def __init__(self, working_directory: str = None, file_searcher=None, file_indexer=None, vector_db=None, graph_service=None):
        """Initialize search tools."""
        self.working_directory = working_directory or os.getcwd()
        self.file_searcher = file_searcher
        self.file_indexer = file_indexer
        self.vector_db = vector_db
        self.graph_service = graph_service

    async def search_files(self, query: str, file_types: list[str] = None, max_results: int = 20) -> dict[str, Any]:
        """Search for files using traditional indexing."""
        try:
            if not self.file_searcher:
                return {"success": False, "error": "File searcher not available"}

            results = self.file_searcher.search(
                query=query,
                file_types=file_types,
                files_only=False,
                directories_only=False
            )

            formatted_results = []
            for result in results[:max_results]:
                formatted_results.append({
                    "path": str(result.path),
                    "name": result.name,
                    "score": result.score,
                    "type": "directory" if result.is_directory else "file",
                    "size": result.size,
                    "file_type": result.file_type,
                    "match_type": result.match_type
                })

            return {
                "success": True,
                "query": query,
                "results": formatted_results,
                "total_found": len(results),
                "returned": len(formatted_results)
            }

        except Exception as e:
            return {"success": False, "error": f"Search failed: {str(e)}"}

    async def semantic_search(self, query: str, max_results: int = 10) -> dict[str, Any]:
        """Perform semantic search using vector database."""
        try:
            if not self.vector_db:
                return {"success": False, "error": "Vector database not available"}

            results = await self.vector_db.search(query, top_k=max_results)

            formatted_results = []
            for result in results:
                formatted_results.append({
                    "content": result.get("content", ""),
                    "file_path": result.get("metadata", {}).get("file_path", ""),
                    "score": result.get("score", 0.0),
                    "chunk_index": result.get("metadata", {}).get("chunk_index", 0),
                    "file_type": result.get("metadata", {}).get("file_type", ""),
                    "size": result.get("metadata", {}).get("size", 0)
                })

            return {
                "success": True,
                "query": query,
                "results": formatted_results,
                "total_found": len(results)
            }

        except Exception as e:
            return {"success": False, "error": f"Semantic search failed: {str(e)}"}

    async def index_directory(self, directory: str = None, recursive: bool = True, force_rebuild: bool = False) -> dict[str, Any]:
        """Index directory for search capabilities."""
        try:
            target_dir = directory or self.working_directory
            
            if not Path(target_dir).exists():
                return {"success": False, "error": f"Directory does not exist: {target_dir}"}

            files_indexed = 0
            errors = []

            # Traditional indexing
            if self.file_indexer:
                try:
                    if force_rebuild:
                        # Clear existing index for this directory
                        pass  # Implement if needed
                    
                    def progress_callback(count, message):
                        nonlocal files_indexed
                        files_indexed = count

                    self.file_indexer.index_directory(
                        target_dir,
                        recursive=recursive,
                        progress_callback=progress_callback
                    )
                except Exception as e:
                    errors.append(f"Traditional indexing error: {str(e)}")

            # Vector indexing
            if self.vector_db:
                try:
                    await self.vector_db.index_directory(target_dir)
                except Exception as e:
                    errors.append(f"Vector indexing error: {str(e)}")

            # Graph indexing
            if self.graph_service:
                try:
                    self.graph_service.index_directory(target_dir, recursive=recursive)
                except Exception as e:
                    errors.append(f"Graph indexing error: {str(e)}")

            return {
                "success": len(errors) == 0,
                "directory": target_dir,
                "files_indexed": files_indexed,
                "recursive": recursive,
                "force_rebuild": force_rebuild,
                "errors": errors if errors else None,
                "timestamp": datetime.now().isoformat()
            }

        except Exception as e:
            return {"success": False, "error": f"Indexing failed: {str(e)}"}

    async def get_file_relationships(self, file_path: str) -> dict[str, Any]:
        """Get file relationships from knowledge graph."""
        try:
            if not self.graph_service:
                return {"success": False, "error": "Graph service not available"}

            relationships = self.graph_service.get_file_relationships(file_path)

            return {
                "success": True,
                "file_path": file_path,
                "relationships": relationships,
                "total_relationships": len(relationships)
            }

        except Exception as e:
            return {"success": False, "error": f"Failed to get relationships: {str(e)}"}

    async def search_memory(self, query: str, memory_type: str = "all", max_results: int = 10) -> dict[str, Any]:
        """Search stored memories."""
        try:
            if not self.vector_db:
                return {"success": False, "error": "Vector database not available for memory search"}

            # Search in memory collection
            results = await self.vector_db.search_memory(query, max_results)

            formatted_results = []
            for result in results:
                metadata = result.get("metadata", {})
                formatted_results.append({
                    "content": result.get("content", ""),
                    "memory_type": metadata.get("memory_type", "unknown"),
                    "importance": metadata.get("importance", 1.0),
                    "tags": metadata.get("tags", []),
                    "timestamp": metadata.get("timestamp", ""),
                    "source": metadata.get("source", ""),
                    "score": result.get("score", 0.0)
                })

            return {
                "success": True,
                "query": query,
                "memory_type": memory_type,
                "results": formatted_results,
                "total_found": len(results)
            }

        except Exception as e:
            return {"success": False, "error": f"Memory search failed: {str(e)}"} 