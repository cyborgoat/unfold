"""
CLI utility functions for shared functionality.
"""

from pathlib import Path

from ..core.mcp_service import UnfoldMCPService


def load_unfold_ignore_patterns(directory: str) -> set[str]:
    """Load ignore patterns from .unfoldignore file."""
    ignore_patterns = set()
    unfoldignore_path = Path(directory) / ".unfoldignore"

    if unfoldignore_path.exists():
        try:
            with open(unfoldignore_path, encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#'):
                        ignore_patterns.add(line)
        except Exception:
            pass  # Continue without ignore file if it can't be read

    return ignore_patterns


def should_ignore_file(file_path: Path, base_dir: Path, ignore_patterns: set[str]) -> bool:
    """Check if a file should be ignored based on .unfoldignore patterns."""
    try:
        # Get relative path from base directory
        rel_path = file_path.relative_to(base_dir)
        rel_path_str = str(rel_path)

        # Check against each ignore pattern
        for pattern in ignore_patterns:
            # Handle directory patterns (ending with /)
            if pattern.endswith('/'):
                if any(part == pattern[:-1] for part in rel_path.parts):
                    return True
            # Handle file extension patterns
            elif pattern.startswith('*.'):
                if file_path.name.endswith(pattern[1:]):
                    return True
            # Handle exact matches
            elif pattern == file_path.name or pattern == rel_path_str:
                return True
            # Handle path patterns
            elif pattern in rel_path_str:
                return True

        return False
    except ValueError:
        # File is not relative to base_dir
        return False


async def quick_index_directory(mcp_service: UnfoldMCPService, directory: str) -> None:
    """Quick index of files in the specified working directory only (not recursive)."""
    try:
        base_dir = Path(directory)

        # Load ignore patterns from .unfoldignore
        ignore_patterns = load_unfold_ignore_patterns(directory)

        indexed_count = 0
        max_files = 30  # Limit to 30 files for quick startup

        # Priority file extensions for understanding the project
        priority_extensions = {'.py', '.js', '.ts', '.md', '.json', '.yaml', '.yml', '.toml', '.txt'}

        # Only look at files in the current directory and immediate subdirectories (max depth 2)
        def get_files_limited_depth(base_path: Path, max_depth: int = 2):
            """Get files with limited depth to avoid deep recursion."""
            for item in base_path.iterdir():
                if item.is_file():
                    yield item
                elif item.is_dir() and max_depth > 0 and not item.name.startswith('.'):
                    # Only recurse one level down, and skip hidden directories
                    try:
                        yield from get_files_limited_depth(item, max_depth - 1)
                    except (PermissionError, OSError):
                        continue  # Skip directories we can't access

        for file_path in get_files_limited_depth(base_dir):
            if indexed_count >= max_files:
                break

            # Check if file should be ignored
            if should_ignore_file(file_path, base_dir, ignore_patterns):
                continue

            # Skip hidden files and large files
            if file_path.name.startswith('.') or file_path.stat().st_size > 256*1024:  # 256KB limit
                continue

            # Only index priority file types
            if file_path.suffix.lower() not in priority_extensions:
                continue

            try:
                with open(file_path, encoding='utf-8', errors='ignore') as f:
                    content = f.read()

                # Index in knowledge graph only (faster than vector DB)
                if mcp_service.graph_service:
                    mcp_service.graph_service.index_file(str(file_path), content)

                indexed_count += 1

            except Exception:
                continue  # Skip files that can't be read

        # Save graph after indexing
        if mcp_service.graph_service and hasattr(mcp_service.graph_service, '_save_graph'):
            mcp_service.graph_service._save_graph()

    except Exception as e:
        raise Exception(f"Failed to quick index directory: {e}") from e


def format_file_size(size: int) -> str:
    """Format file size in human-readable format."""
    if size is None:
        return "N/A"

    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size < 1024.0:
            return f"{size:.1f} {unit}"
        size /= 1024.0
    return f"{size:.1f} PB"


def format_time_ago(timestamp: float) -> str:
    """Format timestamp as time ago."""
    if timestamp is None:
        return "Never"

    import time
    diff = time.time() - timestamp
    if diff < 60:
        return "Just now"
    elif diff < 3600:
        return f"{int(diff/60)} minutes ago"
    elif diff < 86400:
        return f"{int(diff/3600)} hours ago"
    else:
        return f"{int(diff/86400)} days ago"
