"""
Lightweight Graph Service using NetworkX as an alternative to Neo4j.
Provides basic graph analysis and relationship tracking for file systems.
"""

import ast
import json
import logging
import re
from datetime import datetime
from pathlib import Path
from typing import Any

import networkx as nx

from ..utils.config import ConfigManager


class NetworkXGraphService:
    """
    Lightweight graph service using NetworkX for file relationship analysis.
    Alternative to Neo4j that doesn't require external database installation.
    """

    def __init__(self, config_manager: ConfigManager | None = None):
        self.config_manager = config_manager or ConfigManager()
        self.logger = logging.getLogger(__name__)

        # Initialize NetworkX graph
        self.graph = nx.DiGraph()  # Directed graph for file relationships

        # Graph storage path
        self.graph_path = Path(self.config_manager.get("indexing.knowledge_base_path", "./knowledge")) / "graph"
        self.graph_path.mkdir(parents=True, exist_ok=True)
        self.graph_file = self.graph_path / "file_relationships.json"

        # Load existing graph if available
        self._load_graph()

        self.logger.info("NetworkX Graph Service initialized")

    def _load_graph(self):
        """Load graph from storage."""
        try:
            if self.graph_file.exists():
                with open(self.graph_file) as f:
                    data = json.load(f)

                # Rebuild graph from stored data
                for node_data in data.get('nodes', []):
                    self.graph.add_node(node_data['id'], **node_data['attributes'])

                for edge_data in data.get('edges', []):
                    self.graph.add_edge(
                        edge_data['source'],
                        edge_data['target'],
                        **edge_data['attributes']
                    )

                self.logger.info(f"Loaded graph with {self.graph.number_of_nodes()} nodes and {self.graph.number_of_edges()} edges")
        except Exception as e:
            self.logger.warning(f"Could not load existing graph: {e}")

    def _save_graph(self):
        """Save graph to storage."""
        try:
            data = {
                'nodes': [
                    {'id': node, 'attributes': attrs}
                    for node, attrs in self.graph.nodes(data=True)
                ],
                'edges': [
                    {'source': source, 'target': target, 'attributes': attrs}
                    for source, target, attrs in self.graph.edges(data=True)
                ]
            }

            with open(self.graph_file, 'w') as f:
                json.dump(data, f, indent=2, default=str)

        except Exception as e:
            self.logger.error(f"Error saving graph: {e}")

    def index_file(self, file_path: str, content: str | None = None) -> bool:
        """
        Index a file and its relationships in the graph.
        
        Args:
            file_path: Path to the file
            content: Optional file content for analysis
            
        Returns:
            bool: Success status
        """
        try:
            path_obj = Path(file_path)
            if not path_obj.exists():
                return False

            # Add file node
            node_id = str(path_obj.absolute())
            file_attrs = {
                'type': 'file' if path_obj.is_file() else 'directory',
                'name': path_obj.name,
                'extension': path_obj.suffix.lower() if path_obj.is_file() else None,
                'size': path_obj.stat().st_size if path_obj.is_file() else None,
                'modified_time': path_obj.stat().st_mtime,
                'indexed_time': datetime.now().timestamp()
            }

            self.graph.add_node(node_id, **file_attrs)

            # Add directory relationship
            if path_obj.parent != path_obj:
                parent_id = str(path_obj.parent.absolute())
                self.graph.add_edge(parent_id, node_id, relationship='contains')

            # Analyze file content for relationships (if provided)
            if content and path_obj.is_file():
                self._analyze_file_content(node_id, content, path_obj)

            return True

        except Exception as e:
            self.logger.error(f"Error indexing file {file_path}: {e}")
            return False

    def _analyze_file_content(self, file_id: str, content: str, path_obj: Path):
        """Analyze file content to extract relationships."""
        try:
            if path_obj.suffix.lower() == '.py':
                self._analyze_python_file(file_id, content, path_obj)
            elif path_obj.suffix.lower() in ['.js', '.ts']:
                self._analyze_javascript_file(file_id, content, path_obj)
            elif path_obj.suffix.lower() in ['.md', '.txt', '.rst']:
                self._analyze_text_file(file_id, content, path_obj)

        except Exception as e:
            self.logger.error(f"Error analyzing content for {file_id}: {e}")

    def _analyze_python_file(self, file_id: str, content: str, path_obj: Path):
        """Analyze Python file for imports and relationships."""
        try:
            tree = ast.parse(content)

            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        self._add_import_relationship(file_id, alias.name, 'import')

                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        self._add_import_relationship(file_id, node.module, 'from_import')

                elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    self._add_function_node(file_id, node.name, 'function')

                elif isinstance(node, ast.ClassDef):
                    self._add_function_node(file_id, node.name, 'class')

        except Exception as e:
            self.logger.debug(f"Could not parse Python file {file_id}: {e}")

    def _analyze_javascript_file(self, file_id: str, content: str, path_obj: Path):
        """Analyze JavaScript/TypeScript file for imports."""
        # Simple regex-based analysis for imports
        import_patterns = [
            r'import\s+.*\s+from\s+[\'"]([^\'"]+)[\'"]',
            r'require\([\'"]([^\'"]+)[\'"]\)',
            r'import\([\'"]([^\'"]+)[\'"]\)'
        ]

        for pattern in import_patterns:
            matches = re.findall(pattern, content)
            for match in matches:
                self._add_import_relationship(file_id, match, 'import')

    def _analyze_text_file(self, file_id: str, content: str, path_obj: Path):
        """Analyze text files for references to other files."""
        # Look for file references in markdown/text
        file_ref_pattern = r'(?:\.\/|\.\.\/|\/)?([a-zA-Z0-9_\-\/\.]+\.[a-zA-Z0-9]+)'
        matches = re.findall(file_ref_pattern, content)

        for match in matches:
            if len(match) > 3:  # Filter out very short matches
                self._add_reference_relationship(file_id, match, 'references')

    def _add_import_relationship(self, file_id: str, module_name: str, relationship_type: str):
        """Add import relationship to graph."""
        # Create module node
        module_id = f"module:{module_name}"
        self.graph.add_node(module_id, type='module', name=module_name)
        self.graph.add_edge(file_id, module_id, relationship=relationship_type)

    def _add_function_node(self, file_id: str, function_name: str, function_type: str):
        """Add function/class node to graph."""
        func_id = f"{file_id}:{function_name}"
        self.graph.add_node(func_id, type=function_type, name=function_name)
        self.graph.add_edge(file_id, func_id, relationship='defines')

    def _add_reference_relationship(self, file_id: str, referenced_file: str, relationship_type: str):
        """Add file reference relationship."""
        ref_id = f"ref:{referenced_file}"
        self.graph.add_node(ref_id, type='reference', name=referenced_file)
        self.graph.add_edge(file_id, ref_id, relationship=relationship_type)

    def query_knowledge_graph(self, query: str, limit: int = 10) -> list[dict[str, Any]]:
        """
        Query the knowledge graph with natural language.
        
        Args:
            query: Natural language query
            limit: Maximum results to return
            
        Returns:
            List of query results
        """
        try:
            query_lower = query.lower()
            results = []

            # Simple keyword-based querying
            if 'import' in query_lower or 'dependency' in query_lower:
                results = self._find_import_relationships(limit)
            elif 'function' in query_lower or 'class' in query_lower:
                results = self._find_code_elements(limit)
            elif 'file' in query_lower and 'connect' in query_lower:
                results = self._find_connected_files(limit)
            elif 'structure' in query_lower or 'hierarchy' in query_lower:
                results = self._get_project_structure(limit)
            else:
                # General search in node names
                results = self._search_nodes(query, limit)

            return results[:limit]

        except Exception as e:
            self.logger.error(f"Error querying knowledge graph: {e}")
            return []

    def _find_import_relationships(self, limit: int) -> list[dict[str, Any]]:
        """Find import relationships in the graph."""
        results = []
        for source, target, data in self.graph.edges(data=True):
            if data.get('relationship') in ['import', 'from_import']:
                source_attrs = self.graph.nodes.get(source, {})
                target_attrs = self.graph.nodes.get(target, {})
                results.append({
                    'type': 'import_relationship',
                    'source': source,
                    'target': target,
                    'source_name': source_attrs.get('name', source),
                    'target_name': target_attrs.get('name', target),
                    'relationship': data.get('relationship')
                })
        return results

    def _find_code_elements(self, limit: int) -> list[dict[str, Any]]:
        """Find functions and classes in the graph."""
        results = []
        for node, attrs in self.graph.nodes(data=True):
            if attrs.get('type') in ['function', 'class']:
                results.append({
                    'type': 'code_element',
                    'id': node,
                    'name': attrs.get('name'),
                    'element_type': attrs.get('type'),
                    'file': node.split(':')[0] if ':' in node else None
                })
        return results

    def _find_connected_files(self, limit: int) -> list[dict[str, Any]]:
        """Find files that are connected through relationships."""
        results = []
        file_nodes = [n for n, attrs in self.graph.nodes(data=True) if attrs.get('type') == 'file']

        for file_node in file_nodes[:limit]:
            connections = list(self.graph.neighbors(file_node))
            if connections:
                file_attrs = self.graph.nodes.get(file_node, {})
                results.append({
                    'type': 'connected_file',
                    'file': file_node,
                    'name': file_attrs.get('name'),
                    'connections': len(connections),
                    'connected_to': [self.graph.nodes.get(c, {}).get('name', c) for c in connections[:5]]
                })
        return results

    def _get_project_structure(self, limit: int) -> list[dict[str, Any]]:
        """Get project structure information."""
        results = []
        dir_nodes = [n for n, attrs in self.graph.nodes(data=True) if attrs.get('type') == 'directory']

        for dir_node in dir_nodes[:limit]:
            children = [t for s, t in self.graph.edges() if s == dir_node]
            dir_attrs = self.graph.nodes.get(dir_node, {})
            results.append({
                'type': 'directory_structure',
                'directory': dir_node,
                'name': dir_attrs.get('name'),
                'children_count': len(children),
                'children': [self.graph.nodes.get(c, {}).get('name', c) for c in children[:10]]
            })
        return results

    def _search_nodes(self, query: str, limit: int) -> list[dict[str, Any]]:
        """Search nodes by name."""
        results = []
        query_lower = query.lower()

        for node, attrs in self.graph.nodes(data=True):
            name = attrs.get('name', '')
            if query_lower in name.lower():
                results.append({
                    'type': 'search_result',
                    'id': node,
                    'name': name,
                    'node_type': attrs.get('type'),
                    'score': 1.0  # Simple scoring
                })
        return results

    def get_file_relationships(self, file_path: str) -> dict[str, Any]:
        """Get relationships for a specific file."""
        try:
            file_id = str(Path(file_path).absolute())
            if file_id not in self.graph:
                return {'error': f'File not found in graph: {file_path}'}

            # Get all relationships
            imports = []
            functions = []
            references = []

            for neighbor in self.graph.neighbors(file_id):
                edge_data = self.graph.get_edge_data(file_id, neighbor)
                neighbor_attrs = self.graph.nodes.get(neighbor, {})

                relationship = edge_data.get('relationship', 'unknown')

                if relationship in ['import', 'from_import']:
                    imports.append({
                        'name': neighbor_attrs.get('name'),
                        'type': relationship
                    })
                elif relationship == 'defines':
                    functions.append({
                        'name': neighbor_attrs.get('name'),
                        'type': neighbor_attrs.get('type')
                    })
                elif relationship == 'references':
                    references.append({
                        'name': neighbor_attrs.get('name')
                    })

            return {
                'file_path': file_path,
                'imports': imports,
                'functions': functions,
                'references': references,
                'total_connections': len(list(self.graph.neighbors(file_id)))
            }

        except Exception as e:
            self.logger.error(f"Error getting file relationships: {e}")
            return {'error': str(e)}

    def health_check(self) -> bool:
        """Check if the graph service is healthy."""
        try:
            # Simple health check - can we access the graph?
            node_count = self.graph.number_of_nodes()
            return True
        except Exception:
            return False

    def get_stats(self) -> dict[str, Any]:
        """Get graph statistics."""
        try:
            stats = {
                'nodes': self.graph.number_of_nodes(),
                'edges': self.graph.number_of_edges(),
                'files': len([n for n, attrs in self.graph.nodes(data=True) if attrs.get('type') == 'file']),
                'directories': len([n for n, attrs in self.graph.nodes(data=True) if attrs.get('type') == 'directory']),
                'modules': len([n for n, attrs in self.graph.nodes(data=True) if attrs.get('type') == 'module']),
                'functions': len([n for n, attrs in self.graph.nodes(data=True) if attrs.get('type') in ['function', 'class']])
            }
            return stats
        except Exception as e:
            self.logger.error(f"Error getting stats: {e}")
            return {}

    def close(self):
        """Save and close the graph service."""
        try:
            self._save_graph()
            self.logger.info("Graph service closed and saved")
        except Exception as e:
            self.logger.error(f"Error closing graph service: {e}")
