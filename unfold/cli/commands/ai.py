"""
AI assistant command with rich interactive features.
"""

import asyncio
import os
from datetime import datetime

import click

from ...core.mcp_service import UnfoldMCPService
from ...utils.config import ConfigManager
from ..ui import (
    AIResponseStreamer,
    AIThinkingIndicator,
    InteractivePrompt,
    ServiceStatusDisplay,
    console,
    loading_indicator,
    show_error,
    show_success,
    show_warning,
)


class ToolCallMonitor:
    """Monitor and display MCP tool calls during AI interactions."""
    
    def __init__(self, mcp_service):
        self.mcp_service = mcp_service
        self.displayed_tools = set()
        
    async def check_for_tool_calls(self, chunk: str):
        """Check if the chunk mentions tools and display notifications."""
        # Simple pattern matching for tool mentions
        # In a real implementation, this would be integrated with the LLM's function calling
        available_tools = {tool['name'] for tool in self.mcp_service.get_available_tools()}
        
        # Look for tool names in the chunk
        chunk_lower = chunk.lower()
        for tool_name in available_tools:
            # Check for various patterns that might indicate tool usage
            patterns = [
                f"using {tool_name}",
                f"calling {tool_name}",
                f"executing {tool_name}",
                f"{tool_name}(",
                f"search_files" if "search" in chunk_lower and "files" in chunk_lower else None,
                f"list_directory" if "list" in chunk_lower and ("directory" in chunk_lower or "folder" in chunk_lower) else None,
                f"read_file" if "read" in chunk_lower and "file" in chunk_lower else None,
            ]
            
            for pattern in patterns:
                if pattern and pattern.replace("_", " ") in chunk_lower and tool_name not in self.displayed_tools:
                    self.displayed_tools.add(tool_name)
                    self._display_tool_call(tool_name)
                    break
    
    def _display_tool_call(self, tool_name: str):
        """Display a tool call notification."""
        # Get tool description for context
        tools = self.mcp_service.get_available_tools()
        tool_desc = next((t['description'] for t in tools if t['name'] == tool_name), "")
        short_desc = tool_desc[:50] + "..." if len(tool_desc) > 50 else tool_desc
        
        console.print(f"[dim]🔧 [cyan]{tool_name}[/cyan]: {short_desc}[/dim]")
    
    def show_available_tools_summary(self):
        """Show a summary of available tools at the start."""
        tools = self.mcp_service.get_available_tools()
        categories = {}
        for tool in tools:
            category = tool.get('category', 'other')
            if category not in categories:
                categories[category] = []
            categories[category].append(tool['name'])
        
        console.print("[dim]🛠️  Available tools:[/dim]")
        for category, tool_names in categories.items():
            console.print(f"[dim]   {category}: {', '.join(tool_names[:3])}{'...' if len(tool_names) > 3 else ''}[/dim]")


@click.command("ai")
@click.option("--model", "-m", help="Specify LLM model to use")
@click.option("--provider", "-p", help="Specify LLM provider (ollama/openai)")
@click.option("--streaming/--no-streaming", default=True, help="Enable streaming responses")
@click.option("--workdir", "-w", help="Specify working directory for this session")
def ai_command(
    model: str | None,
    provider: str | None,
    streaming: bool,
    workdir: str | None
) -> None:
    """Start AI assistant mode with file management capabilities."""
    try:
        asyncio.run(run_ai_assistant(model, provider, streaming, workdir))
    except KeyboardInterrupt:
        console.print("\n[yellow]AI assistant session ended[/yellow]")
    except Exception as e:
        show_error(f"Error starting AI assistant: {e}")


