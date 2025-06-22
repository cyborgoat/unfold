"""
Search command with rich UI components.
"""


import click

from ...core.searcher import FileSearcher
from ..ui import SearchResultsDisplay, loading_indicator, show_error


@click.command("search")
@click.argument("query", required=True)
@click.option("--limit", "-l", default=20, help="Maximum number of results")
@click.option("--files-only", "-f", is_flag=True, help="Search files only")
@click.option("--dirs-only", "-d", is_flag=True, help="Search directories only")
@click.option("--type", "-t", multiple=True, help="Filter by file type (e.g., .py, .txt)")
def search_command(query: str, limit: int, files_only: bool, dirs_only: bool, type: tuple) -> None:  # noqa: A002
    """Search for files and folders."""
    try:
        with loading_indicator(f"🔍 Searching for '{query}'..."):
            searcher = FileSearcher(max_results=limit)

            file_types = list(type) if type else None
            results = searcher.search(
                query,
                file_types=file_types,
                files_only=files_only,
                directories_only=dirs_only
            )

            # Convert SearchResult objects to dictionaries for display
            result_dicts = []
            for result in results:
                result_dicts.append({
                    "score": result.score,
                    "name": result.name,
                    "type": "DIR" if result.is_directory else (result.file_type or "FILE"),
                    "size": format_file_size(result.size),
                    "path": str(result.path)
                })

        SearchResultsDisplay.show_results(result_dicts, query, "Search")

    except Exception as e:
        show_error(f"Search failed: {e}")


def format_file_size(size: int) -> str:
    """Format file size in human-readable format."""
    if size is None:
        return "N/A"

    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if size < 1024.0:
            return f"{size:.1f} {unit}"
        size /= 1024.0
    return f"{size:.1f} PB"
