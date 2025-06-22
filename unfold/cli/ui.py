"""
Rich UI components for interactive CLI experience.
"""

import asyncio
import time
from contextlib import contextmanager
from typing import Any

from rich.console import Console
from rich.live import Live
from rich.panel import Panel
from rich.progress import (
    BarColumn,
    MofNCompleteColumn,
    Progress,
    SpinnerColumn,
    TextColumn,
    TimeElapsedColumn,
    TimeRemainingColumn,
)
from rich.status import Status
from rich.table import Table
from rich.text import Text

console = Console()


class StatusIndicator:
    """Rich status indicator with animations."""

    def __init__(self, message: str = "Working..."):
        self.message = message
        self.status = None

    def __enter__(self):
        self.status = Status(self.message, spinner="dots")
        self.status.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.status:
            self.status.stop()

    def update(self, message: str):
        """Update the status message."""
        if self.status:
            self.status.update(message)


class AIThinkingIndicator:
    """Animated thinking indicator for AI responses."""

    def __init__(self):
        self.is_running = False
        self.live = None

    async def start(self, message: str = "🤔 AI is thinking"):
        """Start the thinking animation."""
        self.is_running = True

        def create_thinking_display():
            dots = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"
            frame = int(time.time() * 10) % len(dots)
            spinner = dots[frame]

            return Panel(
                f"{spinner} {message}...",
                style="cyan",
                width=50
            )

        self.live = Live(create_thinking_display(), refresh_per_second=10)
        self.live.start()

        # Keep updating while running
        while self.is_running:
            self.live.update(create_thinking_display())
            await asyncio.sleep(0.1)

    def stop(self):
        """Stop the thinking animation."""
        self.is_running = False
        if self.live:
            self.live.stop()


class ServiceStatusDisplay:
    """Display service status with real-time updates."""

    @staticmethod
    def create_status_table(services: dict[str, dict[str, Any]]) -> Table:
        """Create a status table for services."""
        table = Table(title="🤖 AI Services Status", show_header=False, box=None)
        table.add_column("Service", style="cyan", width=20)
        table.add_column("Status", style="yellow", width=15)
        table.add_column("Details", style="dim", width=40)

        for service_name, service_info in services.items():
            status = service_info.get("status", "unknown")
            details = service_info.get("details", "")

            if status == "connected":
                status_icon = "✓ Connected"
                status_style = "green"
            elif status == "warning":
                status_icon = "⚠ Warning"
                status_style = "yellow"
            elif status == "error":
                status_icon = "✗ Error"
                status_style = "red"
            else:
                status_icon = "? Unknown"
                status_style = "dim"

            table.add_row(
                service_name,
                f"[{status_style}]{status_icon}[/{status_style}]",
                details
            )

        return table

    @staticmethod
    def show_warmup_progress(services: list[str]) -> None:
        """Show warmup progress for services."""
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            MofNCompleteColumn(),
            TimeElapsedColumn(),
            console=console,
            transient=True
        ) as progress:

            main_task = progress.add_task("🚀 Warming up services...", total=len(services))

            for _i, service in enumerate(services):
                service_task = progress.add_task(f"Loading {service}...", total=100)

                # Simulate service loading
                for _step in range(100):
                    progress.update(service_task, advance=1)
                    time.sleep(0.01)  # Simulate work

                progress.update(main_task, advance=1)
                progress.update(service_task, completed=100, description=f"✓ {service} ready")


class IndexingProgress:
    """Progress indicator for file indexing operations."""

    def __init__(self):
        self.progress = None
        self.main_task = None
        self.current_task = None

    def start(self, total_paths: int = None):
        """Start the indexing progress display."""
        self.progress = Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            MofNCompleteColumn(),
            TimeElapsedColumn(),
            TimeRemainingColumn(),
            console=console
        )

        self.progress.start()
        self.main_task = self.progress.add_task(
            "📁 Indexing files...",
            total=total_paths
        )

    def update_path(self, path: str, files_found: int = None):
        """Update current path being indexed."""
        if self.progress and self.main_task is not None:
            description = f"📁 Indexing: {path}"
            if files_found:
                description += f" ({files_found} files)"

            self.progress.update(self.main_task, description=description)

    def advance(self, amount: int = 1):
        """Advance the progress."""
        if self.progress and self.main_task is not None:
            self.progress.advance(self.main_task, amount)

    def finish(self):
        """Finish the indexing progress."""
        if self.progress:
            self.progress.stop()


