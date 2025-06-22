"""
System operations tools for MCP integration.
"""

import os
import shutil
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any


class SystemTools:
    """Tools for system operations and information."""

    def __init__(self, working_directory: str = None):
        """Initialize system tools."""
        self.working_directory = working_directory or os.getcwd()

    async def execute_command(self, command: str, working_dir: str = None, timeout: int = 30) -> dict[str, Any]:
        """Execute shell command with safety checks."""
        try:
            # Safety check for dangerous commands
            dangerous_commands = ['rm -rf', 'sudo', 'format', 'del /f', 'rmdir /s', 'chmod 777']
            if any(dangerous in command.lower() for dangerous in dangerous_commands):
                return {
                    "success": False,
                    "error": f"Dangerous command blocked: {command}"
                }

            work_dir = working_dir or self.working_directory

            # Execute command
            result = subprocess.run(
                command,
                shell=True,
                cwd=work_dir,
                capture_output=True,
                text=True,
                timeout=timeout
            )

            return {
                "success": result.returncode == 0,
                "command": command,
                "return_code": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "working_directory": work_dir
            }

        except subprocess.TimeoutExpired:
            return {"success": False, "error": f"Command timed out after {timeout} seconds"}
        except Exception as e:
            return {"success": False, "error": f"Command execution failed: {str(e)}"}

    async def get_system_info(self) -> dict[str, Any]:
        """Get system and environment information."""
        try:
            import platform
            import psutil

            # Basic system information
            system_info = {
                "platform": platform.platform(),
                "system": platform.system(),
                "machine": platform.machine(),
                "processor": platform.processor(),
                "python_version": platform.python_version(),
                "working_directory": self.working_directory
            }

            # Memory information
            memory = psutil.virtual_memory()
            system_info["memory"] = {
                "total": memory.total,
                "available": memory.available,
                "percent": memory.percent,
                "used": memory.used,
                "free": memory.free
            }

            # Disk information
            disk = psutil.disk_usage(self.working_directory)
            system_info["disk"] = {
                "total": disk.total,
                "used": disk.used,
                "free": disk.free,
                "percent": (disk.used / disk.total) * 100
            }

            # CPU information
            system_info["cpu"] = {
                "count": psutil.cpu_count(),
                "percent": psutil.cpu_percent(interval=1),
                "freq": psutil.cpu_freq()._asdict() if psutil.cpu_freq() else None
            }

            return {
                "success": True,
                "system_info": system_info,
                "timestamp": datetime.now().isoformat()
            }

        except ImportError:
            # Fallback without psutil
            import platform
            return {
                "success": True,
                "system_info": {
                    "platform": platform.platform(),
                    "system": platform.system(),
                    "machine": platform.machine(),
                    "python_version": platform.python_version(),
                    "working_directory": self.working_directory
                },
                "timestamp": datetime.now().isoformat(),
                "note": "Limited system info (psutil not available)"
            }
        except Exception as e:
            return {"success": False, "error": f"Failed to get system info: {str(e)}"}

    async def clear_cache(self, cache_type: str = "all") -> dict[str, Any]:
        """Clear various caches and temporary data."""
        try:
            cleared_items = []
            errors = []

            if cache_type in ["all", "knowledge"]:
                # Clear knowledge directory
                knowledge_dir = Path(self.working_directory) / "knowledge"
                if knowledge_dir.exists():
                    try:
                        shutil.rmtree(knowledge_dir)
                        knowledge_dir.mkdir(exist_ok=True)
                        cleared_items.append("knowledge directory")
                    except Exception as e:
                        errors.append(f"Knowledge cache: {str(e)}")

            if cache_type in ["all", "database"]:
                # Clear database cache files
                try:
                    import appdirs
                    app_dir = Path(appdirs.user_data_dir("unfold", "unfold"))
                    db_files = list(app_dir.glob("*.db"))
                    for db_file in db_files:
                        try:
                            db_file.unlink()
                            cleared_items.append(f"database file: {db_file.name}")
                        except Exception as e:
                            errors.append(f"Database file {db_file.name}: {str(e)}")
                except Exception as e:
                    errors.append(f"Database cache: {str(e)}")

            if cache_type in ["all", "temp"]:
                # Clear temporary files
                temp_patterns = ["*.tmp", "*.temp", "*.cache", "*~"]
                for pattern in temp_patterns:
                    try:
                        temp_files = list(Path(self.working_directory).rglob(pattern))
                        for temp_file in temp_files:
                            try:
                                temp_file.unlink()
                                cleared_items.append(f"temp file: {temp_file.name}")
                            except Exception:
                                pass  # Ignore individual file errors
                    except Exception:
                        pass  # Ignore pattern errors

            if cache_type in ["all", "python"]:
                # Clear Python cache
                try:
                    pycache_dirs = list(Path(self.working_directory).rglob("__pycache__"))
                    for cache_dir in pycache_dirs:
                        try:
                            shutil.rmtree(cache_dir)
                            cleared_items.append(f"Python cache: {cache_dir}")
                        except Exception as e:
                            errors.append(f"Python cache {cache_dir}: {str(e)}")
                except Exception as e:
                    errors.append(f"Python cache: {str(e)}")

            return {
                "success": len(errors) == 0,
                "cache_type": cache_type,
                "cleared_items": cleared_items,
                "errors": errors if errors else None,
                "timestamp": datetime.now().isoformat()
            }

        except Exception as e:
            return {"success": False, "error": f"Cache clearing failed: {str(e)}"}

    async def get_environment_variables(self, filter_pattern: str = None) -> dict[str, Any]:
        """Get environment variables, optionally filtered."""
        try:
            import re
            
            env_vars = dict(os.environ)
            
            if filter_pattern:
                try:
                    pattern = re.compile(filter_pattern, re.IGNORECASE)
                    env_vars = {k: v for k, v in env_vars.items() if pattern.search(k)}
                except re.error:
                    return {"success": False, "error": f"Invalid regex pattern: {filter_pattern}"}

            return {
                "success": True,
                "environment_variables": env_vars,
                "filter_pattern": filter_pattern,
                "count": len(env_vars)
            }

        except Exception as e:
            return {"success": False, "error": f"Failed to get environment variables: {str(e)}"}

    async def check_disk_space(self, path: str = None) -> dict[str, Any]:
        """Check disk space for a given path."""
        try:
            target_path = path or self.working_directory
            
            try:
                import psutil
                usage = psutil.disk_usage(target_path)
                
                return {
                    "success": True,
                    "path": target_path,
                    "total": usage.total,
                    "used": usage.used,
                    "free": usage.free,
                    "percent_used": (usage.used / usage.total) * 100,
                    "human_readable": {
                        "total": f"{usage.total / (1024**3):.2f} GB",
                        "used": f"{usage.used / (1024**3):.2f} GB",
                        "free": f"{usage.free / (1024**3):.2f} GB"
                    }
                }
            except ImportError:
                # Fallback using shutil
                total, used, free = shutil.disk_usage(target_path)
                return {
                    "success": True,
                    "path": target_path,
                    "total": total,
                    "used": used,
                    "free": free,
                    "percent_used": (used / total) * 100,
                    "human_readable": {
                        "total": f"{total / (1024**3):.2f} GB",
                        "used": f"{used / (1024**3):.2f} GB",
                        "free": f"{free / (1024**3):.2f} GB"
                    }
                }

        except Exception as e:
            return {"success": False, "error": f"Failed to check disk space: {str(e)}"}

    async def get_environment_variables(self, filter_pattern: str = None) -> dict[str, Any]:
        """Get environment variables, optionally filtered."""
        try:
            env_vars = dict(os.environ)
            
            if filter_pattern:
                import re
                pattern = re.compile(filter_pattern, re.IGNORECASE)
                env_vars = {k: v for k, v in env_vars.items() if pattern.search(k)}

            # Hide sensitive variables
            sensitive_patterns = ['password', 'secret', 'key', 'token', 'auth']
            for key in list(env_vars.keys()):
                if any(pattern in key.lower() for pattern in sensitive_patterns):
                    env_vars[key] = "***HIDDEN***"

            return {
                "success": True,
                "environment_variables": env_vars,
                "total_variables": len(env_vars),
                "filter_pattern": filter_pattern,
                "timestamp": datetime.now().isoformat()
            }

        except Exception as e:
            return {"success": False, "error": f"Failed to get environment variables: {str(e)}"}

    async def check_disk_space(self, path: str = None) -> dict[str, Any]:
        """Check disk space for a given path."""
        try:
            target_path = path or self.working_directory
            
            if not Path(target_path).exists():
                return {"success": False, "error": f"Path does not exist: {target_path}"}

            # Get disk usage
            total, used, free = shutil.disk_usage(target_path)
            
            return {
                "success": True,
                "path": target_path,
                "total_bytes": total,
                "used_bytes": used,
                "free_bytes": free,
                "total_gb": round(total / (1024**3), 2),
                "used_gb": round(used / (1024**3), 2),
                "free_gb": round(free / (1024**3), 2),
                "usage_percent": round((used / total) * 100, 2),
                "timestamp": datetime.now().isoformat()
            }

        except Exception as e:
            return {"success": False, "error": f"Failed to check disk space: {str(e)}"}

    async def list_processes(self, filter_name: str = None) -> dict[str, Any]:
        """List running processes, optionally filtered by name."""
        try:
            import psutil
            
            processes = []
            for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent']):
                try:
                    proc_info = proc.info
                    if filter_name and filter_name.lower() not in proc_info['name'].lower():
                        continue
                    processes.append(proc_info)
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue

            # Sort by CPU usage
            processes.sort(key=lambda x: x.get('cpu_percent', 0), reverse=True)

            return {
                "success": True,
                "processes": processes[:50],  # Limit to top 50
                "total_processes": len(processes),
                "filter_name": filter_name,
                "timestamp": datetime.now().isoformat()
            }

        except ImportError:
            return {"success": False, "error": "psutil not available for process listing"}
        except Exception as e:
            return {"success": False, "error": f"Failed to list processes: {str(e)}"} 