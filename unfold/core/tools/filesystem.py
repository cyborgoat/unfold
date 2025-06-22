"""
Filesystem operations tools for MCP integration.
"""

import os
import shutil
import time
from datetime import datetime
from pathlib import Path
from typing import Any


class FilesystemTools:
    """Tools for filesystem operations."""

    def __init__(self, working_directory: str = None, file_indexer=None, db_manager=None):
        """Initialize filesystem tools."""
        self.working_directory = working_directory or os.getcwd()
        self.file_indexer = file_indexer
        self.db_manager = db_manager

    async def list_directory(self, path: str = None, show_hidden: bool = False, recursive: bool = False) -> dict[str, Any]:
        """List directory contents with detailed information."""
        try:
            target_path = Path(path) if path else Path(self.working_directory)

            if not target_path.exists():
                return {"success": False, "error": f"Path does not exist: {target_path}"}

            if not target_path.is_dir():
                return {"success": False, "error": f"Path is not a directory: {target_path}"}

            items = []

            if recursive:
                iterator = target_path.rglob("*")
            else:
                iterator = target_path.iterdir()

            for item in iterator:
                # Skip hidden files unless requested
                if not show_hidden and item.name.startswith('.'):
                    continue

                try:
                    stat = item.stat()
                    items.append({
                        "name": item.name,
                        "path": str(item.absolute()),
                        "type": "directory" if item.is_dir() else "file",
                        "size": stat.st_size if item.is_file() else None,
                        "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                        "permissions": oct(stat.st_mode)[-3:],
                        "extension": item.suffix if item.is_file() else None
                    })
                except (OSError, PermissionError):
                    continue

            return {
                "success": True,
                "path": str(target_path.absolute()),
                "items": sorted(items, key=lambda x: (x["type"] == "file", x["name"].lower())),
                "total_items": len(items)
            }

        except Exception as e:
            return {"success": False, "error": f"Failed to list directory: {str(e)}"}

    async def read_file(self, file_path: str, encoding: str = "utf-8", max_size: int = 1024*1024) -> dict[str, Any]:
        """Read file content with safety checks."""
        try:
            path = Path(file_path)

            if not path.exists():
                return {"success": False, "error": f"File does not exist: {file_path}"}

            if not path.is_file():
                return {"success": False, "error": f"Path is not a file: {file_path}"}

            # Check file size
            size = path.stat().st_size
            if size > max_size:
                return {
                    "success": False,
                    "error": f"File too large: {size} bytes (max: {max_size})"
                }

            # Try to read file
            try:
                with open(path, encoding=encoding) as f:
                    content = f.read()
            except UnicodeDecodeError:
                # Try binary mode for non-text files
                with open(path, 'rb') as f:
                    content = f.read()
                    content = f"<Binary file: {len(content)} bytes>"

            return {
                "success": True,
                "file_path": str(path.absolute()),
                "content": content,
                "size": size,
                "encoding": encoding,
                "lines": len(content.splitlines()) if isinstance(content, str) else None
            }

        except Exception as e:
            return {"success": False, "error": f"Failed to read file: {str(e)}"}

    async def write_file(self, file_path: str, content: str, encoding: str = "utf-8", backup: bool = True) -> dict[str, Any]:
        """Write content to file with optional backup."""
        try:
            path = Path(file_path)

            # Create backup if file exists and backup is requested
            backup_path = None
            if backup and path.exists():
                backup_path = path.with_suffix(path.suffix + f".backup.{int(time.time())}")
                shutil.copy2(path, backup_path)

            # Ensure parent directory exists
            path.parent.mkdir(parents=True, exist_ok=True)

            # Write file
            with open(path, 'w', encoding=encoding) as f:
                f.write(content)

            # Update index if indexer is available
            if self.file_indexer:
                self.file_indexer._index_single_path(str(path))

            return {
                "success": True,
                "file_path": str(path.absolute()),
                "size": len(content.encode(encoding)),
                "backup_path": str(backup_path) if backup_path else None,
                "lines_written": len(content.splitlines())
            }

        except Exception as e:
            return {"success": False, "error": f"Failed to write file: {str(e)}"}

    async def delete_file(self, file_path: str, force: bool = False) -> dict[str, Any]:
        """Delete file or directory with safety checks."""
        try:
            path = Path(file_path)

            if not path.exists():
                return {"success": False, "error": f"Path does not exist: {file_path}"}

            # Safety check for important directories
            important_dirs = {'.git', 'node_modules', 'venv', '.env'}
            if not force and path.name in important_dirs:
                return {
                    "success": False,
                    "error": f"Refusing to delete important directory: {path.name}. Use force=True to override."
                }

            # Delete
            if path.is_file():
                path.unlink()
                deleted_type = "file"
            else:
                shutil.rmtree(path)
                deleted_type = "directory"

            # Remove from index if available
            if self.db_manager:
                self.db_manager.remove_file(str(path))

            return {
                "success": True,
                "deleted_path": str(path.absolute()),
                "type": deleted_type
            }

        except Exception as e:
            return {"success": False, "error": f"Failed to delete: {str(e)}"}

    async def create_directory(self, dir_path: str, parents: bool = True) -> dict[str, Any]:
        """Create directory with optional parent creation."""
        try:
            path = Path(dir_path)

            if path.exists():
                return {"success": False, "error": f"Directory already exists: {dir_path}"}

            path.mkdir(parents=parents, exist_ok=False)

            # Index new directory if indexer is available
            if self.file_indexer:
                self.file_indexer._index_single_path(str(path))

            return {
                "success": True,
                "directory_path": str(path.absolute()),
                "parents_created": parents
            }

        except Exception as e:
            return {"success": False, "error": f"Failed to create directory: {str(e)}"}

    async def move_file(self, src_path: str, dest_path: str, overwrite: bool = False) -> dict[str, Any]:
        """Move/rename file or directory."""
        try:
            src = Path(src_path)
            dest = Path(dest_path)

            if not src.exists():
                return {"success": False, "error": f"Source does not exist: {src_path}"}

            if dest.exists() and not overwrite:
                return {"success": False, "error": f"Destination exists: {dest_path}. Use overwrite=True to replace."}

            # Perform move
            shutil.move(str(src), str(dest))

            # Update index if available
            if self.db_manager:
                self.db_manager.remove_file(str(src))
            if self.file_indexer:
                self.file_indexer._index_single_path(str(dest))

            return {
                "success": True,
                "source_path": str(src.absolute()),
                "destination_path": str(dest.absolute()),
                "operation": "move"
            }

        except Exception as e:
            return {"success": False, "error": f"Failed to move file: {str(e)}"}

    async def copy_file(self, src_path: str, dest_path: str, overwrite: bool = False) -> dict[str, Any]:
        """Copy file or directory."""
        try:
            src = Path(src_path)
            dest = Path(dest_path)

            if not src.exists():
                return {"success": False, "error": f"Source does not exist: {src_path}"}

            if dest.exists() and not overwrite:
                return {"success": False, "error": f"Destination exists: {dest_path}. Use overwrite=True to replace."}

            # Perform copy
            if src.is_file():
                shutil.copy2(str(src), str(dest))
            else:
                shutil.copytree(str(src), str(dest), dirs_exist_ok=overwrite)

            # Update index if available
            if self.file_indexer:
                self.file_indexer._index_single_path(str(dest))

            return {
                "success": True,
                "source_path": str(src.absolute()),
                "destination_path": str(dest.absolute()),
                "operation": "copy"
            }

        except Exception as e:
            return {"success": False, "error": f"Failed to copy file: {str(e)}"} 