class SearchResultsDisplay:
    """Display search results in rich tables."""

    @staticmethod
    def show_results(results: list[dict[str, Any]], query: str, result_type: str = "Search") -> None:
        """Display search results in a formatted table."""
        if not results:
            console.print(f"[yellow]No results found for '[bold]{query}[/bold]'[/yellow]")
            return

        table = Table(title=f"{result_type} Results for '{query}'")

        # Add columns based on result type
        if result_type == "Semantic Search":
            table.add_column("Score", style="cyan", width=8)
            table.add_column("File", style="bold blue", min_width=20)
            table.add_column("Content Preview", style="dim", max_width=50)
            table.add_column("Path", style="green")

            for result in results:
                score = result.get("score", 0)
                file_path = result.get("file_path", "")
                content = result.get("content", "")[:100] + "..." if len(result.get("content", "")) > 100 else result.get("content", "")

                table.add_row(
                    f"{score:.2f}",
                    file_path.split("/")[-1] if "/" in file_path else file_path,
                    content,
                    file_path
                )
        else:
            # Traditional search results
            table.add_column("Score", style="cyan", width=8)
            table.add_column("Name", style="bold blue", min_width=20)
            table.add_column("Type", style="green", width=8)
            table.add_column("Size", style="yellow", width=10)
            table.add_column("Path", style="dim")

            for result in results:
                table.add_row(
                    f"{result.get('score', 0):.1f}",
                    result.get("name", ""),
                    result.get("type", "FILE"),
                    result.get("size", "N/A"),
                    result.get("path", "")
                )

        console.print(table)
        console.print(f"\n[dim]Found {len(results)} results[/dim]")


class InteractivePrompt:
    """Interactive prompt with rich formatting."""

    @staticmethod
    def get_user_input(prompt: str = "🔍 Search", style: str = "bold cyan") -> str:
        """Get user input with rich formatting."""
        import sys
        
        try:
            # Check if input is being piped
            if not sys.stdin.isatty():
                # Input is piped, read from stdin
                line = sys.stdin.readline().strip()
                if line:
                    console.print(f"[{style}]{prompt}:[/{style}] {line}")
                    return line
                else:
                    # End of piped input - signal EOF
                    raise EOFError("End of piped input")
            else:
                # Interactive input
                return console.input(f"[{style}]{prompt}:[/{style}] ")
        except (EOFError, KeyboardInterrupt):
            # For piped input, we want to exit cleanly
            if not sys.stdin.isatty():
                raise
            return ""

    @staticmethod
    def show_welcome(title: str = "Unfold File Locator", subtitle: str = None) -> None:
        """Show welcome panel."""
        content = f"[bold blue]{title}[/bold blue]"
        if subtitle:
            content += f"\n{subtitle}"

        console.print(Panel.fit(content, title="Welcome"))

    @staticmethod
    def show_help(commands: dict[str, str]) -> None:
        """Show help information."""
        table = Table(title="Available Commands", show_header=False, box=None)
        table.add_column("Command", style="cyan")
        table.add_column("Description", style="white")

        for command, description in commands.items():
            table.add_row(f"[bold]{command}[/bold]", description)

        console.print(table)


class AIResponseStreamer:
    """Stream AI responses with rich formatting."""

    def __init__(self):
        self.response_text = Text()
        self.live = None

    async def start_streaming(self):
        """Start the streaming display."""
        self.live = Live(
            Panel(self.response_text, title="🤖 AI Response", border_style="blue"),
            refresh_per_second=10
        )
        self.live.start()

    async def add_chunk(self, chunk: str):
        """Add a chunk to the response."""
        self.response_text.append(chunk)
        if self.live:
            self.live.update(Panel(self.response_text, title="🤖 AI Response", border_style="blue"))

    def finish(self):
        """Finish streaming."""
        if self.live:
            self.live.stop()


@contextmanager
def loading_indicator(message: str):
    """Context manager for loading indicators."""
    with StatusIndicator(message) as indicator:
        yield indicator


def show_error(message: str, title: str = "Error") -> None:
    """Show error message in a panel."""
    console.print(Panel(
        f"[red]{message}[/red]",
        title=f"[red]{title}[/red]",
        border_style="red"
    ))


def show_success(message: str, title: str = "Success") -> None:
    """Show success message in a panel."""
    console.print(Panel(
        f"[green]{message}[/green]",
        title=f"[green]{title}[/green]",
        border_style="green"
    ))


def show_warning(message: str, title: str = "Warning") -> None:
    """Show warning message in a panel."""
    console.print(Panel(
        f"[yellow]{message}[/yellow]",
        title=f"[yellow]{title}[/yellow]",
        border_style="yellow"
    ))
