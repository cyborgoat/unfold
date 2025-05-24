"""
File system indexer with real-time monitoring and metadata extraction.
"""

import os
import time
import threading
from pathlib import Path
from typing import List, Dict, Set, Optional, Callable
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileSystemEvent

from .database import DatabaseManager


class IndexingHandler(FileSystemEventHandler):
    """File system event handler for real-time indexing."""
    
    def __init__(self, indexer: 'FileIndexer'):
        self.indexer = indexer
    
    def on_created(self, event: FileSystemEvent) -> None:
        """Handle file/directory creation."""
        if not event.is_directory or self.indexer.index_directories:
            self.indexer._index_single_path(event.src_path)
    
    def on_modified(self, event: FileSystemEvent) -> None:
        """Handle file/directory modification."""
        if not event.is_directory or self.indexer.index_directories:
            self.indexer._index_single_path(event.src_path)
    
    def on_moved(self, event: FileSystemEvent) -> None:
        """Handle file/directory move."""
        # Remove old path and index new path
        self.indexer.db.remove_file(event.src_path)
        if not event.is_directory or self.indexer.index_directories:
            self.indexer._index_single_path(event.dest_path)
    
    def on_deleted(self, event: FileSystemEvent) -> None:
        """Handle file/directory deletion."""
        self.indexer.db.remove_file(event.src_path)


class FileIndexer:
    """
    High-performance file system indexer with real-time monitoring.
    Implements inverted indexing and metadata extraction.
    """
    
    def __init__(
        self,
        db_manager: Optional[DatabaseManager] = None,
        index_directories: bool = True,
        index_hidden: bool = False,
        excluded_extensions: Optional[Set[str]] = None,
        excluded_paths: Optional[Set[str]] = None
    ):
        self.db = db_manager or DatabaseManager()
        self.index_directories = index_directories
        self.index_hidden = index_hidden
        self.excluded_extensions = excluded_extensions or {
            '.tmp', '.temp', '.log', '.cache', '.lock'
        }
        self.excluded_paths = excluded_paths or {
            '.git', '.svn', 'node_modules', '__pycache__', '.DS_Store'
        }
        
        self.observer = Observer()
        self.is_monitoring = False
        self._stop_event = threading.Event()
    
    def _should_index(self, path: str) -> bool:
        """Determine if a path should be indexed."""
        path_obj = Path(path)
        
        # Skip hidden files/directories if not indexing them
        if not self.index_hidden and path_obj.name.startswith('.'):
            return False
        
        # Check excluded paths
        for excluded in self.excluded_paths:
            if excluded in path_obj.parts:
                return False
        
        # Check excluded extensions
        if path_obj.suffix.lower() in self.excluded_extensions:
            return False
        
        return True
    
    def _extract_keywords(self, file_path: str, file_name: str) -> List[str]:
        """Extract keywords from filename and path for inverted indexing."""
        keywords = set()
        
        # Split filename by common delimiters
        name_parts = file_name.replace('.', ' ').replace('_', ' ').replace('-', ' ')
        for part in name_parts.split():
            if len(part) > 1:  # Skip single characters
                keywords.add(part.lower())
        
        # Add path components
        path_obj = Path(file_path)
        for part in path_obj.parts[:-1]:  # Exclude the filename itself
            clean_part = part.replace('.', ' ').replace('_', ' ').replace('-', ' ')
            for word in clean_part.split():
                if len(word) > 1:
                    keywords.add(word.lower())
        
        # Add file extension without dot
        if path_obj.suffix:
            keywords.add(path_obj.suffix[1:].lower())
        
        # Add n-grams for better fuzzy matching
        name_lower = file_name.lower()
        for i in range(len(name_lower) - 2):
            keywords.add(name_lower[i:i+3])
        
        return list(keywords)
    
    def _get_file_metadata(self, file_path: str) -> Dict[str, any]:
        """Extract file metadata."""
        try:
            path_obj = Path(file_path)
            stat = path_obj.stat()
            
            return {
                'path': str(path_obj.absolute()),
                'name': path_obj.name,
                'size': stat.st_size if path_obj.is_file() else None,
                'created_time': stat.st_ctime,
                'modified_time': stat.st_mtime,
                'file_type': path_obj.suffix.lower() if path_obj.suffix else None,
                'is_directory': path_obj.is_dir(),
                'indexed_time': time.time()
            }
        except (OSError, IOError) as e:
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
        keywords = self._extract_keywords(path, metadata['name'])
        self.db.insert_keywords(file_id, keywords)
    
    def index_directory(
        self,
        directory: str,
        recursive: bool = True,
        progress_callback: Optional[Callable[[int, str], None]] = None
    ) -> None:
        """Index a directory and optionally its subdirectories."""
        directory_path = Path(directory)
        
        if not directory_path.exists():
            raise ValueError(f"Directory does not exist: {directory}")
        
        file_count = 0
        
        if recursive:
            iterator = directory_path.rglob('*')
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
    
    def start_monitoring(self, paths: List[str]) -> None:
        """Start real-time file system monitoring."""
        if self.is_monitoring:
            return
        
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
        paths: List[str],
        progress_callback: Optional[Callable[[int, str], None]] = None
    ) -> None:
        """Rebuild the entire index from scratch."""
        # Clear existing index
        # Note: In a production system, you might want to be more careful about this
        if hasattr(self.db, 'clear_all'):
            self.db.clear_all()
        
        total_files = 0
        for path in paths:
            if os.path.exists(path):
                try:
                    self.index_directory(
                        path,
                        recursive=True,
                        progress_callback=progress_callback
                    )
                    total_files += sum(1 for _ in Path(path).rglob('*') if self._should_index(str(_)))
                except Exception as e:
                    print(f"Error indexing {path}: {e}")
        
        if progress_callback:
            progress_callback(total_files, f"Rebuild complete: {total_files} items indexed")
    
    def get_indexing_stats(self) -> Dict[str, any]:
        """Get indexing statistics."""
        return {
            'is_monitoring': self.is_monitoring,
            'excluded_extensions': list(self.excluded_extensions),
            'excluded_paths': list(self.excluded_paths),
            'index_directories': self.index_directories,
            'index_hidden': self.index_hidden,
            **self.db.get_stats()
        } 