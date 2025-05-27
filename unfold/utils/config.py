"""
Configuration management for Unfold settings and preferences.
"""

import os
import json
from typing import Dict, Any, Optional
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
    }

    def __init__(self, config_path: Optional[str] = None):
        if config_path is None:
            app_dir = appdirs.user_config_dir("unfold", "unfold")
            os.makedirs(app_dir, exist_ok=True)
            config_path = os.path.join(app_dir, "config.json")

        self.config_path = config_path
        self.config = self._load_config()

    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from file or create default."""
        try:
            if os.path.exists(self.config_path):
                with open(self.config_path, "r") as f:
                    config = json.load(f)
                # Merge with defaults to ensure all keys exist
                return self._merge_config(self.DEFAULT_CONFIG, config)
            else:
                return self.DEFAULT_CONFIG.copy()
        except Exception as e:
            print(f"Error loading config: {e}")
            return self.DEFAULT_CONFIG.copy()

    def _merge_config(self, default: Dict, user: Dict) -> Dict:
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

    def get_indexing_config(self) -> Dict[str, Any]:
        """Get indexing-specific configuration."""
        return self.get("indexing", {})

    def get_search_config(self) -> Dict[str, Any]:
        """Get search-specific configuration."""
        return self.get("search", {})

    def export_config(self, export_path: str) -> None:
        """Export configuration to a file."""
        with open(export_path, "w") as f:
            json.dump(self.config, f, indent=2)

    def import_config(self, import_path: str) -> None:
        """Import configuration from a file."""
        with open(import_path, "r") as f:
            imported_config = json.load(f)

        self.config = self._merge_config(self.DEFAULT_CONFIG, imported_config)
        self.save_config()
