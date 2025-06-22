"""
File system indexer with real-time monitoring and metadata extraction.
"""

import logging
import os
import threading
import time
from collections.abc import Callable
from pathlib import Path

from watchdog.events import FileSystemEvent, FileSystemEventHandler
from watchdog.observers import Observer

from .database import DatabaseManager


class IndexingHandler(FileSystemEventHandler):
    """File system event handler for real-time indexing with AI services."""

    def __init__(self, indexer: "FileIndexer"):
        self.indexer = indexer
        self.logger = logging.getLogger(__name__)

        # Initialize AI services for indexing
        from unfold.utils.config import ConfigManager
        config_manager = ConfigManager()

        # Initialize graph service
        try:
            graph_provider = config_manager.get("graph_db.provider", "networkx")
            if graph_provider == "networkx":
                from .networkx_graph_service import NetworkXGraphService
                self.graph_service = NetworkXGraphService(config_manager)
            else:
                try:
                    from .graph_service import GraphService
                    self.graph_service = GraphService(config_manager)
                except ImportError:
                    # Fallback to NetworkX if Neo4j GraphService not available
                    from .networkx_graph_service import NetworkXGraphService
                    self.graph_service = NetworkXGraphService(config_manager)
        except Exception as e:
            self.logger.warning(f"Graph service not available: {e}")
            self.graph_service = None

    def on_created(self, event: FileSystemEvent) -> None:
        """Handle file/directory creation."""
        if not event.is_directory or self.indexer.index_directories:
            self._process_file_event("created", event.src_path)

    def on_modified(self, event: FileSystemEvent) -> None:
        """Handle file/directory modification."""
        if not event.is_directory or self.indexer.index_directories:
            self._process_file_event("modified", event.src_path)

    def on_moved(self, event: FileSystemEvent) -> None:
        """Handle file/directory move."""
        # Remove old path from all services
        self.indexer.db.remove_file(event.src_path)

        # Index new path if it's not a directory or we index directories
        if not event.is_directory or self.indexer.index_directories:
            self._process_file_event("moved", event.dest_path, event.src_path)

    def on_deleted(self, event: FileSystemEvent) -> None:
        """Handle file/directory deletion."""
        self.indexer.db.remove_file(event.src_path)
        self.logger.info(f"Removed file from index: {event.src_path}")

    def _process_file_event(self, event_type: str, file_path: str, old_path: str = None):
        """Process file events and update all relevant services."""
        try:
            # Index file in traditional database
            self.indexer._index_single_path(file_path)

            # If AI services are available, also index in vector DB and graph
            if hasattr(self.indexer, 'vector_db') and self.indexer.vector_db:
                self._index_in_vector_db(file_path)

            if hasattr(self.indexer, 'graph_service') and self.indexer.graph_service:
                self._index_in_knowledge_graph(file_path)

                # Remove old graph node if this was a move operation
                if old_path and event_type == "moved":
                    self.indexer.graph_service.remove_file_node(old_path)

            self.logger.info(f"Processed {event_type} event for: {file_path}")

        except Exception as e:
            self.logger.error(f"Error processing {event_type} event for {file_path}: {e}")

    def _index_in_vector_db(self, file_path: str):
        """Index file content in vector database."""
        try:
            path_obj = Path(file_path)
            if path_obj.is_file() and self._is_text_file(file_path):
                with open(path_obj, encoding='utf-8', errors='ignore') as f:
                    content = f.read()

                # Index content in vector database
                self.indexer.vector_db.index_file_content(
                    file_path=file_path,
                    content=content,
                    metadata={"indexed_at": time.time()}
                )
        except Exception as e:
            self.logger.error(f"Error indexing {file_path} in vector DB: {e}")

    def _index_in_knowledge_graph(self, file_path: str):
        """Index file in knowledge graph."""
        try:
            path_obj = Path(file_path)
            content = None

            # Read content for code files to extract relationships
            if path_obj.is_file() and self._is_code_file(file_path):
                try:
                    with open(path_obj, encoding='utf-8', errors='ignore') as f:
                        content = f.read()
                except Exception:
                    pass  # Continue without content if read fails

            # Index in knowledge graph
            if self.graph_service:
                self.graph_service.index_file(
                    file_path=file_path,
                    content=content
                )
        except Exception as e:
            self.logger.error(f"Error indexing {file_path} in knowledge graph: {e}")

    def _is_text_file(self, file_path: str) -> bool:
        """Check if file is a text file for vector indexing."""
        text_extensions = {'.txt', '.md', '.json', '.py', '.js', '.ts', '.java', '.cpp', '.c', '.h', '.go', '.rs', '.php', '.html', '.css', '.xml', '.yaml', '.yml'}
        return Path(file_path).suffix.lower() in text_extensions

    def _is_code_file(self, file_path: str) -> bool:
        """Check if file is a code file for relationship extraction."""
        code_extensions = {'.py', '.js', '.ts', '.java', '.cpp', '.c', '.h', '.go', '.rs', '.php'}
        return Path(file_path).suffix.lower() in code_extensions


