"""
Interactive mode with rich UI components.
"""


from ..core.searcher import FileSearcher, SearchResult
from .ui import (
    InteractivePrompt,
    SearchResultsDisplay,
    console,
    loading_indicator,
    show_error,
)
from .utils import format_file_size


def interactive_search() -> None:
    """Interactive search mode with rich UI."""

    InteractivePrompt.show_welcome(
        title="🔍 Unfold File Locator",
        subtitle="Type your search query or use commands"
    )

    searcher = FileSearcher()

    # Show available commands
    commands = {
        "recent": "Show recently accessed files",
        "frequent": "Show frequently accessed files",
        "stats": "Show indexing statistics",
        "help": "Show this help",
        "quit/exit": "Exit the program",
    }

    console.print("\n[dim]Available commands:[/dim]")
    InteractivePrompt.show_help(commands)

    while True:
        try:
            query = InteractivePrompt.get_user_input("🔍 Search")

            if query.lower() in ['quit', 'exit', 'q']:
                break
            elif query.lower() == 'help':
                InteractivePrompt.show_help(commands)
                continue
            elif query.lower() == 'recent':
                with loading_indicator("📅 Finding recent files..."):
                    results = searcher.get_recent_files()
                display_search_results(results, "Recent Files")
                continue
            elif query.lower() == 'frequent':
                with loading_indicator("⭐ Finding frequent files..."):
                    results = searcher.get_frequent_files()
                display_search_results(results, "Frequent Files")
                continue
            elif query.lower() == 'stats':
                show_interactive_stats()
                continue
            elif not query:
                continue

            # Perform search
            with loading_indicator(f"🔍 Searching for '{query}'..."):
                results = searcher.search(query)

            display_search_results(results, query)

            # Handle file selection
            if results:
                handle_file_selection(results, searcher)

        except KeyboardInterrupt:
            break
        except EOFError:
            break

    console.print("\n[yellow]👋 Goodbye![/yellow]")


def display_search_results(results: list[SearchResult], query: str) -> None:
    """Display search results using rich components."""
    if not results:
        console.print(f"[yellow]No results found for '[bold]{query}[/bold]'[/yellow]")
        return

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


def handle_file_selection(results: list[SearchResult], searcher: FileSearcher) -> None:
    """Handle file selection with rich prompts."""
    console.print("\n[dim]Press Enter to continue or type a number to open a file...[/dim]")

    try:
        selection = console.input("[cyan]Select file (number):[/cyan] ").strip()

        if selection.isdigit():
            idx = int(selection) - 1
            if 0 <= idx < len(results):
                result = results[idx]

                with loading_indicator(f"📂 Opening {result.name}..."):
                    searcher.update_access_stats(result.path)

                console.print(f"[green]✓ Opened: {result.path}[/green]")

                # Here you could actually open the file with the system default app
                # import subprocess
                # subprocess.run(["open", str(result.path)])  # macOS
                # subprocess.run(["xdg-open", str(result.path)])  # Linux
                # os.startfile(result.path)  # Windows
            else:
                show_error("Invalid selection number")
    except (ValueError, KeyboardInterrupt, EOFError):
        pass  # Continue without selection


def show_interactive_stats() -> None:
    """Show stats in interactive mode."""
    from click.testing import CliRunner

    from .commands.stats import stats_command

    try:
        # Use the stats command from the modular structure
        runner = CliRunner()
        runner.invoke(stats_command, catch_exceptions=False)
    except Exception as e:
        show_error(f"Failed to show stats: {e}")
