"""
Command-line interface for the Unfold file locator.
"""

import os
import sys
import time
import threading
from pathlib import Path
from typing import Optional, List

import click
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, BarColumn, TextColumn, TimeRemainingColumn
from rich.panel import Panel
from rich.text import Text

from .core.database import DatabaseManager
from .core.indexer import FileIndexer
from .core.searcher import FileSearcher, SearchResult


console = Console()


def format_file_size(size: Optional[int]) -> str:
    """Format file size in human-readable format."""
    if size is None:
        return "N/A"
    
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size < 1024.0:
            return f"{size:.1f} {unit}"
        size /= 1024.0
    return f"{size:.1f} PB"


def format_time_ago(timestamp: Optional[float]) -> str:
    """Format timestamp as time ago."""
    if timestamp is None:
        return "Never"
    
    diff = time.time() - timestamp
    if diff < 60:
        return "Just now"
    elif diff < 3600:
        return f"{int(diff/60)} minutes ago"
    elif diff < 86400:
        return f"{int(diff/3600)} hours ago"
    else:
        return f"{int(diff/86400)} days ago"


def display_search_results(results: List[SearchResult], query: str) -> None:
    """Display search results in a formatted table."""
    if not results:
        console.print(f"[yellow]No results found for '[bold]{query}[/bold]'[/yellow]")
        return
    
    table = Table(title=f"Search Results for '{query}'")
    table.add_column("Score", style="cyan", width=8)
    table.add_column("Name", style="bold blue", min_width=20)
    table.add_column("Type", style="green", width=8)
    table.add_column("Size", style="yellow", width=10)
    table.add_column("Match", style="magenta", width=12)
    table.add_column("Path", style="dim")
    
    for result in results:
        file_type = "DIR" if result.is_directory else (result.file_type or "FILE")
        size = format_file_size(result.size)
        path_display = str(result.path)
        
        # Truncate long paths
        if len(path_display) > 60:
            path_display = "..." + path_display[-57:]
        
        table.add_row(
            f"{result.score:.1f}",
            result.name,
            file_type,
            size,
            result.match_type,
            path_display
        )
    
    console.print(table)
    console.print(f"\n[dim]Found {len(results)} results[/dim]")


def progress_callback(count: int, current_path: str) -> None:
    """Progress callback for indexing operations."""
    if count % 1000 == 0:
        console.print(f"[dim]Indexed {count} items... {current_path}[/dim]")


@click.group(invoke_without_command=True)
@click.option('--version', is_flag=True, help='Show version information')
@click.pass_context
def main(ctx: click.Context, version: bool) -> None:
    """Unfold - A superfast file/folder locator."""
    if version:
        from . import __version__
        console.print(f"Unfold version {__version__}")
        return
    
    if ctx.invoked_subcommand is None:
        # Interactive mode
        console.print(Panel.fit(
            "[bold blue]Unfold File Locator[/bold blue]\n"
            "Type your search query or use --help for commands",
            title="Welcome"
        ))
        interactive_search()


def interactive_search() -> None:
    """Interactive search mode."""
    searcher = FileSearcher()
    
    console.print("\n[dim]Type 'quit' or 'exit' to quit, 'help' for commands[/dim]")
    
    while True:
        try:
            query = input("\n🔍 Search: ").strip()
            
            if query.lower() in ['quit', 'exit', 'q']:
                break
            elif query.lower() == 'help':
                console.print("""
[bold]Available commands:[/bold]
- [cyan]recent[/cyan]: Show recently accessed files
- [cyan]frequent[/cyan]: Show frequently accessed files  
- [cyan]stats[/cyan]: Show indexing statistics
- [cyan]quit/exit[/cyan]: Exit the program
- Or just type to search for files/folders
                """)
                continue
            elif query.lower() == 'recent':
                results = searcher.get_recent_files()
                display_search_results(results, "Recent Files")
                continue
            elif query.lower() == 'frequent':
                results = searcher.get_frequent_files()
                display_search_results(results, "Frequent Files")
                continue
            elif query.lower() == 'stats':
                show_stats()
                continue
            elif not query:
                continue
            
            # Perform search
            results = searcher.search(query)
            display_search_results(results, query)
            
            # Update access stats if user selects a result
            if results:
                console.print("\n[dim]Press Enter to continue or type a number to open a file...[/dim]")
                selection = input().strip()
                if selection.isdigit():
                    idx = int(selection) - 1
                    if 0 <= idx < len(results):
                        result = results[idx]
                        searcher.update_access_stats(result.path)
                        console.print(f"[green]Opened: {result.path}[/green]")
                        # Here you could actually open the file with the system default app
                        # os.system(f"open '{result.path}'")  # macOS
                        # os.system(f"xdg-open '{result.path}'")  # Linux
                        # os.startfile(result.path)  # Windows
        
        except KeyboardInterrupt:
            break
        except EOFError:
            break
    
    console.print("\n[yellow]Goodbye![/yellow]")


@click.command()
@click.argument('query', required=True)
@click.option('--limit', '-l', default=20, help='Maximum number of results')
@click.option('--files-only', '-f', is_flag=True, help='Search files only')
@click.option('--dirs-only', '-d', is_flag=True, help='Search directories only')
@click.option('--type', '-t', multiple=True, help='Filter by file type (e.g., .py, .txt)')
def search(query: str, limit: int, files_only: bool, dirs_only: bool, type: tuple) -> None:
    """Search for files and folders."""
    searcher = FileSearcher(max_results=limit)
    
    file_types = list(type) if type else None
    results = searcher.search(
        query,
        file_types=file_types,
        files_only=files_only,
        directories_only=dirs_only
    )
    
    display_search_results(results, query)


