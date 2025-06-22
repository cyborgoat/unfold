"""
Configuration management for Unfold settings and preferences.
"""

import json
import os
from typing import Any

import appdirs


class ConfigManager:
    """Manages user configuration and settings."""

    DEFAULT_CONFIG = {
        "indexing": {
            "index_hidden_files": False,
            "index_directories": True,
            "excluded_extensions": [".tmp", ".temp", ".log", ".cache", ".lock"],
            "excluded_paths": [
                ".git",
                ".svn",
                "node_modules",
                "__pycache__",
                ".DS_Store",
            ],
            "auto_index_paths": [],
            "watch_paths": [],
            "enable_real_time_monitoring": True,
            "knowledge_base_path": "./knowledge",
        },
        "search": {
            "enable_fuzzy_matching": True,
            "fuzzy_threshold": 0.6,
            "max_results": 50,
            "cache_results": True,
            "case_sensitive": False,
        },
        "ui": {
            "show_file_sizes": True,
            "show_modified_times": True,
            "max_path_length": 60,
            "color_scheme": "auto",
        },
        "performance": {
            "database_cache_size": 100,
            "indexing_batch_size": 1000,
            "search_timeout": 30,
        },
        "llm": {
            "provider": "ollama",
            "model": "llama3.2",
            "base_url": "http://localhost:11434",
            "api_key": None,
            "temperature": 0.7,
            "max_tokens": 2048,
            "timeout": 30.0,
            "stream": True,
        },
        "vector_db": {
            "host": "localhost",
            "port": "19530",
            "enabled": True,
            "use_milvus_lite": True,
            "local_db_path": "./knowledge/vector.db",
            "embedding_model": "Qwen/Qwen3-Embedding-0.6B",
            "chunk_size": 512,
            "chunk_overlap": 50,
        },
        "graph_db": {
            "provider": "networkx",  # "networkx" or "neo4j"
            "uri": "bolt://localhost:7687",
            "user": "neo4j",
            "password": "password",
            "database": "unfold",
            "enabled": True,  # Enabled by default with NetworkX
            "optional": True,  # Mark as optional service
        },
        "mcp": {
            "host": "localhost",
            "port": 8000,
            "enabled": True,
        },
        "ai_assistant": {
            "enabled": True,
            "streaming_response": True,
            "context_window": 20,
            "memory_retention_days": 30,
        },
        "session": {
            "working_directory": "./",
            "timestamp": "",
            "knowledge_log_path": "./knowledge/sessions/",
        },
    }

    def __init__(self, config_path: str | None = None):
        if config_path is None:
            app_dir = appdirs.user_config_dir("unfold", "unfold")
            os.makedirs(app_dir, exist_ok=True)
            config_path = os.path.join(app_dir, "config.json")

        self.config_path = config_path
        self.config = self._load_config()
        
        # Load .env overrides
        self._load_env_overrides()

    def _load_config(self) -> dict[str, Any]:
        """Load configuration from file or create default."""
        try:
            if os.path.exists(self.config_path):
                with open(self.config_path) as f:
                    config = json.load(f)
                # Merge with defaults to ensure all keys exist
                return self._merge_config(self.DEFAULT_CONFIG, config)
            else:
                return self.DEFAULT_CONFIG.copy()
        except Exception as e:
            print(f"Error loading config: {e}")
            return self.DEFAULT_CONFIG.copy()

    def _merge_config(self, default: dict, user: dict) -> dict:
        """Recursively merge user config with defaults."""
        result = default.copy()
        for key, value in user.items():
            if (
                key in result
                and isinstance(result[key], dict)
                and isinstance(value, dict)
            ):
                result[key] = self._merge_config(result[key], value)
            else:
                result[key] = value
        return result

    def _load_env_overrides(self) -> None:
        """Load configuration overrides from .env file and environment variables."""
        # First, try to load from .env file
        env_file_path = os.path.join(os.getcwd(), ".env")
        env_vars = {}
        
        if os.path.exists(env_file_path):
            try:
                with open(env_file_path, 'r') as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith('#') and '=' in line:
                            key, value = line.split('=', 1)
                            env_vars[key.strip()] = value.strip().strip('"\'')
            except Exception as e:
                print(f"Warning: Error reading .env file: {e}")
        
        # Also check actual environment variables (they take precedence)
        env_vars.update(os.environ)
        
        # Map environment variables to config paths
        env_mappings = {
            # LLM Configuration
            "UNFOLD_LLM_PROVIDER": "llm.provider",
            "UNFOLD_LLM_MODEL": "llm.model", 
            "UNFOLD_LLM_BASE_URL": "llm.base_url",
            "UNFOLD_LLM_API_KEY": "llm.api_key",
            "UNFOLD_LLM_TEMPERATURE": "llm.temperature",
            "UNFOLD_LLM_MAX_TOKENS": "llm.max_tokens",
            "UNFOLD_LLM_TIMEOUT": "llm.timeout",
            
            # Vector DB Configuration
            "UNFOLD_VECTOR_DB_HOST": "vector_db.host",
            "UNFOLD_VECTOR_DB_PORT": "vector_db.port",
            "UNFOLD_VECTOR_DB_ENABLED": "vector_db.enabled",
            "UNFOLD_VECTOR_DB_USE_MILVUS_LITE": "vector_db.use_milvus_lite",
            "UNFOLD_VECTOR_DB_LOCAL_PATH": "vector_db.local_db_path",
            "UNFOLD_VECTOR_DB_EMBEDDING_MODEL": "vector_db.embedding_model",
            
            # Graph DB Configuration
            "UNFOLD_GRAPH_DB_PROVIDER": "graph_db.provider",
            "UNFOLD_GRAPH_DB_URI": "graph_db.uri",
            "UNFOLD_GRAPH_DB_USER": "graph_db.user",
            "UNFOLD_GRAPH_DB_PASSWORD": "graph_db.password",
            "UNFOLD_GRAPH_DB_DATABASE": "graph_db.database",
            "UNFOLD_GRAPH_DB_ENABLED": "graph_db.enabled",
            
            # MCP Configuration
            "UNFOLD_MCP_HOST": "mcp.host",
            "UNFOLD_MCP_PORT": "mcp.port",
            "UNFOLD_MCP_ENABLED": "mcp.enabled",
            
            # AI Assistant Configuration
            "UNFOLD_AI_ENABLED": "ai_assistant.enabled",
            "UNFOLD_AI_STREAMING": "ai_assistant.streaming_response",
            "UNFOLD_AI_CONTEXT_WINDOW": "ai_assistant.context_window",
        }
        
        # Apply environment variable overrides
        for env_key, config_path in env_mappings.items():
            if env_key in env_vars:
                value = env_vars[env_key]
                
                # Type conversion based on the config path
                if config_path.endswith(('.enabled', '.stream', '.use_milvus_lite', '.streaming_response')):
                    # Boolean values
                    value = value.lower() in ('true', '1', 'yes', 'on')
                elif config_path.endswith(('.port', '.max_tokens', '.context_window')):
                    # Integer values
                    try:
                        value = int(value)
                    except ValueError:
                        print(f"Warning: Invalid integer value for {env_key}: {value}")
                        continue
                elif config_path.endswith(('.temperature', '.timeout')):
                    # Float values
                    try:
                        value = float(value)
                    except ValueError:
                        print(f"Warning: Invalid float value for {env_key}: {value}")
                        continue
                
                # Set the configuration value
                self.set(config_path, value)
                print(f"Config override from environment: {config_path} = {value}")

    def save_config(self) -> None:
        """Save current configuration to file."""
        try:
            os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
            with open(self.config_path, "w") as f:
                json.dump(self.config, f, indent=2)
        except Exception as e:
            print(f"Error saving config: {e}")

    def get(self, key_path: str, default: Any = None) -> Any:
        """Get configuration value using dot notation (e.g., 'search.fuzzy_threshold')."""
        keys = key_path.split(".")
        value = self.config

        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return default

        return value

    def set(self, key_path: str, value: Any) -> None:
        """Set configuration value using dot notation."""
        keys = key_path.split(".")
        config = self.config

        for key in keys[:-1]:
            if key not in config:
                config[key] = {}
            config = config[key]

        config[keys[-1]] = value

    def reset_to_defaults(self) -> None:
        """Reset configuration to default values."""
        self.config = self.DEFAULT_CONFIG.copy()
        self.save_config()

    def add_watch_path(self, path: str) -> None:
        """Add a path to be monitored for changes."""
        watch_paths = self.get("indexing.watch_paths", [])
        if path not in watch_paths:
            watch_paths.append(path)
            self.set("indexing.watch_paths", watch_paths)
            self.save_config()

    def remove_watch_path(self, path: str) -> None:
        """Remove a path from monitoring."""
        watch_paths = self.get("indexing.watch_paths", [])
        if path in watch_paths:
            watch_paths.remove(path)
            self.set("indexing.watch_paths", watch_paths)
            self.save_config()

    def add_excluded_extension(self, ext: str) -> None:
        """Add file extension to exclusion list."""
        excluded = self.get("indexing.excluded_extensions", [])
        if ext not in excluded:
            excluded.append(ext)
            self.set("indexing.excluded_extensions", excluded)
            self.save_config()

    def remove_excluded_extension(self, ext: str) -> None:
        """Remove file extension from exclusion list."""
        excluded = self.get("indexing.excluded_extensions", [])
        if ext in excluded:
            excluded.remove(ext)
            self.set("indexing.excluded_extensions", excluded)
            self.save_config()

    def get_indexing_config(self) -> dict[str, Any]:
        """Get indexing-specific configuration."""
        return self.get("indexing", {})

    def get_search_config(self) -> dict[str, Any]:
        """Get search-specific configuration."""
        return self.get("search", {})

    def export_config(self, export_path: str) -> None:
        """Export configuration to a file."""
        with open(export_path, "w") as f:
            json.dump(self.config, f, indent=2)

    def import_config(self, import_path: str) -> None:
        """Import configuration from a file."""
        with open(import_path) as f:
            imported_config = json.load(f)

        self.config = self._merge_config(self.DEFAULT_CONFIG, imported_config)
        self.save_config()