class FileIndexer:
    """
    High-performance file system indexer with real-time monitoring.
    Implements inverted indexing and metadata extraction.
    """

    def __init__(
        self,
        db_manager: DatabaseManager | None = None,
        index_directories: bool = True,
        index_hidden: bool = False,
        excluded_extensions: set[str] | None = None,
        excluded_paths: set[str] | None = None,
    ):
        self.db = db_manager or DatabaseManager()
        self.index_directories = index_directories
        self.index_hidden = index_hidden
        self.excluded_extensions = excluded_extensions or {
            ".tmp",
            ".temp",
            ".log",
            ".cache",
            ".lock",
        }
        self.excluded_paths = excluded_paths or {
            ".git",
            ".svn",
            "node_modules",
            "__pycache__",
            ".DS_Store",
        }

        self.observer = Observer()
        self.is_monitoring = False
        self._stop_event = threading.Event()
        self.logger = logging.getLogger(__name__)

    def _should_index(self, path: str) -> bool:
        """Determine if a path should be indexed."""
        path_obj = Path(path)

        # Skip hidden files/directories if not indexing them
        if not self.index_hidden and path_obj.name.startswith("."):
            return False

        # Check excluded paths
        for excluded in self.excluded_paths:
            if excluded in path_obj.parts:
                return False

        # Check excluded extensions
        if path_obj.suffix.lower() in self.excluded_extensions:
            return False

        return True

    def _extract_keywords(self, file_path: str, file_name: str) -> list[str]:
        """Extract keywords from filename and path for inverted indexing."""
        keywords = set()

        # Split filename by common delimiters
        name_parts = file_name.replace(".", " ").replace("_", " ").replace("-", " ")
        for part in name_parts.split():
            if len(part) > 1:  # Skip single characters
                keywords.add(part.lower())

        # Add path components
        path_obj = Path(file_path)
        for part in path_obj.parts[:-1]:  # Exclude the filename itself
            clean_part = part.replace(".", " ").replace("_", " ").replace("-", " ")
            for word in clean_part.split():
                if len(word) > 1:
                    keywords.add(word.lower())

        # Add file extension without dot
        if path_obj.suffix:
            keywords.add(path_obj.suffix[1:].lower())

        # Add n-grams for better fuzzy matching
        name_lower = file_name.lower()
        for i in range(len(name_lower) - 2):
            keywords.add(name_lower[i : i + 3])

        return list(keywords)

    def _get_file_metadata(self, file_path: str) -> dict[str, any]:
        """Extract file metadata."""
        try:
            path_obj = Path(file_path)
            stat = path_obj.stat()

            return {
                "path": str(path_obj.absolute()),
                "name": path_obj.name,
                "size": stat.st_size if path_obj.is_file() else None,
                "created_time": stat.st_ctime,
                "modified_time": stat.st_mtime,
                "file_type": path_obj.suffix.lower() if path_obj.suffix else None,
                "is_directory": path_obj.is_dir(),
                "indexed_time": time.time(),
            }
        except OSError as e:
            print(f"Error getting metadata for {file_path}: {e}")
            return None

    def _index_single_path(self, path: str) -> None:
        """Index a single file or directory."""
        if not self._should_index(path):
            return

        metadata = self._get_file_metadata(path)
        if not metadata:
            return

        # Insert file into database
        file_id = self.db.insert_file(metadata)

        # Generate and insert keywords
        keywords = self._extract_keywords(path, metadata["name"])
        self.db.insert_keywords(file_id, keywords)

    def index_directory(
        self,
        directory: str,
        recursive: bool = True,
        progress_callback: Callable[[int, str], None] | None = None,
    ) -> None:
        """Index a directory and optionally its subdirectories."""
        directory_path = Path(directory)

        if not directory_path.exists():
            raise ValueError(f"Directory does not exist: {directory}")

        file_count = 0

        if recursive:
            iterator = directory_path.rglob("*")
        else:
            iterator = directory_path.iterdir()

        for path in iterator:
            if self._stop_event.is_set():
                break

            if self._should_index(str(path)):
                self._index_single_path(str(path))
                file_count += 1

                if progress_callback and file_count % 100 == 0:
                    progress_callback(file_count, str(path))

        if progress_callback:
            progress_callback(file_count, "Indexing complete")

    def start_monitoring(self, paths: list[str]) -> None:
        """Start real-time file system monitoring."""
        if self.is_monitoring:
            return

        self.logger.info(f"Starting real-time monitoring for paths: {paths}")

        # Clear stop event
        self._stop_event.clear()

        # Add paths to be monitored
        for path in paths:
            if Path(path).exists():
                self.observer.schedule(
                    IndexingHandler(self),
                    path,
                    recursive=True
                )
                self.logger.info(f"Added monitoring for: {path}")
            else:
                self.logger.warning(f"Path does not exist: {path}")

        # Start the observer
        try:
            self.observer.start()
            self.is_monitoring = True
            self.logger.info("File system monitoring started successfully")
        except Exception as e:
            self.logger.error(f"Failed to start monitoring: {e}")
            raise

        self.is_monitoring = True
        self._stop_event.clear()

        event_handler = IndexingHandler(self)

        for path in paths:
            if os.path.exists(path):
                self.observer.schedule(event_handler, path, recursive=True)

        self.observer.start()

    def stop_monitoring(self) -> None:
        """Stop file system monitoring."""
        if not self.is_monitoring:
            return

        self._stop_event.set()
        self.observer.stop()
        self.observer.join()
        self.is_monitoring = False

    def rebuild_index(
        self,
        paths: list[str],
        progress_callback: Callable[[int, str], None] | None = None,
    ) -> None:
        """Rebuild the entire index from scratch."""
        # Clear existing index
        # Note: In a production system, you might want to be more careful about this
        if hasattr(self.db, "clear_all"):
            self.db.clear_all()

        total_files = 0
        for path in paths:
            if os.path.exists(path):
                try:
                    self.index_directory(
                        path, recursive=True, progress_callback=progress_callback
                    )
                    total_files += sum(
                        1 for _ in Path(path).rglob("*") if self._should_index(str(_))
                    )
                except Exception as e:
                    print(f"Error indexing {path}: {e}")

        if progress_callback:
            progress_callback(
                total_files, f"Rebuild complete: {total_files} items indexed"
            )

    def get_indexing_stats(self) -> dict[str, any]:
        """Get indexing statistics."""
        return {
            "is_monitoring": self.is_monitoring,
            "excluded_extensions": list(self.excluded_extensions),
            "excluded_paths": list(self.excluded_paths),
            "index_directories": self.index_directories,
            "index_hidden": self.index_hidden,
            **self.db.get_stats(),
        }
