"""
AI-powered analysis tools for MCP integration.
"""

import os
from datetime import datetime
from pathlib import Path
from typing import Any


class AnalysisTools:
    """Tools for AI-powered file and project analysis."""

    def __init__(self, working_directory: str = None, llm_service=None):
        """Initialize analysis tools."""
        self.working_directory = working_directory or os.getcwd()
        self.llm_service = llm_service

    async def analyze_file_content(self, file_path: str) -> dict[str, Any]:
        """Analyze file content using AI."""
        try:
            if not self.llm_service:
                return {"success": False, "error": "LLM service not available"}

            path = Path(file_path)
            if not path.exists():
                return {"success": False, "error": f"File does not exist: {file_path}"}

            if not path.is_file():
                return {"success": False, "error": f"Path is not a file: {file_path}"}

            # Read file content
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    content = f.read()
            except UnicodeDecodeError:
                return {"success": False, "error": "File is not text-readable (binary file)"}

            # Analyze with LLM
            prompt = f"""Analyze this file and provide insights:

File: {file_path}
Content:
{content}

Please provide:
1. File type and purpose
2. Key components/functions
3. Dependencies or imports
4. Potential issues or improvements
5. Summary of functionality

Keep the analysis concise and actionable.
"""

            analysis = await self.llm_service.chat_streaming(prompt, "", [])
            analysis_text = "".join([chunk async for chunk in analysis])

            return {
                "success": True,
                "file_path": file_path,
                "analysis": analysis_text,
                "file_size": len(content),
                "lines": len(content.splitlines()),
                "timestamp": datetime.now().isoformat()
            }

        except Exception as e:
            return {"success": False, "error": f"Analysis failed: {str(e)}"}

    async def suggest_file_improvements(self, file_path: str) -> dict[str, Any]:
        """Suggest improvements for a file using AI."""
        try:
            if not self.llm_service:
                return {"success": False, "error": "LLM service not available"}

            path = Path(file_path)
            if not path.exists():
                return {"success": False, "error": f"File does not exist: {file_path}"}

            # Read file content
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    content = f.read()
            except UnicodeDecodeError:
                return {"success": False, "error": "File is not text-readable (binary file)"}

            # Get improvement suggestions
            prompt = f"""Review this code file and suggest specific improvements:

File: {file_path}
Content:
{content}

Please provide:
1. Code quality improvements
2. Performance optimizations
3. Security considerations
4. Best practices to follow
5. Refactoring suggestions

Format as actionable recommendations with specific examples where possible.
"""

            suggestions = await self.llm_service.chat_streaming(prompt, "", [])
            suggestions_text = "".join([chunk async for chunk in suggestions])

            return {
                "success": True,
                "file_path": file_path,
                "suggestions": suggestions_text,
                "timestamp": datetime.now().isoformat()
            }

        except Exception as e:
            return {"success": False, "error": f"Suggestion generation failed: {str(e)}"}

    async def analyze_project_structure(self, directory: str = None) -> dict[str, Any]:
        """Analyze overall project structure and provide insights."""
        try:
            target_dir = directory or self.working_directory
            target_path = Path(target_dir)

            if not target_path.exists():
                return {"success": False, "error": f"Directory does not exist: {target_dir}"}

            # Collect directory information
            items = []
            for item in target_path.rglob("*"):
                try:
                    stat = item.stat()
                    items.append({
                        "name": item.name,
                        "path": str(item.relative_to(target_path)),
                        "type": "directory" if item.is_dir() else "file",
                        "size": stat.st_size if item.is_file() else None,
                        "extension": item.suffix if item.is_file() else None
                    })
                except (OSError, PermissionError):
                    continue

            # Analyze file types and structure
            file_types = {}
            directories = []
            total_size = 0

            for item in items:
                if item["type"] == "directory":
                    directories.append(item["name"])
                else:
                    ext = item["extension"] or "no_extension"
                    file_types[ext] = file_types.get(ext, 0) + 1
                    if item["size"]:
                        total_size += item["size"]

            # Detect project type
            project_type = "unknown"
            config_files = [item["name"] for item in items if item["type"] == "file"]
            
            if any(f in config_files for f in ["package.json", "yarn.lock", "package-lock.json"]):
                project_type = "nodejs"
            elif any(f in config_files for f in ["requirements.txt", "pyproject.toml", "setup.py", "Pipfile"]):
                project_type = "python"
            elif any(f in config_files for f in ["pom.xml", "build.gradle", "build.xml"]):
                project_type = "java"
            elif any(f in config_files for f in ["Cargo.toml", "Cargo.lock"]):
                project_type = "rust"
            elif any(f in config_files for f in ["go.mod", "go.sum"]):
                project_type = "go"
            elif any(f in config_files for f in ["composer.json", "composer.lock"]):
                project_type = "php"

            # AI analysis if available
            ai_analysis = None
            if self.llm_service:
                try:
                    summary = f"""Project Analysis:
Directory: {target_dir}
Project Type: {project_type}
Total Files: {len([i for i in items if i["type"] == "file"])}
Total Directories: {len(directories)}
File Types: {dict(list(file_types.items())[:10])}
Main Directories: {directories[:10]}
Total Size: {total_size} bytes

Please provide insights about:
1. Project organization and structure
2. Potential improvements
3. Missing best practices
4. Recommended tools or configurations
5. Code quality observations
"""

                    analysis = await self.llm_service.chat_streaming(summary, "", [])
                    ai_analysis = "".join([chunk async for chunk in analysis])
                except Exception as e:
                    ai_analysis = f"AI analysis failed: {str(e)}"

            return {
                "success": True,
                "directory": target_dir,
                "project_type": project_type,
                "total_files": len([i for i in items if i["type"] == "file"]),
                "total_directories": len(directories),
                "total_size": total_size,
                "file_types": file_types,
                "main_directories": directories[:10],
                "ai_analysis": ai_analysis,
                "analysis_timestamp": datetime.now().isoformat()
            }

        except Exception as e:
            return {"success": False, "error": f"Project analysis failed: {str(e)}"}

    async def detect_code_patterns(self, directory: str = None, file_extensions: list[str] = None) -> dict[str, Any]:
        """Detect common code patterns and anti-patterns in the project."""
        try:
            if not self.llm_service:
                return {"success": False, "error": "LLM service not available"}

            target_dir = directory or self.working_directory
            target_path = Path(target_dir)

            if not target_path.exists():
                return {"success": False, "error": f"Directory does not exist: {target_dir}"}

            # Default extensions for code analysis
            if not file_extensions:
                file_extensions = ['.py', '.js', '.ts', '.java', '.cpp', '.c', '.rs', '.go', '.php']

            # Collect code files
            code_files = []
            for ext in file_extensions:
                code_files.extend(target_path.rglob(f"*{ext}"))

            if not code_files:
                return {"success": False, "error": "No code files found"}

            # Sample a few files for analysis
            sample_files = code_files[:5]  # Analyze first 5 files
            
            file_contents = []
            for file_path in sample_files:
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                        file_contents.append({
                            "path": str(file_path.relative_to(target_path)),
                            "content": content[:2000]  # First 2000 chars
                        })
                except (UnicodeDecodeError, PermissionError):
                    continue

            if not file_contents:
                return {"success": False, "error": "Could not read any code files"}

            # AI analysis
            prompt = f"""Analyze these code files for patterns and quality:

Project Directory: {target_dir}
Files Analyzed: {len(file_contents)}

Files:
"""
            for file_info in file_contents:
                prompt += f"\n--- {file_info['path']} ---\n{file_info['content']}\n"

            prompt += """
Please identify:
1. Common design patterns used
2. Code quality issues
3. Anti-patterns or code smells
4. Consistency in coding style
5. Architecture insights
6. Recommendations for improvement
"""

            analysis = await self.llm_service.chat_streaming(prompt, "", [])
            analysis_text = "".join([chunk async for chunk in analysis])

            return {
                "success": True,
                "directory": target_dir,
                "files_analyzed": len(file_contents),
                "total_code_files": len(code_files),
                "file_extensions": file_extensions,
                "pattern_analysis": analysis_text,
                "timestamp": datetime.now().isoformat()
            }

        except Exception as e:
            return {"success": False, "error": f"Pattern detection failed: {str(e)}"} 