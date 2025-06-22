"""
FastMCP Service implementation for AI-enhanced file operations.
Wraps all file system tools and provides MCP protocol interface for LLM function calling.
"""

import json
import logging
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any

from fastmcp import FastMCP
from fastmcp.resources import Resource

from ..utils.config import ConfigManager
from .mcp_tools import UnfoldTools


class UnfoldMCPService:
    """
    FastMCP service for Unfold file management system.
    Provides AI assistant with access to all file system tools and capabilities.
    """

    def __init__(self, config_manager: ConfigManager | None = None, working_directory: str = None):
        self.config_manager = config_manager or ConfigManager()
        self.working_directory = working_directory
        self.logger = logging.getLogger(__name__)

        # Clear cache on startup
        self._clear_startup_cache()

        # Initialize comprehensive tools
        self.tools = UnfoldTools(
            config_manager=self.config_manager,
            working_directory=self.working_directory
        )

        # Initialize FastMCP
        self.mcp = FastMCP("Unfold Filesystem Agent")
        self._register_tools()
        self._register_resources()

    @property
    def llm_service(self):
        """Access to LLM service through tools."""
        return getattr(self.tools, 'llm_service', None)

    @property
    def vector_db(self):
        """Access to vector database through tools."""
        return getattr(self.tools, 'vector_db', None)

    @property
    def graph_service(self):
        """Access to graph service through tools."""
        return getattr(self.tools, 'graph_service', None)

    @property
    def db_manager(self):
        """Access to database manager through tools."""
        return getattr(self.tools, 'db_manager', None)

    @property
    def file_searcher(self):
        """Access to file searcher through tools."""
        return getattr(self.tools, 'file_searcher', None)

    def _clear_startup_cache(self):
        """Clear cache and knowledge data on startup."""
        try:
            if self.working_directory:
                knowledge_dir = Path(self.working_directory) / "knowledge"
                if knowledge_dir.exists():
                    import shutil
                    shutil.rmtree(knowledge_dir)
                    self.logger.info("Cleared knowledge directory on startup")
        except Exception as e:
            self.logger.warning(f"Failed to clear startup cache: {e}")

    def _register_tools(self):
        """Register all available tools with the MCP service."""

        # File search tools
        @self.mcp.tool()
        async def search_files(query: str, file_types: list[str] | None = None, max_results: int = 20) -> dict[str, Any]:
            """
            Search for files using traditional search algorithms.
            
            Args:
                query: Search query string
                file_types: Optional list of file extensions to filter by
                max_results: Maximum number of results to return
            
            Returns:
                Dictionary containing search results and metadata
            """
            return await self.tools.search_files(query, file_types, max_results)

        @self.mcp.tool()
        async def semantic_search(query: str, max_results: int = 10) -> dict[str, Any]:
            """
            Search for similar content using vector database.
            
            Args:
                query: Search query for semantic similarity
                max_results: Maximum number of results
            
            Returns:
                Dictionary containing similar documents
            """
            return await self.tools.semantic_search(query, max_results)

        @self.mcp.tool()
        async def get_file_relationships(file_path: str) -> dict[str, Any]:
            """
            Get file relationships from knowledge graph.
            
            Args:
                file_path: Path to the file to analyze relationships for
            
            Returns:
                Dictionary containing file relationships
            """
            return await self.tools.get_file_relationships(file_path)

        # File operations tools
        @self.mcp.tool()
        async def read_file(file_path: str, encoding: str = "utf-8", max_size: int = 1024*1024) -> dict[str, Any]:
            """
            Read and return file content.
            
            Args:
                file_path: Path to the file to read
                encoding: File encoding (default utf-8)
                max_size: Maximum file size to read (default 1MB)
            
            Returns:
                Dictionary containing file content and metadata
            """
            return await self.tools.read_file(file_path, encoding, max_size)

        @self.mcp.tool()
        async def write_file(file_path: str, content: str, encoding: str = "utf-8", backup: bool = True) -> dict[str, Any]:
            """
            Write content to file with optional backup.
            
            Args:
                file_path: Path to the file to write
                content: Content to write
                encoding: File encoding (default utf-8)
                backup: Whether to create backup of existing file
            
            Returns:
                Dictionary containing write operation results
            """
            return await self.tools.write_file(file_path, content, encoding, backup)

        @self.mcp.tool()
        async def delete_file(file_path: str, force: bool = False) -> dict[str, Any]:
            """
            Delete file or directory with safety checks.
            
            Args:
                file_path: Path to the file or directory to delete
                force: Whether to force deletion of important directories
            
            Returns:
                Dictionary containing deletion results
            """
            return await self.tools.delete_file(file_path, force)

        @self.mcp.tool()
        async def move_file(src_path: str, dest_path: str, overwrite: bool = False) -> dict[str, Any]:
            """
            Move/rename file or directory.
            
            Args:
                src_path: Source path
                dest_path: Destination path
                overwrite: Whether to overwrite existing destination
            
            Returns:
                Dictionary containing move operation results
            """
            return await self.tools.move_file(src_path, dest_path, overwrite)

        @self.mcp.tool()
        async def copy_file(src_path: str, dest_path: str, overwrite: bool = False) -> dict[str, Any]:
            """
            Copy file or directory.
            
            Args:
                src_path: Source path
                dest_path: Destination path
                overwrite: Whether to overwrite existing destination
            
            Returns:
                Dictionary containing copy operation results
            """
            return await self.tools.copy_file(src_path, dest_path, overwrite)

        @self.mcp.tool()
        async def list_directory(path: str = None, show_hidden: bool = False, recursive: bool = False) -> dict[str, Any]:
            """
            List directory contents with detailed information.
            
            Args:
                path: Directory path (defaults to working directory)
                show_hidden: Whether to show hidden files
                recursive: Whether to list recursively
            
            Returns:
                Dictionary containing directory listing
            """
            return await self.tools.list_directory(path, show_hidden, recursive)

        @self.mcp.tool()
        async def create_directory(dir_path: str, parents: bool = True) -> dict[str, Any]:
            """
            Create directory with optional parent creation.
            
            Args:
                dir_path: Directory path to create
                parents: Whether to create parent directories
            
            Returns:
                Dictionary containing creation results
            """
            return await self.tools.create_directory(dir_path, parents)

        @self.mcp.tool()
        async def index_directory(directory: str = None, recursive: bool = True, force_rebuild: bool = False) -> dict[str, Any]:
            """
            Index a directory for search capabilities.
            
            Args:
                directory: Path to directory to index (defaults to working directory)
                recursive: Whether to index subdirectories
                force_rebuild: Whether to rebuild existing index
            
            Returns:
                Dictionary containing indexing results
            """
            return await self.tools.index_directory(directory, recursive, force_rebuild)

        # AI Analysis tools
        @self.mcp.tool()
        async def analyze_file_content(file_path: str) -> dict[str, Any]:
            """
            Analyze file content using AI.
            
            Args:
                file_path: Path to the file to analyze
            
            Returns:
                Dictionary containing AI analysis results
            """
            return await self.tools.analyze_file_content(file_path)

        @self.mcp.tool()
        async def suggest_file_improvements(file_path: str) -> dict[str, Any]:
            """
            Suggest improvements for a file using AI.
            
            Args:
                file_path: Path to the file to analyze
            
            Returns:
                Dictionary containing improvement suggestions
            """
            return await self.tools.suggest_file_improvements(file_path)

        @self.mcp.tool()
        async def analyze_project_structure(directory: str = None) -> dict[str, Any]:
            """
            Analyze overall project structure and provide insights.
            
            Args:
                directory: Directory to analyze (defaults to working directory)
            
            Returns:
                Dictionary containing project analysis
            """
            return await self.tools.analyze_project_structure(directory)

        # System operations
        @self.mcp.tool()
        async def execute_command(command: str, working_dir: str = None, timeout: int = 30) -> dict[str, Any]:
            """
            Execute shell command with safety checks.
            
            Args:
                command: Command to execute
                working_dir: Working directory for command
                timeout: Command timeout in seconds
            
            Returns:
                Dictionary containing command execution results
            """
            return await self.tools.execute_command(command, working_dir, timeout)

        @self.mcp.tool()
        async def get_system_info() -> dict[str, Any]:
            """
            Get system and environment information.
            
            Returns:
                Dictionary containing system information
            """
            return await self.tools.get_system_info()

        @self.mcp.tool()
        async def clear_cache(cache_type: str = "all") -> dict[str, Any]:
            """
            Clear various caches and temporary data.
            
            Args:
                cache_type: Type of cache to clear ("all", "knowledge", "database", "vector", "graph")
            
            Returns:
                Dictionary containing cache clearing results
            """
            return await self.tools.clear_cache(cache_type)

        @self.mcp.tool()
        async def visualize_knowledge_graph() -> dict[str, Any]:
            """
            Display the knowledge graph in an interactive popup window.
            
            Returns:
                Dictionary containing visualization results
            """
            try:
                if not self.tools.graph_service:
                    return {"success": False, "error": "Graph service not available"}

                # Get the graph from the service
                graph = self.tools.graph_service.get_graph()

                if not graph or (hasattr(graph, 'number_of_nodes') and graph.number_of_nodes() == 0):
                    return {"success": False, "error": "Knowledge graph is empty. Please index some files first."}

                # Import visualization libraries
                try:
                    import tkinter as tk
                    from tkinter import ttk

                    import matplotlib.patches as patches
                    import matplotlib.pyplot as plt
                    import networkx as nx
                except ImportError as e:
                    return {"success": False, "error": f"Visualization libraries not available: {e}"}

                # Create the visualization
                plt.style.use('default')
                fig, ax = plt.subplots(1, 1, figsize=(14, 10))
                fig.suptitle('🔗 Unfold Knowledge Graph', fontsize=16, fontweight='bold')

                # Choose layout based on graph size
                num_nodes = graph.number_of_nodes()
                if num_nodes < 50:
                    pos = nx.spring_layout(graph, k=3, iterations=50, seed=42)
                elif num_nodes < 200:
                    pos = nx.spring_layout(graph, k=2, iterations=30, seed=42)
                else:
                    pos = nx.spring_layout(graph, k=1, iterations=20, seed=42)

                # Define node colors by type
                node_colors = []
                node_sizes = []
                for node, data in graph.nodes(data=True):
                    node_type = data.get('type', 'unknown')
                    if node_type == 'file':
                        node_colors.append('lightblue')
                        node_sizes.append(300)
                    elif node_type == 'directory':
                        node_colors.append('lightgreen')
                        node_sizes.append(500)
                    elif node_type == 'function':
                        node_colors.append('pink')
                        node_sizes.append(200)
                    elif node_type == 'class':
                        node_colors.append('orange')
                        node_sizes.append(400)
                    else:
                        node_colors.append('lightgray')
                        node_sizes.append(250)

                # Draw the graph
                nx.draw_networkx_nodes(graph, pos, node_color=node_colors, node_size=node_sizes, alpha=0.8, ax=ax)
                nx.draw_networkx_edges(graph, pos, alpha=0.5, edge_color='gray', width=1, ax=ax)

                # Add labels for important nodes
                important_nodes = {node: data.get('name', node) for node, data in graph.nodes(data=True)
                                 if data.get('type') in ['directory', 'class'] or len(list(graph.neighbors(node))) > 3}
                nx.draw_networkx_labels(graph, pos, labels=important_nodes, font_size=8, ax=ax)

                # Create legend
                legend_elements = [
                    patches.Patch(color='lightblue', label='Files'),
                    patches.Patch(color='lightgreen', label='Directories'),
                    patches.Patch(color='orange', label='Classes'),
                    patches.Patch(color='pink', label='Functions'),
                    patches.Patch(color='lightgray', label='Other')
                ]
                ax.legend(handles=legend_elements, loc='upper left', bbox_to_anchor=(0, 1))

                # Add statistics
                stats_text = f"Nodes: {num_nodes} | Edges: {graph.number_of_edges()}"
                ax.text(0.02, 0.02, stats_text, transform=ax.transAxes, fontsize=10,
                       bbox=dict(boxstyle="round,pad=0.3", facecolor="white", alpha=0.8))

                ax.set_title("Interactive Knowledge Graph Visualization", fontsize=12)
                ax.axis('off')

                # Create interactive window
                root = tk.Tk()
                root.title("🔗 Unfold Knowledge Graph")
                root.geometry("1000x700")

                # Add control frame
                control_frame = ttk.Frame(root)
                control_frame.pack(side=tk.TOP, fill=tk.X, padx=10, pady=5)

                ttk.Label(control_frame, text=f"📊 Graph Statistics: {stats_text}").pack(side=tk.LEFT)

                close_button = ttk.Button(control_frame, text="Close", command=root.destroy)
                close_button.pack(side=tk.RIGHT)

                # Embed matplotlib in tkinter
                from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
                canvas = FigureCanvasTkAgg(fig, master=root)
                canvas.draw()
                canvas.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=1)

                # Add toolbar
                from matplotlib.backends.backend_tkagg import NavigationToolbar2Tk
                toolbar = NavigationToolbar2Tk(canvas, root)
                toolbar.update()
                canvas.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=1)

                # Show the window
                root.lift()
                root.attributes('-topmost', True)
                root.after_idle(root.attributes, '-topmost', False)
                root.mainloop()

                plt.close(fig)

                return {
                    "success": True,
                    "message": "Knowledge graph visualization displayed successfully",
                    "nodes": num_nodes,
                    "edges": graph.number_of_edges()
                }

            except Exception as e:
                self.logger.error(f"Visualization error: {e}")
                return {"success": False, "error": f"Failed to create visualization: {str(e)}"}

        @self.mcp.tool()
        async def summarize_conversation() -> dict[str, Any]:
            """
            Summarize the current conversation for long-term memory.
            
            Returns:
                Dictionary containing conversation summary
            """
            if not self.llm_service or not self.vector_db:
                return {"error": "Required services not available"}

            try:
                # Get recent conversation history
                chat_history = self.llm_service.get_history()

                if not chat_history:
                    return {"summary": "No conversation to summarize"}

                # Create conversation context
                conversation_text = "\n".join([
                    f"{msg.role}: {msg.content}" for msg in chat_history[-10:]
                ])

                # Generate summary (this would use the LLM service)
                summary = f"Conversation summary: {len(chat_history)} messages exchanged about file operations and search queries."

                # Store in long-term memory
                success = self.vector_db.store_long_term_memory(summary, importance_score=0.8)

                return {
                    "summary": summary,
                    "messages_processed": len(chat_history),
                    "stored_in_memory": success
                }
            except Exception as e:
                self.logger.error(f"Conversation summary error: {e}")
                return {"error": str(e)}

        # System information tools
        @self.mcp.tool()
        async def get_system_stats() -> dict[str, Any]:
            """
            Get system statistics and health information.
            
            Returns:
                Dictionary containing system statistics
            """
            try:
                stats = {
                    "database": self.db_manager.get_stats(),
                    "search": self.file_searcher.get_search_stats()
                }

                if self.vector_db:
                    stats["vector_db"] = self.vector_db.get_collection_stats()
                    stats["vector_db_healthy"] = self.vector_db.health_check()  # Synchronous

                if self.graph_service:
                    stats["knowledge_graph"] = self.graph_service.get_stats()
                    stats["graph_db_healthy"] = self.graph_service.health_check()  # Synchronous

                if self.llm_service:
                    stats["llm_healthy"] = await self.llm_service.health_check()  # Async

                return stats
            except Exception as e:
                self.logger.error(f"System stats error: {e}")
                return {"error": str(e)}

        @self.mcp.tool()
        async def get_project_structure() -> dict[str, Any]:
            """
            Get an overview of the project structure and organization.
            
            Returns:
                Dictionary containing project structure information
            """
            if not self.graph_service:
                return {"error": "Graph service not available"}

            try:
                structure = self.graph_service.get_project_structure()
                return {
                    "project_structure": structure,
                    "analysis_type": "knowledge_graph"
                }
            except Exception as e:
                self.logger.error(f"Project structure error: {e}")
                return {"error": str(e)}



    def _register_resources(self):
        """Register resources that can be accessed by the AI assistant."""

        @self.mcp.resource("file://config")
        async def get_config() -> Resource:
            """Get current configuration."""
            return Resource(
                uri="file://config",
                name="Configuration",
                description="Current system configuration",
                mimeType="application/json",
                text=json.dumps(self.config_manager.config, indent=2)
            )

    async def start_server(self, host: str = "localhost", port: int = 8000):
        """Start the MCP server."""
        try:
            await self.mcp.run(host=host, port=port)
        except Exception as e:
            self.logger.error(f"Failed to start MCP server: {e}")
            raise

    def get_available_tools(self) -> list[dict[str, Any]]:
        """Get list of all available tools."""
        return self.tools.get_available_tools()

    async def handle_streaming_response(self, tool_name: str, parameters: dict[str, Any]) -> AsyncIterator[str]:
        """Handle streaming responses for tools that support it."""
        # This would be implemented for tools that can provide streaming responses
        yield f"Executing tool: {tool_name} with parameters: {parameters}"
        # Actual implementation would call the appropriate tool and stream results

    def close(self):
        """Clean up resources."""
        try:
            if self.vector_db:
                self.vector_db.close()
            if self.graph_service:
                self.graph_service.close()
            if self.db_manager:
                self.db_manager.close()
        except Exception as e:
            self.logger.error(f"Error during cleanup: {e}")