async def run_ai_assistant(
    model: str | None,
    provider: str | None,
    streaming: bool,
    workdir: str | None
) -> None:
    """Run the AI assistant with rich UI."""

    # Setup working directory
    if workdir:
        if not os.path.exists(workdir):
            show_error(f"Working directory does not exist: {workdir}")
            return
        os.chdir(workdir)

    current_workdir = os.getcwd()
    session_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # Initialize configuration
    with loading_indicator("🔧 Initializing configuration..."):
        config_manager = ConfigManager()

        # Update configuration with session context
        config_manager.set("session.working_directory", current_workdir)
        config_manager.set("session.timestamp", session_timestamp)
        config_manager.set("session.knowledge_log_path",
                          f"./knowledge/sessions/session_{session_timestamp}_{os.path.basename(current_workdir)}.log")

        # Update LLM config if options provided
        if model:
            config_manager.set("llm.model", model)
        if provider:
            config_manager.set("llm.provider", provider)
        config_manager.set("llm.stream", streaming)

    # Show welcome
    InteractivePrompt.show_welcome(
        title="🤖 Unfold AI Assistant",
        subtitle=f"Working Directory: {current_workdir}\nSession: {session_timestamp}"
    )

    # Initialize services with progress
    console.print("\n[cyan]🚀 Starting AI services...[/cyan]")

    try:
        with loading_indicator("🔧 Initializing AI services...") as indicator:
            indicator.update("Loading MCP service...")
            mcp_service = UnfoldMCPService(config_manager)

            indicator.update("Checking LLM service...")
            llm_service = mcp_service.llm_service

            if not llm_service:
                show_error("LLM service not available. Please check your configuration.")
                return

        # Show service status
        await display_service_status(mcp_service, llm_service)

        # Auto-index with progress
        console.print("\n[cyan]📁 Preparing workspace...[/cyan]")
        await warmup_workspace(mcp_service, current_workdir)

        # Start interactive session
        await interactive_ai_session(llm_service, mcp_service, streaming)

    except Exception as e:
        show_error(f"AI Assistant initialization failed: {e}")
    finally:
        # Cleanup
        if 'mcp_service' in locals():
            mcp_service.close()


async def display_service_status(mcp_service: UnfoldMCPService, llm_service) -> None:
    """Display service status with rich formatting."""
    services = {}

    # LLM Service
    try:
        if await llm_service.health_check():
            services["LLM Service"] = {
                "status": "connected",
                "details": f"{llm_service.config.provider.value}:{llm_service.config.model}"
            }
        else:
            services["LLM Service"] = {
                "status": "warning",
                "details": "Service responding but may have issues"
            }
    except Exception as e:
        services["LLM Service"] = {
            "status": "error",
            "details": f"Connection failed: {str(e)[:30]}..."
        }

    # Vector Database
    if mcp_service.vector_db:
        try:
            if mcp_service.vector_db.health_check():
                db_type = "Milvus Lite" if mcp_service.vector_db.use_milvus_lite else "Milvus"
                services["Vector DB"] = {
                    "status": "connected",
                    "details": f"{db_type} ready"
                }
            else:
                services["Vector DB"] = {
                    "status": "error",
                    "details": "Health check failed"
                }
        except Exception as e:
            services["Vector DB"] = {
                "status": "error",
                "details": f"{str(e)[:30]}..."
            }
    else:
        services["Vector DB"] = {
            "status": "warning",
            "details": "Vector database not available"
        }

    # Knowledge Graph
    if mcp_service.graph_service:
        try:
            if mcp_service.graph_service.health_check():
                provider = ConfigManager().get("graph_db.provider", "networkx")
                services["Knowledge Graph"] = {
                    "status": "connected",
                    "details": f"{provider.title()} ready"
                }
            else:
                services["Knowledge Graph"] = {
                    "status": "error",
                    "details": "Graph service connection failed"
                }
        except Exception as e:
            services["Knowledge Graph"] = {
                "status": "error",
                "details": f"{str(e)[:30]}..."
            }
    else:
        services["Knowledge Graph"] = {
            "status": "warning",
            "details": "Graph service not available (optional)"
        }

    # Display status table
    status_table = ServiceStatusDisplay.create_status_table(services)
    console.print(status_table)

    # Show available tools
    available_tools = []
    if llm_service:
        available_tools.append("AI chat")
    available_tools.append("file search")
    if mcp_service.vector_db and mcp_service.vector_db.health_check():
        available_tools.append("vector similarity")
    if mcp_service.graph_service and mcp_service.graph_service.health_check():
        available_tools.append("knowledge graph")
    available_tools.append("file operations")

    console.print(f"[dim]Available tools: {', '.join(available_tools)}[/dim]")


