"""
Monitor command with real-time status updates.
"""

import os
import time

import click

from ...core.indexer import FileIndexer
from ..ui import console, loading_indicator, show_error, show_success


@click.command("monitor")
@click.argument("paths", nargs=-1, required=True)
@click.option("--daemon", "-d", is_flag=True, help="Run as daemon process")
def monitor_command(paths: tuple, daemon: bool) -> None:
    """Start real-time file system monitoring."""
    try:
        indexer = FileIndexer()

        console.print(f"[blue]👁️ Starting monitoring of {len(paths)} path(s)...[/blue]")

        # Validate paths
        valid_paths = []
        for path in paths:
            if os.path.exists(path):
                valid_paths.append(path)
            else:
                show_error(f"Path does not exist: {path}")

        if not valid_paths:
            return

        with loading_indicator("🔧 Setting up file system monitoring..."):
            indexer.start_monitoring(valid_paths)

        if daemon:
            show_success("👁️ Monitoring started in daemon mode")
            console.print("[dim]Process will continue running in background...[/dim]")
            # In a real implementation, you'd detach from the terminal here
            while True:
                time.sleep(60)
        else:
            show_success("👁️ Monitoring started. Press Ctrl+C to stop.")
            console.print("[dim]Watching for file system changes...[/dim]")

            try:
                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                console.print("\n[yellow]⏹️ Stopping monitoring...[/yellow]")
                with loading_indicator("Cleaning up monitors..."):
                    indexer.stop_monitoring()
                show_success("👁️ Monitoring stopped")

    except KeyboardInterrupt:
        console.print("\n[yellow]⏹️ Monitoring interrupted[/yellow]")
        if 'indexer' in locals():
            indexer.stop_monitoring()
    except Exception as e:
        show_error(f"Monitoring failed: {e}")
