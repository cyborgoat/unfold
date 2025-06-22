"""
Main CLI entry point with modular command structure.
"""

import click

from .commands import (
    ai_command,
    index_command,
    mcp_command,
    monitor_command,
    search_command,
    stats_command,
)
from .interactive import interactive_search
from .ui import console, show_error


@click.group(invoke_without_command=True)
@click.option('--version', is_flag=True, help='Show version information')
@click.option('--workdir', '-w', help='Set working directory for this session')
@click.pass_context
def main(ctx: click.Context, version: bool, workdir: str | None) -> None:
    """🚀 Unfold - A comprehensive filesystem agent with AI capabilities."""
    if version:
        from .. import __version__
        console.print(f"[bold cyan]Unfold[/bold cyan] version [yellow]{__version__}[/yellow]")
        return

    # Set working directory if provided
    if workdir:
        import os
        from pathlib import Path
        work_path = Path(workdir)
        if work_path.exists() and work_path.is_dir():
            os.chdir(work_path)
            console.print(f"📁 Working directory set to: [cyan]{work_path.absolute()}[/cyan]")
        else:
            show_error(f"Invalid working directory: {workdir}")
            return

    # Clear cache on startup (when user picks working directory)
    if workdir or ctx.invoked_subcommand is None:
        try:
            from .ui import loading_indicator
            with loading_indicator("🧹 Clearing cache for fresh start..."):
                _clear_startup_cache()
        except Exception as e:
            console.print(f"[yellow]Warning: Could not clear cache: {e}[/yellow]")

    if ctx.invoked_subcommand is None:
        # Interactive mode
        try:
            interactive_search()
        except Exception as e:
            show_error(f"Interactive mode failed: {e}")


def _clear_startup_cache() -> None:
    """Clear cache and knowledge data on startup."""
    import shutil
    from pathlib import Path

    # Clear knowledge directory
    knowledge_dir = Path.cwd() / "knowledge"
    if knowledge_dir.exists():
        shutil.rmtree(knowledge_dir)

    # Clear database cache
    try:
        from ..core.database import DatabaseManager
        db_manager = DatabaseManager()
        if hasattr(db_manager, 'clear_all'):
            db_manager.clear_all()
    except Exception:
        pass  # Silently fail if database not available


@click.command("clear")
@click.option('--cache-only', is_flag=True, help='Clear only search cache')
def clear_command(cache_only: bool) -> None:
    """Clear database and cache."""
    from ..core.database import DatabaseManager
    from ..core.searcher import FileSearcher
    from .ui import loading_indicator, show_success

    if cache_only:
        with loading_indicator("🧹 Clearing search cache..."):
            searcher = FileSearcher()
            searcher.clear_cache()
        show_success("🧹 Search cache cleared")
    else:
        console.print("[yellow]This command will clear the ENTIRE database and all indexed data.[/yellow]")
        # Prompt for confirmation; aborts if user says no.
        click.confirm("Are you absolutely sure you want to proceed? This action CANNOT be undone.", abort=True, err=True)

        try:
            with loading_indicator("🧹 Clearing entire database..."):
                db_manager = DatabaseManager()
                if hasattr(db_manager, 'clear_all'):
                    db_manager.clear_all()
                else:
                    show_error("The 'clear_all' method is not available in the DatabaseManager.")
                    return

            show_success("🧹 Entire database and associated index cleared successfully.")

        except ImportError:
            show_error("Could not import or instantiate DatabaseManager.")
        except Exception as e:
            show_error(f"An error occurred while clearing the database: {e}")


# Add all commands to the main group
main.add_command(search_command)
main.add_command(index_command)
main.add_command(monitor_command)
main.add_command(stats_command)
main.add_command(clear_command)
main.add_command(ai_command)
main.add_command(mcp_command)


if __name__ == "__main__":
    main(prog_name="unfold")