async def warmup_workspace(mcp_service: UnfoldMCPService, workdir: str) -> None:
    """Warmup workspace with progress indicators."""
    try:
        with loading_indicator("📁 Quick indexing workspace...") as indicator:
            # Import the function from the main CLI
            from ..utils import quick_index_directory

            indicator.update("Scanning files...")
            await quick_index_directory(mcp_service, workdir)

        show_success("✓ Workspace ready")

    except Exception as e:
        show_warning(f"⚠ Indexing failed: {str(e)[:50]}...")


async def interactive_ai_session(llm_service, mcp_service: UnfoldMCPService, streaming: bool) -> None:
    """Interactive AI session with rich UI."""

    # Show help
    commands = {
        "help": "Show available commands",
        "tools": "List available AI tools",
        "stats": "Show system statistics",
        "clear": "Clear screen",
        "quit/exit": "End session",
    }

    # Show available tools summary
    tool_monitor = ToolCallMonitor(mcp_service)
    tool_monitor.show_available_tools_summary()
    
    console.print("\n[dim]Type 'help' for commands or ask me anything![/dim]")

    while True:
        try:
            # Get user input
            user_input = InteractivePrompt.get_user_input("🤖 Ask me anything")

            if not user_input:
                continue

            if user_input.lower() in ["quit", "exit", "q"]:
                break
            elif user_input.lower() == "help":
                InteractivePrompt.show_help(commands)
                continue
            elif user_input.lower() == "tools":
                show_available_tools(mcp_service)
                continue
            elif user_input.lower() == "stats":
                await show_ai_stats(mcp_service)
                continue
            elif user_input.lower() == "clear":
                console.clear()
                continue

            # Process AI query
            await process_ai_query_rich(llm_service, mcp_service, user_input, streaming)

        except EOFError:
            console.print("\nAI assistant session ended")
            break
        except KeyboardInterrupt:
            console.print("\nCancellation requested; stopping current tasks.")
            break


async def process_ai_query_rich(
    llm_service,
    mcp_service: UnfoldMCPService,
    query: str,
    streaming: bool
) -> None:
    """Process AI query with rich UI components and actual tool calling."""
    try:
        # Get system prompt
        working_dir = os.getcwd()
        system_prompt = llm_service.get_system_prompt(working_directory=working_dir)

        if streaming:
            # Create thinking indicator
            thinking_indicator = AIThinkingIndicator()
            thinking_task = asyncio.create_task(thinking_indicator.start("🤔 AI is thinking"))

            # Create response streamer
            streamer = AIResponseStreamer()
            await streamer.start_streaming()

            try:
                # Add user message to history first
                llm_service.add_to_history("user", query)
                
                # Get AI response with actual tool calling
                response_parts = []
                async for chunk in llm_service._get_response_with_tools(
                    llm_service._prepare_messages(system_prompt), 
                    mcp_service.get_available_tools(), 
                    mcp_service
                ):
                    # Stop thinking indicator on first chunk
                    if not response_parts:
                        thinking_indicator.stop()
                        thinking_task.cancel()

                    response_parts.append(chunk)
                    await streamer.add_chunk(chunk)

                streamer.finish()

                # Store in memory
                full_response = "".join(response_parts)
                try:
                    if mcp_service.vector_db:
                        mcp_service.vector_db.store_short_term_memory(
                            f"Q: {query}\nA: {full_response}",
                            importance_score=0.6
                        )
                except Exception:
                    pass  # Silently continue if memory storage fails

            except Exception as e:
                thinking_indicator.stop()
                thinking_task.cancel()
                streamer.finish()
                raise e
        else:
            # Non-streaming mode with tool calling
            with loading_indicator("🤔 Processing your request..."):
                # Use the new chat_with_tools method
                full_response = await llm_service.chat_with_tools(query, system_prompt, mcp_service)
                console.print(f"\n🤖 {full_response}\n")

    except Exception as e:
        show_error(f"Error processing query: {e}")


