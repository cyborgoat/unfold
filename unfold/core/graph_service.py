"""
Graph RAG service using Neo4j for file relationship mapping and knowledge graph queries.
Provides intelligent understanding of project structure and inter-file relationships.
"""

import hashlib
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from neo4j import GraphDatabase, Session
from neo4j.exceptions import DatabaseError, ServiceUnavailable

from ..utils.config import ConfigManager


@dataclass
class FileNode:
    """Represents a file node in the knowledge graph."""
    id: str
    path: str
    name: str
    file_type: str
    size: int | None
    modified_time: float
    metadata: dict[str, Any]


@dataclass
class Relationship:
    """Represents a relationship between nodes."""
    source_id: str
    target_id: str
    relationship_type: str
    properties: dict[str, Any]


class GraphRAGService:
    """
    Graph RAG service for intelligent file relationship mapping.
    Uses Neo4j to store and query knowledge graphs about file relationships.
    """

    def __init__(self, config_manager: ConfigManager | None = None):
        self.config_manager = config_manager or ConfigManager()
        self.logger = logging.getLogger(__name__)

        # Neo4j configuration
        self.neo4j_uri = self.config_manager.get("graph_db.uri", "bolt://localhost:7687")
        self.neo4j_user = self.config_manager.get("graph_db.user", "neo4j")
        self.neo4j_password = self.config_manager.get("graph_db.password", "password")
        self.database_name = self.config_manager.get("graph_db.database", "unfold")

        # Initialize Neo4j driver
        self.driver = None
        self._connect_to_neo4j()
        self._setup_constraints_and_indexes()

    def _connect_to_neo4j(self):
        """Connect to Neo4j database."""
        try:
            self.driver = GraphDatabase.driver(
                self.neo4j_uri,
                auth=(self.neo4j_user, self.neo4j_password)
            )
            # Test connection
            with self.driver.session(database=self.database_name) as session:
                session.run("RETURN 1")
            self.logger.info(f"Connected to Neo4j at {self.neo4j_uri}")
        except ServiceUnavailable as e:
            self.logger.error(f"Failed to connect to Neo4j: {e}")
            raise

    def _setup_constraints_and_indexes(self):
        """Setup Neo4j constraints and indexes for performance."""
        constraints_and_indexes = [
            # Unique constraint on file path
            "CREATE CONSTRAINT file_path_unique IF NOT EXISTS FOR (f:File) REQUIRE f.path IS UNIQUE",
            # Index on filename for faster searches
            "CREATE INDEX file_name_index IF NOT EXISTS FOR (f:File) ON (f.name)",
            # Index on file type
            "CREATE INDEX file_type_index IF NOT EXISTS FOR (f:File) ON (f.file_type)",
            # Index on directory path
            "CREATE INDEX directory_path_index IF NOT EXISTS FOR (d:Directory) ON (d.path)",
            # Index on keywords
            "CREATE INDEX keyword_index IF NOT EXISTS FOR (k:Keyword) ON (k.word)",
        ]

        with self.driver.session(database=self.database_name) as session:
            for constraint in constraints_and_indexes:
                try:
                    session.run(constraint)
                except DatabaseError as e:
                    # Constraint/index might already exist
                    if "already exists" not in str(e):
                        self.logger.warning(f"Failed to create constraint/index: {e}")

    def _generate_file_id(self, file_path: str) -> str:
        """Generate unique file ID from path."""
        return hashlib.md5(file_path.encode()).hexdigest()

    def index_file_node(self, file_path: str, content: str | None = None, metadata: dict | None = None) -> bool:
        """
        Index a file as a node in the knowledge graph.
        
        Args:
            file_path: Path to the file
            content: Optional file content for relationship analysis
            metadata: Optional metadata about the file
            
        Returns:
            bool: Success status
        """
        try:
            path_obj = Path(file_path)
            if not path_obj.exists():
                return False

            file_stats = path_obj.stat()
            file_id = self._generate_file_id(file_path)

            # Create file node
            file_node = FileNode(
                id=file_id,
                path=str(path_obj.absolute()),
                name=path_obj.name,
                file_type=path_obj.suffix.lower() or "unknown",
                size=file_stats.st_size if path_obj.is_file() else None,
                modified_time=file_stats.st_mtime,
                metadata=metadata or {}
            )

            with self.driver.session(database=self.database_name) as session:
                # Create or update file node
                session.run("""
                    MERGE (f:File {id: $id})
                    SET f.path = $path,
                        f.name = $name,
                        f.file_type = $file_type,
                        f.size = $size,
                        f.modified_time = $modified_time,
                        f.metadata = $metadata,
                        f.updated_at = datetime()
                """, **file_node.__dict__)

                # Create directory hierarchy
                self._create_directory_hierarchy(session, path_obj)

                # Extract and create relationships if content is provided
                if content and self._is_code_file(file_path):
                    self._extract_code_relationships(session, file_id, file_path, content)

                # Extract keywords from filename and path
                self._extract_file_keywords(session, file_id, file_path)

            self.logger.info(f"Indexed file node: {file_path}")
            return True

        except Exception as e:
            self.logger.error(f"Error indexing file {file_path}: {e}")
            return False

    def _create_directory_hierarchy(self, session: Session, path_obj: Path):
        """Create directory hierarchy in the graph."""
        current_path = path_obj.parent
        directories = []

        # Build directory path from root to current
        while current_path != current_path.parent:
            directories.append(current_path)
            current_path = current_path.parent

        directories.reverse()

        # Create directory nodes and relationships
        for i, dir_path in enumerate(directories):
            dir_id = self._generate_file_id(str(dir_path))

            # Create directory node
            session.run("""
                MERGE (d:Directory {id: $id})
                SET d.path = $path,
                    d.name = $name,
                    d.updated_at = datetime()
            """,
                id=dir_id,
                path=str(dir_path.absolute()),
                name=dir_path.name
            )

            # Create parent-child relationships
            if i > 0:
                parent_id = self._generate_file_id(str(directories[i-1]))
                session.run("""
                    MATCH (parent:Directory {id: $parent_id})
                    MATCH (child:Directory {id: $child_id})
                    MERGE (parent)-[:CONTAINS]->(child)
                """, parent_id=parent_id, child_id=dir_id)

        # Connect file to its parent directory
        if directories:
            parent_dir_id = self._generate_file_id(str(path_obj.parent))
            file_id = self._generate_file_id(str(path_obj))

            session.run("""
                MATCH (dir:Directory {id: $dir_id})
                MATCH (file:File {id: $file_id})
                MERGE (dir)-[:CONTAINS]->(file)
            """, dir_id=parent_dir_id, file_id=file_id)

    def _is_code_file(self, file_path: str) -> bool:
        """Check if file is a code file for relationship extraction."""
        code_extensions = {'.py', '.js', '.ts', '.java', '.cpp', '.c', '.h', '.go', '.rs', '.php'}
        return Path(file_path).suffix.lower() in code_extensions

    def _extract_code_relationships(self, session: Session, file_id: str, file_path: str, content: str):
        """Extract relationships from code content."""
        try:
            # Extract imports/dependencies
            imports = self._extract_imports(file_path, content)

            for imported_module in imports:
                # Create module node
                module_id = hashlib.md5(imported_module.encode()).hexdigest()
                session.run("""
                    MERGE (m:Module {id: $id})
                    SET m.name = $name,
                        m.updated_at = datetime()
                """, id=module_id, name=imported_module)

                # Create IMPORTS relationship
                session.run("""
                    MATCH (f:File {id: $file_id})
                    MATCH (m:Module {id: $module_id})
                    MERGE (f)-[:IMPORTS]->(m)
                """, file_id=file_id, module_id=module_id)

            # Extract function/class definitions
            definitions = self._extract_definitions(file_path, content)

            for def_name, def_type in definitions:
                # Create definition node
                def_id = hashlib.md5(f"{file_path}:{def_name}".encode()).hexdigest()
                session.run(f"""
                    MERGE (d:{def_type} {{id: $id}})
                    SET d.name = $name,
                        d.file_path = $file_path,
                        d.updated_at = datetime()
                """, id=def_id, name=def_name, file_path=file_path)

                # Create DEFINES relationship
                session.run(f"""
                    MATCH (f:File {{id: $file_id}})
                    MATCH (d:{def_type} {{id: $def_id}})
                    MERGE (f)-[:DEFINES]->(d)
                """, file_id=file_id, def_id=def_id)

        except Exception as e:
            self.logger.error(f"Error extracting code relationships: {e}")

    def _extract_imports(self, file_path: str, content: str) -> list[str]:
        """Extract import statements from code."""
        imports = []
        lines = content.split('\n')

        for line in lines:
            line = line.strip()

            # Python imports
            if file_path.endswith('.py'):
                if line.startswith('import '):
                    imports.append(line.split('import ')[1].split(' as ')[0].split('.')[0])
                elif line.startswith('from '):
                    imports.append(line.split('from ')[1].split(' import ')[0])

            # JavaScript/TypeScript imports
            elif file_path.endswith(('.js', '.ts')):
                if 'import' in line and 'from' in line:
                    module = line.split("from ")[-1].strip().strip('"\'')
                    imports.append(module)

            # Java imports
            elif file_path.endswith('.java'):
                if line.startswith('import '):
                    imports.append(line.split('import ')[1].rstrip(';'))

        return imports

    def _extract_definitions(self, file_path: str, content: str) -> list[tuple[str, str]]:
        """Extract function and class definitions."""
        definitions = []
        lines = content.split('\n')

        for line in lines:
            line = line.strip()

            # Python definitions
            if file_path.endswith('.py'):
                if line.startswith('def '):
                    func_name = line.split('def ')[1].split('(')[0]
                    definitions.append((func_name, 'Function'))
                elif line.startswith('class '):
                    class_name = line.split('class ')[1].split('(')[0].split(':')[0]
                    definitions.append((class_name, 'Class'))

            # JavaScript/TypeScript definitions
            elif file_path.endswith(('.js', '.ts')):
                if 'function ' in line:
                    func_name = line.split('function ')[1].split('(')[0]
                    definitions.append((func_name, 'Function'))
                elif 'class ' in line:
                    class_name = line.split('class ')[1].split(' ')[0].split('{')[0]
                    definitions.append((class_name, 'Class'))

        return definitions

    def _extract_file_keywords(self, session: Session, file_id: str, file_path: str):
        """Extract keywords from filename and path."""
        path_obj = Path(file_path)

        # Extract words from filename
        words = set()
        filename_words = path_obj.stem.replace('_', ' ').replace('-', ' ').split()
        words.update(word.lower() for word in filename_words if len(word) > 2)

        # Extract words from directory names
        for part in path_obj.parts[:-1]:
            dir_words = part.replace('_', ' ').replace('-', ' ').split()
            words.update(word.lower() for word in dir_words if len(word) > 2)

        # Create keyword nodes and relationships
        for word in words:
            keyword_id = hashlib.md5(word.encode()).hexdigest()

            session.run("""
                MERGE (k:Keyword {id: $id})
                SET k.word = $word,
                    k.updated_at = datetime()
            """, id=keyword_id, word=word)

            session.run("""
                MATCH (f:File {id: $file_id})
                MATCH (k:Keyword {id: $keyword_id})
                MERGE (f)-[:HAS_KEYWORD]->(k)
            """, file_id=file_id, keyword_id=keyword_id)

    def query_knowledge_graph(self, query: str, limit: int = 10) -> list[dict[str, Any]]:
        """
        Query the knowledge graph for file relationships and information.
        
        Args:
            query: Natural language query
            limit: Maximum number of results
            
        Returns:
            List of query results with file information
        """
        try:
            # Convert natural language query to graph query
            cypher_query = self._generate_cypher_query(query, limit)

            with self.driver.session(database=self.database_name) as session:
                result = session.run(cypher_query)

                results = []
                for record in result:
                    results.append(dict(record))

                return results

        except Exception as e:
            self.logger.error(f"Error querying knowledge graph: {e}")
            return []

    def _generate_cypher_query(self, query: str, limit: int) -> str:
        """Generate Cypher query from natural language query."""
        query_lower = query.lower()

        # Common query patterns
        if "files in" in query_lower:
            # Find files in a directory
            directory = query_lower.split("files in")[-1].strip()
            return f"""
                MATCH (d:Directory)-[:CONTAINS]->(f:File)
                WHERE d.name CONTAINS '{directory}' OR d.path CONTAINS '{directory}'
                RETURN f.name, f.path, f.file_type, f.size
                ORDER BY f.modified_time DESC
                LIMIT {limit}
            """

        elif "imports" in query_lower:
            # Find import relationships
            return f"""
                MATCH (f:File)-[:IMPORTS]->(m:Module)
                WHERE f.name CONTAINS '{query_lower.replace("imports", "").strip()}'
                RETURN f.name, f.path, collect(m.name) as imports
                LIMIT {limit}
            """

        elif "classes" in query_lower or "functions" in query_lower:
            # Find class or function definitions
            return f"""
                MATCH (f:File)-[:DEFINES]->(d)
                WHERE f.name CONTAINS '{query_lower.replace("classes", "").replace("functions", "").strip()}'
                RETURN f.name, f.path, labels(d) as definition_type, d.name as definition_name
                LIMIT {limit}
            """

        elif "similar" in query_lower:
            # Find similar files by keywords
            keywords = [word for word in query_lower.split() if len(word) > 2]
            keyword_conditions = " OR ".join([f"k.word CONTAINS '{word}'" for word in keywords])
            return f"""
                MATCH (f:File)-[:HAS_KEYWORD]->(k:Keyword)
                WHERE {keyword_conditions}
                WITH f, count(k) as keyword_matches
                ORDER BY keyword_matches DESC
                RETURN f.name, f.path, f.file_type, keyword_matches
                LIMIT {limit}
            """

        else:
            # General file search
            return f"""
                MATCH (f:File)
                WHERE f.name CONTAINS '{query}' OR f.path CONTAINS '{query}'
                RETURN f.name, f.path, f.file_type, f.size
                ORDER BY f.modified_time DESC
                LIMIT {limit}
            """

    def get_file_relationships(self, file_path: str) -> dict[str, list[dict]]:
        """Get all relationships for a specific file."""
        try:
            file_id = self._generate_file_id(file_path)

            with self.driver.session(database=self.database_name) as session:
                # Get imports
                imports_result = session.run("""
                    MATCH (f:File {id: $file_id})-[:IMPORTS]->(m:Module)
                    RETURN m.name as module_name
                """, file_id=file_id)

                imports = [record["module_name"] for record in imports_result]

                # Get definitions
                definitions_result = session.run("""
                    MATCH (f:File {id: $file_id})-[:DEFINES]->(d)
                    RETURN labels(d) as type, d.name as name
                """, file_id=file_id)

                definitions = [{"type": record["type"][0], "name": record["name"]} for record in definitions_result]

                # Get keywords
                keywords_result = session.run("""
                    MATCH (f:File {id: $file_id})-[:HAS_KEYWORD]->(k:Keyword)
                    RETURN k.word as keyword
                """, file_id=file_id)

                keywords = [record["keyword"] for record in keywords_result]

                return {
                    "imports": imports,
                    "definitions": definitions,
                    "keywords": keywords
                }

        except Exception as e:
            self.logger.error(f"Error getting file relationships: {e}")
            return {"imports": [], "definitions": [], "keywords": []}

    def get_project_structure(self) -> dict[str, Any]:
        """Get an overview of the project structure."""
        try:
            with self.driver.session(database=self.database_name) as session:
                # Get file count by type
                file_types_result = session.run("""
                    MATCH (f:File)
                    RETURN f.file_type as file_type, count(f) as count
                    ORDER BY count DESC
                """)

                file_types = {record["file_type"]: record["count"] for record in file_types_result}

                # Get directory structure
                directories_result = session.run("""
                    MATCH (d:Directory)
                    OPTIONAL MATCH (d)-[:CONTAINS]->(f:File)
                    RETURN d.name as directory, count(f) as file_count
                    ORDER BY file_count DESC
                    LIMIT 20
                """)

                directories = [{"name": record["directory"], "file_count": record["file_count"]} for record in directories_result]

                # Get most imported modules
                imports_result = session.run("""
                    MATCH (f:File)-[:IMPORTS]->(m:Module)
                    RETURN m.name as module, count(f) as import_count
                    ORDER BY import_count DESC
                    LIMIT 10
                """)

                top_imports = [{"module": record["module"], "count": record["import_count"]} for record in imports_result]

                return {
                    "file_types": file_types,
                    "directories": directories,
                    "top_imports": top_imports
                }

        except Exception as e:
            self.logger.error(f"Error getting project structure: {e}")
            return {}

    def remove_file_node(self, file_path: str) -> bool:
        """Remove a file node and its relationships from the graph."""
        try:
            file_id = self._generate_file_id(file_path)

            with self.driver.session(database=self.database_name) as session:
                session.run("""
                    MATCH (f:File {id: $file_id})
                    DETACH DELETE f
                """, file_id=file_id)

            return True

        except Exception as e:
            self.logger.error(f"Error removing file node: {e}")
            return False

    def health_check(self) -> bool:
        """Check if graph database is healthy."""
        try:
            with self.driver.session(database=self.database_name) as session:
                session.run("RETURN 1")
            return True
        except Exception:
            return False

    def get_graph_stats(self) -> dict[str, Any]:
        """Get statistics about the knowledge graph."""
        try:
            with self.driver.session(database=self.database_name) as session:
                result = session.run("""
                    MATCH (f:File) 
                    OPTIONAL MATCH (d:Directory)
                    OPTIONAL MATCH (m:Module)
                    OPTIONAL MATCH (k:Keyword)
                    RETURN count(f) as files, count(d) as directories, 
                           count(m) as modules, count(k) as keywords
                """)

                stats = dict(result.single())
                return stats

        except Exception as e:
            self.logger.error(f"Error getting graph stats: {e}")
            return {}

    def close(self):
        """Close Neo4j connection."""
        if self.driver:
            self.driver.close()
