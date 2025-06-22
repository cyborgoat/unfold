"""
MCP server command for the CLI.
"""

import asyncio
from pathlib import Path

import click

from ...core.mcp_service import UnfoldMCPService
from ...utils.config import ConfigManager
from ..ui import (
    console,
    loading_indicator,
    show_error,
    show_success,
    show_warning,
)


@click.command()
@click.option("--host", default="localhost", help="Host to bind the server to")
@click.option("--port", "-p", default=8000, type=int, help="Port to bind the server to")
@click.option("--config", "-c", help="Path to configuration file")
@click.option("--workdir", "-w", help="Working directory for the server")
@click.option("--auto-index", is_flag=True, help="Automatically index the working directory on startup")
@click.option("--no-cache-clear", is_flag=True, help="Don't clear cache on startup")
@click.option("--log-level", "-l",
              type=click.Choice(["DEBUG", "INFO", "WARNING", "ERROR"]),
              default="INFO",
              help="Logging level")
def mcp_command(
    host: str,
    port: int,
    config: str | None,
    workdir: str | None,
    auto_index: bool,
    no_cache_clear: bool,
    log_level: str
) -> None:
    """Start the FastMCP server for external applications."""
    asyncio.run(run_mcp_server(host, port, config, workdir, auto_index, no_cache_clear, log_level))


async def run_mcp_server(
    host: str,
    port: int,
    config: str | None,
    workdir: str | None,
    auto_index: bool,
    no_cache_clear: bool,
    log_level: str
) -> None:
    """Run the MCP server with rich UI feedback."""

    # Determine working directory
    working_dir = Path(workdir) if workdir else Path.cwd()
    if not working_dir.exists():
        show_error(f"Working directory does not exist: {working_dir}")
        return

    if not working_dir.is_dir():
        show_error(f"Working directory is not a directory: {working_dir}")
        return

    console.print("🚀 [bold blue]Starting Unfold MCP Server[/bold blue]")
    console.print(f"📁 Working Directory: [cyan]{working_dir.absolute()}[/cyan]")
    console.print(f"🌐 Server Address: [cyan]{host}:{port}[/cyan]")
    console.print(f"📊 Log Level: [cyan]{log_level}[/cyan]")

    try:
        # Initialize configuration
        config_manager = None
        if config:
            config_path = Path(config)
            if config_path.exists():
                with loading_indicator("Loading configuration..."):
                    config_manager = ConfigManager(config_path)
                show_success(f"Configuration loaded from: {config_path}")
            else:
                show_warning(f"Configuration file not found: {config_path}, using defaults")
                config_manager = ConfigManager()
        else:
            config_manager = ConfigManager()

        # Initialize MCP service
        with loading_indicator("Initializing MCP service..."):
            mcp_service = UnfoldMCPService(
                config_manager=config_manager,
                working_directory=str(working_dir)
            )

        # Clear cache unless disabled
        if not no_cache_clear:
            with loading_indicator("Clearing cache..."):
                await mcp_service.tools.clear_cache("all")
            show_success("Cache cleared")

        # Auto-index if requested
        if auto_index:
            with loading_indicator(f"Auto-indexing directory: {working_dir}"):
                result = await mcp_service.tools.index_directory(
                    directory=str(working_dir),
                    recursive=True,
                    force_rebuild=True
                )

            if result.get("success"):
                show_success(f"Auto-indexing completed: {result.get('files_indexed', 0)} files indexed")
            else:
                show_warning(f"Auto-indexing failed: {result.get('error', 'Unknown error')}")

        # Show available tools
        tools = mcp_service.get_available_tools()
        console.print(f"\n🔧 [bold green]Available Tools: {len(tools)}[/bold green]")

        # Group tools by category
        tool_categories = {}
        for tool in tools:
            category = tool.get('category', 'other')
            if category not in tool_categories:
                tool_categories[category] = []
            tool_categories[category].append(tool['name'])

        for category, tool_names in tool_categories.items():
            console.print(f"  📂 [bold]{category.title()}[/bold]: {', '.join(tool_names[:3])}")
            if len(tool_names) > 3:
                console.print(f"     ... and {len(tool_names) - 3} more")

        console.print("\n🎯 [bold green]Server ready![/bold green] Use Ctrl+C to stop.\n")

        # Start the server
        await mcp_service.start_server(host=host, port=port)

    except KeyboardInterrupt:
        console.print("\n🛑 [yellow]Server stopped by user[/yellow]")
    except Exception as e:
        show_error(f"Server error: {e}")
    finally:
        # Cleanup
        try:
            if 'mcp_service' in locals():
                with loading_indicator("Cleaning up..."):
                    mcp_service.close()
                show_success("Server cleanup completed")
        except Exception as e:
            show_error(f"Cleanup error: {e}")