def show_available_tools(mcp_service: UnfoldMCPService) -> None:
    """Show available tools in a rich table."""
    from rich.table import Table

    tools = mcp_service.get_available_tools()

    table = Table(title="🛠️ Available AI Tools", show_header=True)
    table.add_column("Tool", style="cyan")
    table.add_column("Description", style="white")
    table.add_column("Status", style="green")

    for tool in tools:
        status = "✓ Available"
        table.add_row(tool["name"], tool["description"][:60] + "...", status)

    console.print(table)


async def show_ai_stats(mcp_service: UnfoldMCPService) -> None:
    """Show AI stats with rich formatting."""
    from rich.table import Table

    with loading_indicator("📊 Gathering statistics..."):
        table = Table(title="📊 AI System Statistics", show_header=True)
        table.add_column("Component", style="cyan")
        table.add_column("Status", style="white")
        table.add_column("Details", style="dim")

        # Database stats
        if mcp_service.db_manager:
            try:
                db_stats = mcp_service.db_manager.get_stats()
                table.add_row("Database", "✓ Connected", f"{db_stats.get('total_files', 0)} files indexed")
            except Exception as e:
                table.add_row("Database", "✗ Error", f"Failed to get stats: {str(e)[:30]}...")

        # Vector DB stats
        if mcp_service.vector_db:
            try:
                if mcp_service.vector_db.health_check():
                    vdb_stats = mcp_service.vector_db.get_collection_stats() if hasattr(mcp_service.vector_db, "get_collection_stats") else {}
                    files_count = vdb_stats.get("files_indexed", "N/A")
                    table.add_row("Vector DB", "✓ Healthy", f"{files_count} files vectorized")
                else:
                    table.add_row("Vector DB", "⚠ Issues", "Health check failed")
            except Exception as e:
                table.add_row("Vector DB", "✗ Error", f"{str(e)[:30]}...")
        else:
            table.add_row("Vector DB", "✗ Disabled", "Vector database not available")

        # Knowledge Graph stats
        if mcp_service.graph_service:
            try:
                if mcp_service.graph_service.health_check():
                    graph_stats = mcp_service.graph_service.get_stats()
                    nodes = graph_stats.get("nodes", 0)
                    edges = graph_stats.get("edges", 0)
                    files = graph_stats.get("files", 0)
                    table.add_row("Knowledge Graph", "✓ Healthy", f"{nodes} nodes, {edges} edges, {files} files")
                else:
                    table.add_row("Knowledge Graph", "⚠ Issues", "Health check failed")
            except Exception as e:
                table.add_row("Knowledge Graph", "✗ Error", f"{str(e)[:30]}...")
        else:
            table.add_row("Knowledge Graph", "✗ Optional", "Graph service not available")

        # LLM stats
        if mcp_service.llm_service:
            try:
                if await mcp_service.llm_service.health_check():
                    model_info = f"{mcp_service.llm_service.config.provider.value}:{mcp_service.llm_service.config.model}"
                    table.add_row("LLM Service", "✓ Healthy", f"Model: {model_info}")
                else:
                    table.add_row("LLM Service", "⚠ Issues", "Health check failed")
            except Exception as e:
                table.add_row("LLM Service", "✗ Error", f"{str(e)[:30]}...")
        else:
            table.add_row("LLM Service", "✗ Disabled", "LLM service not available")

    console.print(table)
