"""
Stats command with rich table displays.
"""

import click
from rich.table import Table

from ...core.database import DatabaseManager
from ...core.indexer import FileIndexer
from ...core.searcher import FileSearcher
from ..ui import console, loading_indicator, show_error


@click.command("stats")
def stats_command() -> None:
    """Show indexing and search statistics."""
    try:
        with loading_indicator("📊 Gathering statistics..."):
            db = DatabaseManager()
            searcher = FileSearcher(db)
            indexer = FileIndexer(db)

            db_stats = db.get_stats()
            search_stats = searcher.get_search_stats()
            index_stats = indexer.get_indexing_stats()

        # Database stats
        db_table = Table(title="📊 Database Statistics", show_header=False)
        db_table.add_column("Metric", style="cyan")
        db_table.add_column("Value", style="yellow")

        db_table.add_row("Total Files", str(db_stats["total_files"]))
        db_table.add_row("Total Keywords", str(db_stats["total_keywords"]))
        db_table.add_row("Cached Searches", str(db_stats["cached_searches"]))

        # Search stats
        search_table = Table(title="🔍 Search Configuration", show_header=False)
        search_table.add_column("Setting", style="cyan")
        search_table.add_column("Value", style="yellow")

        search_table.add_row("Fuzzy Matching", "Enabled" if search_stats["fuzzy_enabled"] else "Disabled")
        search_table.add_row("Fuzzy Threshold", f"{search_stats['fuzzy_threshold']:.2f}")
        search_table.add_row("Max Results", str(search_stats["max_results"]))
        search_table.add_row("Result Caching", "Enabled" if search_stats["cache_enabled"] else "Disabled")

        # Indexing stats
        index_table = Table(title="📁 Indexing Configuration", show_header=False)
        index_table.add_column("Setting", style="cyan")
        index_table.add_column("Value", style="yellow")

        index_table.add_row("Monitoring", "Active" if index_stats["is_monitoring"] else "Inactive")
        index_table.add_row("Index Directories", "Yes" if index_stats["index_directories"] else "No")
        index_table.add_row("Index Hidden", "Yes" if index_stats["index_hidden"] else "No")
        index_table.add_row("Excluded Extensions", ", ".join(index_stats["excluded_extensions"][:5]))

        console.print(db_table)
        console.print(search_table)
        console.print(index_table)

    except Exception as e:
        show_error(f"Failed to gather statistics: {e}")
