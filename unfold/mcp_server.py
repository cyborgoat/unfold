#!/usr/bin/env python3
"""
Standalone MCP Server for Unfold Filesystem Agent.

This server can be used by external applications for autocompletion,
code analysis, and file management capabilities.

Usage:
    python -m unfold.mcp_server [working_directory] [options]
    
Example:
    python -m unfold.mcp_server ~/project --config config.yaml --auto-index
"""

import argparse
import asyncio
import logging
import os
import sys
from pathlib import Path

# Add the parent directory to the path so we can import unfold modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from unfold.core.mcp_service import UnfoldMCPService
from unfold.utils.config import ConfigManager


def setup_logging(log_level: str = "INFO") -> None:
    """Setup logging configuration."""
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler('unfold_mcp_server.log')
        ]
    )


async def auto_index_directory(mcp_service: UnfoldMCPService, directory: str) -> None:
    """Auto-index the working directory on startup."""
    logger = logging.getLogger(__name__)
    logger.info(f"Starting auto-indexing of directory: {directory}")

    try:
        # Index the directory
        result = await mcp_service.tools.index_directory(
            directory=directory,
            recursive=True,
            force_rebuild=True
        )

        if result.get("success"):
            logger.info(f"Auto-indexing completed: {result.get('files_indexed', 0)} files indexed")
        else:
            logger.warning(f"Auto-indexing failed: {result.get('error', 'Unknown error')}")

    except Exception as e:
        logger.error(f"Auto-indexing error: {e}")


async def main():
    """Main entry point for the standalone MCP server."""
    parser = argparse.ArgumentParser(
        description="Unfold Standalone MCP Server for Filesystem Operations",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s ~/project                    # Start server for ~/project directory
  %(prog)s . --config unfold.yaml      # Use custom config file
  %(prog)s ~/code --auto-index          # Auto-index on startup
  %(prog)s --host 0.0.0.0 --port 8080   # Custom host and port
        """
    )

    parser.add_argument(
        "working_directory",
        nargs="?",
        default=os.getcwd(),
        help="Working directory to serve (default: current directory)"
    )

    parser.add_argument(
        "--config", "-c",
        help="Path to configuration file"
    )

    parser.add_argument(
        "--host",
        default="localhost",
        help="Host to bind the server to (default: localhost)"
    )

    parser.add_argument(
        "--port", "-p",
        type=int,
        default=8000,
        help="Port to bind the server to (default: 8000)"
    )

    parser.add_argument(
        "--log-level", "-l",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default="INFO",
        help="Logging level (default: INFO)"
    )

    parser.add_argument(
        "--auto-index",
        action="store_true",
        help="Automatically index the working directory on startup"
    )

    parser.add_argument(
        "--no-cache-clear",
        action="store_true",
        help="Don't clear cache on startup (useful for development)"
    )

    args = parser.parse_args()

    # Setup logging
    setup_logging(args.log_level)
    logger = logging.getLogger(__name__)

    # Resolve working directory
    working_dir = Path(args.working_directory).resolve()
    if not working_dir.exists():
        logger.error(f"Working directory does not exist: {working_dir}")
        sys.exit(1)

    if not working_dir.is_dir():
        logger.error(f"Working directory is not a directory: {working_dir}")
        sys.exit(1)

    logger.info("Starting Unfold MCP Server")
    logger.info(f"Working directory: {working_dir}")
    logger.info(f"Server address: {args.host}:{args.port}")

    try:
        # Initialize configuration
        config_manager = None
        if args.config:
            config_path = Path(args.config)
            if config_path.exists():
                config_manager = ConfigManager(config_path)
                logger.info(f"Loaded configuration from: {config_path}")
            else:
                logger.warning(f"Configuration file not found: {config_path}")
                config_manager = ConfigManager()
        else:
            config_manager = ConfigManager()

        # Initialize MCP service
        mcp_service = UnfoldMCPService(
            config_manager=config_manager,
            working_directory=str(working_dir)
        )

        # Clear cache unless disabled
        if not args.no_cache_clear:
            logger.info("Clearing cache on startup...")
            await mcp_service.tools.clear_cache("all")

        # Auto-index if requested
        if args.auto_index:
            await auto_index_directory(mcp_service, str(working_dir))

        # Get available tools for logging
        tools = mcp_service.get_available_tools()
        logger.info(f"Available tools: {len(tools)}")
        for tool in tools[:5]:  # Log first 5 tools
            logger.info(f"  - {tool['name']}: {tool['description']}")
        if len(tools) > 5:
            logger.info(f"  ... and {len(tools) - 5} more tools")

        # Start the server
        logger.info("Starting MCP server...")
        await mcp_service.start_server(host=args.host, port=args.port)

    except KeyboardInterrupt:
        logger.info("Server stopped by user")
    except Exception as e:
        logger.error(f"Server error: {e}")
        sys.exit(1)
    finally:
        # Cleanup
        try:
            if 'mcp_service' in locals():
                mcp_service.close()
                logger.info("Server cleanup completed")
        except Exception as e:
            logger.error(f"Cleanup error: {e}")


if __name__ == "__main__":
    asyncio.run(main())