@click.command()
@click.argument('paths', nargs=-1, required=True)
@click.option('--recursive/--no-recursive', default=True, help='Index recursively')
@click.option('--hidden/--no-hidden', default=False, help='Index hidden files')
@click.option('--rebuild', is_flag=True, help='Rebuild index from scratch')
def index(paths: tuple, recursive: bool, hidden: bool, rebuild: bool) -> None:
    """Index specified paths."""
    indexer = FileIndexer(index_hidden=hidden)
    
    console.print(f"[blue]Starting indexing of {len(paths)} path(s)...[/blue]")
    
    with Progress(
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        TimeRemainingColumn(),
        console=console
    ) as progress:
        
        if rebuild:
            task = progress.add_task("Rebuilding index...", total=None)
            indexer.rebuild_index(list(paths), progress_callback)
        else:
            for path in paths:
                if os.path.exists(path):
                    task = progress.add_task(f"Indexing {path}...", total=None)
                    indexer.index_directory(path, recursive=recursive, progress_callback=progress_callback)
                else:
                    console.print(f"[red]Path does not exist: {path}[/red]")
    
    stats = indexer.get_indexing_stats()
    console.print(f"\n[green]Indexing complete![/green]")
    console.print(f"Total files indexed: {stats['total_files']}")


@click.command()
@click.argument('paths', nargs=-1, required=True)
@click.option('--daemon', '-d', is_flag=True, help='Run as daemon process')
def monitor(paths: tuple, daemon: bool) -> None:
    """Start real-time file system monitoring."""
    indexer = FileIndexer()
    
    console.print(f"[blue]Starting monitoring of {len(paths)} path(s)...[/blue]")
    
    for path in paths:
        if not os.path.exists(path):
            console.print(f"[red]Path does not exist: {path}[/red]")
            return
    
    try:
        indexer.start_monitoring(list(paths))
        
        if daemon:
            console.print("[green]Monitoring started in daemon mode[/green]")
            # In a real implementation, you'd detach from the terminal here
            while True:
                time.sleep(60)
        else:
            console.print("[green]Monitoring started. Press Ctrl+C to stop.[/green]")
            while True:
                time.sleep(1)
                
    except KeyboardInterrupt:
        console.print("\n[yellow]Stopping monitoring...[/yellow]")
        indexer.stop_monitoring()
        console.print("[green]Monitoring stopped[/green]")


@click.command()
def stats() -> None:
    """Show indexing and search statistics."""
    show_stats()


def show_stats() -> None:
    """Display database and indexing statistics."""
    db = DatabaseManager()
    searcher = FileSearcher(db)
    indexer = FileIndexer(db)
    
    db_stats = db.get_stats()
    search_stats = searcher.get_search_stats()
    index_stats = indexer.get_indexing_stats()
    
    # Database stats
    db_table = Table(title="Database Statistics", show_header=False)
    db_table.add_column("Metric", style="cyan")
    db_table.add_column("Value", style="yellow")
    
    db_table.add_row("Total Files", str(db_stats['total_files']))
    db_table.add_row("Total Keywords", str(db_stats['total_keywords']))
    db_table.add_row("Cached Searches", str(db_stats['cached_searches']))
    
    # Search stats
    search_table = Table(title="Search Configuration", show_header=False)
    search_table.add_column("Setting", style="cyan")
    search_table.add_column("Value", style="yellow")
    
    search_table.add_row("Fuzzy Matching", "Enabled" if search_stats['fuzzy_enabled'] else "Disabled")
    search_table.add_row("Fuzzy Threshold", f"{search_stats['fuzzy_threshold']:.2f}")
    search_table.add_row("Max Results", str(search_stats['max_results']))
    search_table.add_row("Result Caching", "Enabled" if search_stats['cache_enabled'] else "Disabled")
    
    # Indexing stats
    index_table = Table(title="Indexing Configuration", show_header=False)
    index_table.add_column("Setting", style="cyan")
    index_table.add_column("Value", style="yellow")
    
    index_table.add_row("Monitoring", "Active" if index_stats['is_monitoring'] else "Inactive")
    index_table.add_row("Index Directories", "Yes" if index_stats['index_directories'] else "No")
    index_table.add_row("Index Hidden", "Yes" if index_stats['index_hidden'] else "No")
    index_table.add_row("Excluded Extensions", ", ".join(index_stats['excluded_extensions'][:5]))
    
    console.print(db_table)
    console.print(search_table)
    console.print(index_table)


@click.command()
@click.option('--cache-only', is_flag=True, help='Clear only search cache')
def clear(cache_only: bool) -> None:
    """Clear database and cache."""
    if cache_only:
        searcher = FileSearcher()
        searcher.clear_cache()
        console.print("[green]Search cache cleared[/green]")
    else:
        # In a real implementation, you'd want confirmation here
        console.print("[red]This would clear the entire database. Use --cache-only for now.[/red]")


# Add commands to the main group
main.add_command(search)
main.add_command(index)
main.add_command(monitor)
main.add_command(stats)
main.add_command(clear)


if __name__ == "__main__":
    main() 