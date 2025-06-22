"""
LLM Service for AI-enhanced file operations and question answering.
Supports Ollama and OpenAI compatible endpoints with streaming capabilities.
"""

import logging
from collections.abc import AsyncIterator
from dataclasses import dataclass
from enum import Enum
from typing import Any

import ollama
import openai
from pydantic import BaseModel

from ..utils.config import ConfigManager


class LLMProvider(Enum):
    """Supported LLM providers."""
    OLLAMA = "ollama"
    OPENAI = "openai"
    CUSTOM = "custom"


@dataclass
class ChatMessage:
    """Represents a chat message."""
    role: str  # 'user', 'assistant', 'system'
    content: str
    metadata: dict[str, Any] | None = None


class LLMConfig(BaseModel):
    """Configuration for LLM service."""
    provider: LLMProvider = LLMProvider.OLLAMA
    model: str = "llama3.2"
    base_url: str = "http://localhost:11434"
    api_key: str | None = None
    temperature: float = 0.7
    max_tokens: int = 2048
    timeout: float = 30.0
    stream: bool = True


class LLMService:
    """
    LLM Service for AI-enhanced file operations.
    Provides streaming chat, function calling, and context management.
    """

    def __init__(self, config: LLMConfig | None = None, config_manager: ConfigManager | None = None):
        self.config = config or self._load_config(config_manager)
        self.config_manager = config_manager or ConfigManager()
        self.logger = logging.getLogger(__name__)

        # Initialize clients
        self.ollama_client = None
        self.openai_client = None
        self._initialize_clients()

        # Chat history for context
        self.chat_history: list[ChatMessage] = []
        self.max_history_length = 20

    def _load_config(self, config_manager: ConfigManager | None) -> LLMConfig:
        """Load LLM configuration."""
        cm = config_manager or ConfigManager()

        llm_config = cm.get("llm", {})
        return LLMConfig(
            provider=LLMProvider(llm_config.get("provider", "ollama")),
            model=llm_config.get("model", "llama3.2"),
            base_url=llm_config.get("base_url", "http://localhost:11434"),
            api_key=llm_config.get("api_key"),
            temperature=llm_config.get("temperature", 0.7),
            max_tokens=llm_config.get("max_tokens", 2048),
            timeout=llm_config.get("timeout", 30.0),
            stream=llm_config.get("stream", True)
        )

    def _initialize_clients(self):
        """Initialize LLM clients based on configuration."""
        try:
            if self.config.provider == LLMProvider.OLLAMA:
                self.ollama_client = ollama.AsyncClient(host=self.config.base_url)
            elif self.config.provider == LLMProvider.OPENAI:
                self.openai_client = openai.AsyncOpenAI(
                    api_key=self.config.api_key,
                    base_url=self.config.base_url if self.config.base_url != "http://localhost:11434" else None,
                    timeout=self.config.timeout
                )
        except Exception as e:
            self.logger.error(f"Failed to initialize LLM client: {e}")

    async def chat_streaming(
        self,
        message: str,
        system_prompt: str | None = None,
        tools: list[dict] | None = None
    ) -> AsyncIterator[str]:
        """
        Stream chat responses from the LLM.
        
        Args:
            message: User message
            system_prompt: Optional system prompt
            tools: Optional list of available tools for function calling
            
        Yields:
            str: Streaming response chunks
        """
        # Add user message to history
        self.add_to_history("user", message)

        # Prepare messages
        messages = self._prepare_messages(system_prompt)

        try:
            if self.config.provider == LLMProvider.OLLAMA:
                async for chunk in self._stream_ollama(messages, tools):
                    yield chunk
            elif self.config.provider == LLMProvider.OPENAI:
                async for chunk in self._stream_openai(messages, tools):
                    yield chunk
        except Exception as e:
            self.logger.error(f"Error in streaming chat: {e}")
            yield f"Error: {str(e)}"

    async def _stream_ollama(self, messages: list[dict], tools: list[dict] | None = None) -> AsyncIterator[str]:
        """Stream responses from Ollama."""
        if not self.ollama_client:
            raise ValueError("Ollama client not initialized")

        try:
            kwargs = {
                "model": self.config.model,
                "messages": messages,
                "stream": True,
                "options": {
                    "temperature": self.config.temperature,
                    "num_predict": self.config.max_tokens
                }
            }

            # Note: Ollama doesn't support tools/function calling in this version
            # if tools:
            #     kwargs["tools"] = tools

            response = await self.ollama_client.chat(**kwargs)

            assistant_response = ""
            async for chunk in response:
                if chunk.get('message') and chunk['message'].get('content'):
                    content = chunk['message']['content']
                    assistant_response += content
                    yield content

            # Add assistant response to history
            if assistant_response:
                self.add_to_history("assistant", assistant_response)

        except Exception as e:
            self.logger.error(f"Ollama streaming error: {e}")
            raise

    async def _stream_openai(self, messages: list[dict], tools: list[dict] | None = None) -> AsyncIterator[str]:
        """Stream responses from OpenAI compatible endpoint."""
        if not self.openai_client:
            raise ValueError("OpenAI client not initialized")

        try:
            kwargs = {
                "model": self.config.model,
                "messages": messages,
                "stream": True,
                "temperature": self.config.temperature,
                "max_tokens": self.config.max_tokens
            }

            if tools:
                kwargs["tools"] = tools
                kwargs["tool_choice"] = "auto"

            response = await self.openai_client.chat.completions.create(**kwargs)

            assistant_response = ""
            async for chunk in response:
                if chunk.choices and chunk.choices[0].delta.content:
                    content = chunk.choices[0].delta.content
                    assistant_response += content
                    yield content

            # Add assistant response to history
            if assistant_response:
                self.add_to_history("assistant", assistant_response)

        except Exception as e:
            self.logger.error(f"OpenAI streaming error: {e}")
            raise

    def _prepare_messages(self, system_prompt: str | None = None) -> list[dict]:
        """Prepare messages for LLM API."""
        messages = []

        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})

        # Add chat history
        for msg in self.chat_history[-self.max_history_length:]:
            messages.append({"role": msg.role, "content": msg.content})

        return messages

    def add_to_history(self, role: str, content: str, metadata: dict | None = None):
        """Add message to chat history."""
        self.chat_history.append(ChatMessage(role=role, content=content, metadata=metadata))

        # Trim history if too long
        if len(self.chat_history) > self.max_history_length:
            self.chat_history = self.chat_history[-self.max_history_length:]

    def clear_history(self):
        """Clear chat history."""
        self.chat_history.clear()

    def get_history(self) -> list[ChatMessage]:
        """Get current chat history."""
        return self.chat_history.copy()

    async def function_call(self, function_name: str, parameters: dict[str, Any]) -> Any:
        """
        Execute a function call through the LLM.
        This will be used by the MCP service to handle tool calls.
        """
        # This method will be implemented in conjunction with the MCP service
        pass

    async def chat_with_tools(
        self,
        message: str,
        system_prompt: str | None = None,
        mcp_service = None
    ) -> str:
        """
        Chat with tool calling support.
        
        Args:
            message: User message
            system_prompt: Optional system prompt
            mcp_service: MCP service for tool execution
            
        Returns:
            str: Complete response including tool calls
        """
        # Add user message to history
        self.add_to_history("user", message)

        # Prepare messages
        messages = self._prepare_messages(system_prompt)
        
        # Get available tools
        tools = mcp_service.get_available_tools() if mcp_service else []
        
        # Add tools information to the system prompt
        if tools and system_prompt:
            tools_info = "\n\nAvailable tools:\n"
            for tool in tools:
                tools_info += f"- {tool['name']}: {tool['description']}\n"
            
            # Update system message with tools info
            for msg in messages:
                if msg['role'] == 'system':
                    msg['content'] += tools_info
                    break

        try:
            # Get initial response
            response_parts = []
            async for chunk in self._get_response_with_tools(messages, tools, mcp_service):
                response_parts.append(chunk)

            full_response = "".join(response_parts)
            
            # Add assistant response to history
            if full_response:
                self.add_to_history("assistant", full_response)
            
            return full_response

        except Exception as e:
            self.logger.error(f"Error in chat with tools: {e}")
            return f"Error: {str(e)}"

    async def _get_response_with_tools(self, messages: list[dict], tools: list[dict], mcp_service) -> AsyncIterator[str]:
        """Get response with tool calling support."""
        
        # Get the user's query from the last message
        user_query = ""
        for msg in reversed(messages):
            if msg['role'] == 'user':
                user_query = msg['content']
                break
        
        # First, check if we need to call tools based on the user query
        if mcp_service and tools:
            tool_calls = self._infer_tool_calls(user_query, tools)
            
            if tool_calls:
                yield "🔧 **Executing tools:**\n"
                
                tool_results = []
                for tool_call in tool_calls:
                    tool_name = tool_call['name']
                    parameters = tool_call['parameters']
                    
                    yield f"- Calling `{tool_name}` with parameters: {parameters}\n"
                    
                    try:
                        # Execute the tool
                        result = await self._execute_tool(mcp_service, tool_name, parameters)
                        tool_results.append(f"Tool {tool_name} result: {result}")
                        
                        yield f"  ✓ Success\n"
                        
                    except Exception as e:
                        yield f"  ✗ Error: {str(e)}\n"
                        tool_results.append(f"Tool {tool_name} error: {str(e)}")
                
                yield "\n🤖 **Based on the tool results:**\n"
                
                # Add tool results to the context for LLM response
                tool_context = "\n".join(tool_results)
                enhanced_prompt = f"User query: {user_query}\n\nTool execution results:\n{tool_context}\n\nBased on these actual results, provide a helpful and accurate response to the user:"
                
                # Update the last user message with tool context
                messages[-1]['content'] = enhanced_prompt
                
                # Get LLM response with tool context
                if self.config.provider == LLMProvider.OLLAMA:
                    async for chunk in self._stream_ollama(messages, []):
                        yield chunk
                elif self.config.provider == LLMProvider.OPENAI:
                    async for chunk in self._stream_openai(messages, []):
                        yield chunk
                        
                return
        
        # No tools needed, get regular LLM response
        if self.config.provider == LLMProvider.OLLAMA:
            async for chunk in self._stream_ollama(messages, tools):
                yield chunk
        elif self.config.provider == LLMProvider.OPENAI:
            async for chunk in self._stream_openai(messages, tools):
                yield chunk



    def _infer_tool_calls(self, response: str, available_tools: list[dict]) -> list[dict]:
        """Infer tool calls based on response content and user intent."""
        import re
        
        tool_calls = []
        response_lower = response.lower()
        
        # Infer based on common patterns
        if any(phrase in response_lower for phrase in ['list files', 'show files', 'directory contents', 'what files', 'files in']):
            tool_calls.append({
                'name': 'list_directory',
                'parameters': self._extract_parameters(response, 'list_directory')
            })
        
        elif any(phrase in response_lower for phrase in ['read file', 'show content', 'file content', 'open file']):
            tool_calls.append({
                'name': 'read_file', 
                'parameters': self._extract_parameters(response, 'read_file')
            })
        
        elif any(phrase in response_lower for phrase in ['search for', 'find files', 'locate files']):
            tool_calls.append({
                'name': 'search_files',
                'parameters': self._extract_parameters(response, 'search_files')
            })
        
        elif any(phrase in response_lower for phrase in ['analyze', 'examine', 'inspect']):
            if 'project' in response_lower or 'structure' in response_lower:
                tool_calls.append({
                    'name': 'analyze_project_structure',
                    'parameters': {}
                })
            elif 'file' in response_lower:
                tool_calls.append({
                    'name': 'analyze_file_content',
                    'parameters': self._extract_parameters(response, 'analyze_file_content')
                })
        
        elif any(phrase in response_lower for phrase in ['system info', 'system information', 'system stats']):
            tool_calls.append({
                'name': 'get_system_info',
                'parameters': {}
            })
        
        return tool_calls

    def _extract_parameters(self, response: str, tool_name: str) -> dict:
        """Extract parameters for a tool call from the response."""
        import re
        
        # Simple parameter extraction - this could be much more sophisticated
        parameters = {}
        
        # Look for quoted strings that might be parameters
        if 'search' in tool_name:
            # Look for search queries
            search_patterns = [
                r'"([^"]+)"',
                r"'([^']+)'",
                r"search for ([^\n\.,!?]+)",
                r"find ([^\n\.,!?]+)"
            ]
            
            for pattern in search_patterns:
                match = re.search(pattern, response, re.IGNORECASE)
                if match:
                    parameters['query'] = match.group(1).strip()
                    break
            
            if not parameters.get('query'):
                # Default to a general search
                parameters['query'] = 'files'
        
        elif 'list' in tool_name:
            # For list_directory, try to extract path
            path_patterns = [
                r'(?:in|of|from)\s+([^\s\n\.,!?]+)',
                r'directory\s+([^\s\n\.,!?]+)'
            ]
            
            for pattern in path_patterns:
                match = re.search(pattern, response, re.IGNORECASE)
                if match:
                    path = match.group(1).strip()
                    # Don't use 'current' as a path, leave empty for current directory
                    if path.lower() not in ['current', 'this', 'here']:
                        parameters['path'] = path
                    break
        
        elif 'read' in tool_name:
            # For read_file, try to extract file path
            file_patterns = [
                r'(?:read|open|show)\s+([^\s\n\.,!?]+\.[a-zA-Z0-9]+)',
                r'file\s+([^\s\n\.,!?]+)'
            ]
            
            for pattern in file_patterns:
                match = re.search(pattern, response, re.IGNORECASE)
                if match:
                    parameters['file_path'] = match.group(1).strip()
                    break
        
        return parameters

    async def _execute_tool(self, mcp_service, tool_name: str, parameters: dict) -> Any:
        """Execute a tool through the MCP service."""
        # Get the tool method from the MCP service
        if hasattr(mcp_service.tools, tool_name):
            tool_method = getattr(mcp_service.tools, tool_name)
            return await tool_method(**parameters)
        else:
            raise ValueError(f"Tool {tool_name} not found")

    def get_system_prompt(self, working_directory: str = None) -> str:
        """Get the system prompt for the AI assistant."""
        base_prompt = """You are an AI assistant integrated into the Unfold file management system.

IMPORTANT: You have access to powerful tools that you MUST use to provide accurate, real-time information. 
NEVER guess or hallucinate file contents, directory listings, or system information.

When users ask about:
- "list files" or "show directory contents" → Use list_directory tool
- "read file" or "show file content" → Use read_file tool  
- "search for files" → Use search_files tool
- "find similar content" → Use semantic_search tool
- "analyze file" → Use analyze_file_content tool
- "project structure" → Use analyze_project_structure tool
- "system info" → Use get_system_info tool

ALWAYS use the appropriate tool first, then provide a helpful summary based on the ACTUAL results.

Available tool categories:
- File operations: list_directory, read_file, write_file, delete_file, move_file, copy_file, create_directory
- Search: search_files, semantic_search, get_file_relationships, index_directory  
- Analysis: analyze_file_content, suggest_file_improvements, analyze_project_structure
- System: execute_command, get_system_info, clear_cache
- Memory: store_memory, search_memory, get_memory_stats
- Visualization: visualize_knowledge_graph, export_graph_data"""

        if working_directory:
            base_prompt += f"\n\nCurrent working directory: {working_directory}"
            base_prompt += "\nWhen users ask about 'this directory' or similar, they're referring to the current working directory."

        return base_prompt

    async def health_check(self) -> bool:
        """Check if the LLM service is healthy and accessible."""
        try:
            if self.config.provider == LLMProvider.OLLAMA:
                if not self.ollama_client:
                    return False
                # Try a simple model list request
                models = await self.ollama_client.list()
                return len(models.get('models', [])) > 0
            elif self.config.provider == LLMProvider.OPENAI:
                if not self.openai_client:
                    return False
                # Try a simple models request
                models = await self.openai_client.models.list()
                return len(models.data) > 0
            return False
        except Exception as e:
            self.logger.error(f"Health check failed: {e}")
            return False

    def update_config(self, new_config: LLMConfig):
        """Update LLM configuration."""
        self.config = new_config
        self._initialize_clients()
