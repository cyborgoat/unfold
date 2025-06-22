"""
Legacy CLI module - redirects to new modular CLI structure.
"""

# Import the new modular CLI
from .cli.main import main

# Re-export main for backward compatibility
__all__ = ["main"]
