"""
Index command with rich progress indicators.
"""

import os

import click

from ...core.indexer import FileIndexer
from ..ui import IndexingProgress, console, loading_indicator, show_error, show_success


@click.command("index")
@click.argument("paths", nargs=-1, required=True)
@click.option("--recursive/--no-recursive", default=True, help="Index recursively")
@click.option("--hidden/--no-hidden", default=False, help="Index hidden files")
@click.option("--rebuild", is_flag=True, help="Rebuild index from scratch")
@click.option("--workdir", "-w", help="Working directory for AI indexing")
def index_command(paths: tuple, recursive: bool, hidden: bool, rebuild: bool, workdir: str) -> None:
    """Index specified paths."""
    try:
        indexer = FileIndexer(index_hidden=hidden)

        console.print(f"[blue]📁 Starting indexing of {len(paths)} path(s)...[/blue]")

        # Validate paths
        valid_paths = []
        for path in paths:
            if os.path.exists(path):
                valid_paths.append(path)
            else:
                show_error(f"Path does not exist: {path}")

        if not valid_paths:
            return

        # Start indexing with progress
        progress = IndexingProgress()
        progress.start(len(valid_paths))

        try:
            if rebuild:
                progress.update_path("Rebuilding index...", 0)

                def progress_callback(count: int, current_path: str):
                    if count % 100 == 0:
                        progress.update_path(current_path, count)

                indexer.rebuild_index(valid_paths, progress_callback)
                progress.advance(len(valid_paths))
            else:
                for _i, path in enumerate(valid_paths):
                    progress.update_path(path, 0)

                    def progress_callback(count: int, current_path: str):
                        if count % 100 == 0:
                            progress.update_path(current_path, count)

                    indexer.index_directory(path, recursive=recursive, progress_callback=progress_callback)
                    progress.advance(1)

        finally:
            progress.finish()

        # Show results
        with loading_indicator("📊 Gathering indexing statistics..."):
            stats = indexer.get_indexing_stats()

        show_success(f"Indexing complete! Total files indexed: {stats['total_files']}")

    except Exception as e:
        show_error(f"Indexing failed: {e}")
