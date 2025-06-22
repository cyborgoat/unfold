"""
Vector Database service using Milvus for file content indexing and memory management.
Supports file content embeddings, short-term memory, and long-term memory storage.
"""

import hashlib
import json
import logging
import os
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from pymilvus import (
    Collection,
    CollectionSchema,
    DataType,
    FieldSchema,
    MilvusClient,
    MilvusException,
    connections,
    utility,
)
from sentence_transformers import SentenceTransformer

from ..utils.config import ConfigManager


@dataclass
class DocumentChunk:
    """Represents a document chunk for vector storage."""
    id: str
    content: str
    file_path: str
    chunk_index: int
    metadata: dict[str, Any]
    timestamp: float
    embedding: list[float] | None = None


@dataclass
class MemoryEntry:
    """Represents a memory entry for conversation context."""
    id: str
    content: str
    memory_type: str  # 'short_term' or 'long_term'
    importance_score: float
    timestamp: float
    metadata: dict[str, Any]
    embedding: list[float] | None = None


class VectorDBService:
    """
    Vector Database service for file content and memory management.
    Uses Milvus for vector storage and Sentence-Transformers for embeddings.
    """

    def __init__(self, config_manager: ConfigManager | None = None):
        self.config_manager = config_manager or ConfigManager()
        self.logger = logging.getLogger(__name__)

        # Initialize embedding model
        embedding_model_name = self.config_manager.get("vector_db.embedding_model", "all-MiniLM-L6-v2")
        self.embedding_model = SentenceTransformer(embedding_model_name)
        self.embedding_dim = self.embedding_model.get_sentence_embedding_dimension()

        # Check if using Milvus Lite
        self.use_milvus_lite = self.config_manager.get("vector_db.use_milvus_lite", False)

        if self.use_milvus_lite:
            # Milvus Lite configuration
            self.db_path = self.config_manager.get("vector_db.local_db_path", "./knowledge/vector.db")
            # Ensure directory exists
            os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
            self.client = MilvusClient(self.db_path)
            self.logger.info(f"Using Milvus Lite with database at {self.db_path}")
        else:
            # Regular Milvus configuration
            self.milvus_host = self.config_manager.get("vector_db.host", "localhost")
            self.milvus_port = self.config_manager.get("vector_db.port", "19530")
            self.connection_alias = "unfold_connection"
            # Initialize connections and collections
            self._connect_to_milvus()

        # Collection names
        self.files_collection_name = "file_contents"
        self.memory_collection_name = "conversation_memory"

        # Setup collections
        self._setup_collections()

    def _connect_to_milvus(self):
        """Connect to Milvus server."""
        try:
            connections.connect(
                alias=self.connection_alias,
                host=self.milvus_host,
                port=self.milvus_port
            )
            self.logger.info(f"Connected to Milvus at {self.milvus_host}:{self.milvus_port}")
        except MilvusException as e:
            self.logger.error(f"Failed to connect to Milvus: {e}")
            raise

    def _setup_collections(self):
        """Setup Milvus collections for files and memory."""
        if self.use_milvus_lite:
            self._create_collections_lite()
        else:
            self._create_files_collection()
            self._create_memory_collection()

    def _create_collections_lite(self):
        """Create collections for Milvus Lite."""
        # Check if collections exist
        collections = self.client.list_collections()

        if self.files_collection_name not in collections:
            # For Milvus Lite, we need to use auto-generated integer IDs
            # Create schema with proper field definitions
            from pymilvus import CollectionSchema, DataType, FieldSchema

            fields = [
                FieldSchema(name="id", dtype=DataType.INT64, is_primary=True, auto_id=True),
                FieldSchema(name="doc_id", dtype=DataType.VARCHAR, max_length=256),  # Our string ID
                FieldSchema(name="content", dtype=DataType.VARCHAR, max_length=8192),
                FieldSchema(name="file_path", dtype=DataType.VARCHAR, max_length=1024),
                FieldSchema(name="chunk_index", dtype=DataType.INT64),
                FieldSchema(name="metadata", dtype=DataType.VARCHAR, max_length=2048),
                FieldSchema(name="timestamp", dtype=DataType.DOUBLE),
                FieldSchema(name="vector", dtype=DataType.FLOAT_VECTOR, dim=self.embedding_dim)
            ]

            schema = CollectionSchema(fields, "File content embeddings for semantic search")
            self.client.create_collection(
                collection_name=self.files_collection_name,
                schema=schema
            )
            self.logger.info("Created files collection in Milvus Lite")

        if self.memory_collection_name not in collections:
            # Create memory collection with proper schema
            fields = [
                FieldSchema(name="id", dtype=DataType.INT64, is_primary=True, auto_id=True),
                FieldSchema(name="mem_id", dtype=DataType.VARCHAR, max_length=256),  # Our string ID
                FieldSchema(name="content", dtype=DataType.VARCHAR, max_length=8192),
                FieldSchema(name="memory_type", dtype=DataType.VARCHAR, max_length=32),
                FieldSchema(name="importance_score", dtype=DataType.DOUBLE),
                FieldSchema(name="timestamp", dtype=DataType.DOUBLE),
                FieldSchema(name="metadata", dtype=DataType.VARCHAR, max_length=2048),
                FieldSchema(name="vector", dtype=DataType.FLOAT_VECTOR, dim=self.embedding_dim)
            ]

            schema = CollectionSchema(fields, "Conversation memory embeddings")
            self.client.create_collection(
                collection_name=self.memory_collection_name,
                schema=schema
            )
            self.logger.info("Created memory collection in Milvus Lite")

    def _create_files_collection(self):
        """Create collection for file content vectors."""
        if utility.has_collection(self.files_collection_name, using=self.connection_alias):
            self.files_collection = Collection(self.files_collection_name, using=self.connection_alias)
            return

        # Define schema for file contents
        fields = [
            FieldSchema(name="id", dtype=DataType.VARCHAR, max_length=256, is_primary=True),
            FieldSchema(name="content", dtype=DataType.VARCHAR, max_length=8192),
            FieldSchema(name="file_path", dtype=DataType.VARCHAR, max_length=1024),
            FieldSchema(name="chunk_index", dtype=DataType.INT64),
            FieldSchema(name="metadata", dtype=DataType.VARCHAR, max_length=2048),
            FieldSchema(name="timestamp", dtype=DataType.DOUBLE),
            FieldSchema(name="embedding", dtype=DataType.FLOAT_VECTOR, dim=self.embedding_dim)
        ]

        schema = CollectionSchema(fields, "File content embeddings for semantic search")
        self.files_collection = Collection(self.files_collection_name, schema, using=self.connection_alias)

        # Create index for vector field
        index_params = {
            "index_type": "IVF_FLAT",
            "metric_type": "COSINE",
            "params": {"nlist": 1024}
        }
        self.files_collection.create_index("embedding", index_params)
        self.logger.info("Created files collection with vector index")

    def _create_memory_collection(self):
        """Create collection for conversation memory."""
        if utility.has_collection(self.memory_collection_name, using=self.connection_alias):
            self.memory_collection = Collection(self.memory_collection_name, using=self.connection_alias)
            return

        # Define schema for memory
        fields = [
            FieldSchema(name="id", dtype=DataType.VARCHAR, max_length=256, is_primary=True),
            FieldSchema(name="content", dtype=DataType.VARCHAR, max_length=8192),
            FieldSchema(name="memory_type", dtype=DataType.VARCHAR, max_length=32),
            FieldSchema(name="importance_score", dtype=DataType.DOUBLE),
            FieldSchema(name="timestamp", dtype=DataType.DOUBLE),
            FieldSchema(name="metadata", dtype=DataType.VARCHAR, max_length=2048),
            FieldSchema(name="embedding", dtype=DataType.FLOAT_VECTOR, dim=self.embedding_dim)
        ]

        schema = CollectionSchema(fields, "Conversation memory embeddings")
        self.memory_collection = Collection(self.memory_collection_name, schema, using=self.connection_alias)

        # Create index for vector field
        index_params = {
            "index_type": "IVF_FLAT",
            "metric_type": "COSINE",
            "params": {"nlist": 1024}
        }
        self.memory_collection.create_index("embedding", index_params)
        self.logger.info("Created memory collection with vector index")

    def _chunk_text(self, text: str, chunk_size: int = 512, overlap: int = 50) -> list[str]:
        """Split text into overlapping chunks."""
        if len(text) <= chunk_size:
            return [text]

        chunks = []
        start = 0
        while start < len(text):
            end = start + chunk_size
            chunk = text[start:end]
            chunks.append(chunk)
            start = end - overlap
            if start >= len(text):
                break

        return chunks

    def _generate_embeddings(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for a list of texts."""
        try:
            embeddings = self.embedding_model.encode(texts, convert_to_tensor=False)
            return embeddings.tolist()
        except Exception as e:
            self.logger.error(f"Error generating embeddings: {e}")
            return []

    def _create_document_id(self, file_path: str, chunk_index: int) -> str:
        """Create unique document ID."""
        content = f"{file_path}_{chunk_index}"
        return hashlib.md5(content.encode()).hexdigest()

    def index_file_content(self, file_path: str, content: str, metadata: dict | None = None) -> bool:
        """
        Index file content in the vector database.
        
        Args:
            file_path: Path to the file
            content: File content to index
            metadata: Optional metadata about the file
            
        Returns:
            bool: Success status
        """
        try:
            # Check if it's a supported text file
            if not self._is_supported_file(file_path):
                return False

            # Chunk the content
            chunks = self._chunk_text(content)

            # Generate embeddings
            embeddings = self._generate_embeddings(chunks)

            if not embeddings:
                return False

            # Prepare data for insertion
            documents = []
            for i, (chunk, embedding) in enumerate(zip(chunks, embeddings, strict=False)):
                doc_id = self._create_document_id(file_path, i)
                doc = DocumentChunk(
                    id=doc_id,
                    content=chunk,
                    file_path=file_path,
                    chunk_index=i,
                    metadata=metadata or {},
                    timestamp=datetime.now().timestamp(),
                    embedding=embedding
                )
                documents.append(doc)

            # Insert into Milvus
            self._insert_documents(documents)

            self.logger.info(f"Indexed {len(documents)} chunks from {file_path}")
            return True

        except Exception as e:
            self.logger.error(f"Error indexing file {file_path}: {e}")
            return False

    def _is_supported_file(self, file_path: str) -> bool:
        """Check if file type is supported for content indexing."""
        supported_extensions = {'.txt', '.md', '.json', '.py', '.js', '.ts', '.java', '.cpp', '.c', '.h'}
        return Path(file_path).suffix.lower() in supported_extensions

    def _insert_documents(self, documents: list[DocumentChunk]):
        """Insert document chunks into Milvus."""
        if self.use_milvus_lite:
            # Milvus Lite uses auto-generated IDs, so we store our string ID in doc_id field
            data = []
            for doc in documents:
                data.append({
                    "doc_id": doc.id,  # Our string ID goes in doc_id field
                    "vector": doc.embedding,
                    "content": doc.content,
                    "file_path": doc.file_path,
                    "chunk_index": doc.chunk_index,
                    "metadata": json.dumps(doc.metadata),
                    "timestamp": doc.timestamp
                })

            self.client.insert(
                collection_name=self.files_collection_name,
                data=data
            )
        else:
            # Regular Milvus API
            data = [
                [doc.id for doc in documents],
                [doc.content for doc in documents],
                [doc.file_path for doc in documents],
                [doc.chunk_index for doc in documents],
                [json.dumps(doc.metadata) for doc in documents],
                [doc.timestamp for doc in documents],
                [doc.embedding for doc in documents]
            ]

            self.files_collection.insert(data)
            self.files_collection.flush()

    def search_similar_content(self, query: str, limit: int = 10, score_threshold: float = 0.7) -> list[dict]:
        """
        Search for similar content in the vector database.
        
        Args:
            query: Search query
            limit: Maximum number of results
            score_threshold: Minimum similarity score
            
        Returns:
            List of similar documents with metadata
        """
        try:
            # Generate query embedding
            query_embedding = self._generate_embeddings([query])[0]

            similar_docs = []

            if self.use_milvus_lite:
                # Milvus Lite search
                results = self.client.search(
                    collection_name=self.files_collection_name,
                    data=[query_embedding],
                    limit=limit,
                    output_fields=["doc_id", "content", "file_path", "chunk_index", "metadata", "timestamp"]
                )

                # Process results
                for hit in results[0]:
                    if hit.get("distance", 0) >= score_threshold:
                        similar_docs.append({
                            "id": hit.get("entity", {}).get("doc_id"),
                            "content": hit.get("entity", {}).get("content"),
                            "file_path": hit.get("entity", {}).get("file_path"),
                            "chunk_index": hit.get("entity", {}).get("chunk_index"),
                            "metadata": json.loads(hit.get("entity", {}).get("metadata", "{}")),
                            "timestamp": hit.get("entity", {}).get("timestamp"),
                            "similarity_score": hit.get("distance", 0)
                        })
            else:
                # Regular Milvus search
                # Load collection into memory
                self.files_collection.load()

                # Search parameters
                search_params = {"metric_type": "COSINE", "params": {"nprobe": 10}}

                # Perform search
                results = self.files_collection.search(
                    data=[query_embedding],
                    anns_field="embedding",
                    param=search_params,
                    limit=limit,
                    output_fields=["content", "file_path", "chunk_index", "metadata", "timestamp"]
                )

                # Process results
                for hit in results[0]:
                    if hit.score >= score_threshold:
                        similar_docs.append({
                            "id": hit.id,
                            "content": hit.entity.get("content"),
                            "file_path": hit.entity.get("file_path"),
                            "chunk_index": hit.entity.get("chunk_index"),
                            "metadata": json.loads(hit.entity.get("metadata", "{}")),
                            "timestamp": hit.entity.get("timestamp"),
                            "similarity_score": hit.score
                        })

            return similar_docs

        except Exception as e:
            self.logger.error(f"Error searching similar content: {e}")
            return []

    def store_short_term_memory(self, content: str, importance_score: float = 0.5, metadata: dict | None = None) -> bool:
        """Store short-term conversation memory."""
        return self._store_memory(content, "short_term", importance_score, metadata)

    def store_long_term_memory(self, content: str, importance_score: float = 0.8, metadata: dict | None = None) -> bool:
        """Store long-term conversation memory."""
        return self._store_memory(content, "long_term", importance_score, metadata)

    def _store_memory(self, content: str, memory_type: str, importance_score: float, metadata: dict | None = None) -> bool:
        """Store memory entry in vector database."""
        try:
            # Generate embedding
            embedding = self._generate_embeddings([content])[0]

            # Create memory entry
            memory_id = hashlib.md5(f"{content}_{datetime.now().timestamp()}".encode()).hexdigest()

            if self.use_milvus_lite:
                # Milvus Lite API - use auto-generated ID and store our string ID in mem_id field
                data = [{
                    "mem_id": memory_id,  # Our string ID goes in mem_id field
                    "vector": embedding,
                    "content": content,
                    "memory_type": memory_type,
                    "importance_score": importance_score,
                    "timestamp": datetime.now().timestamp(),
                    "metadata": json.dumps(metadata or {})
                }]

                self.client.insert(
                    collection_name=self.memory_collection_name,
                    data=data
                )
            else:
                # Regular Milvus API
                data = [
                    [memory_id],
                    [content],
                    [memory_type],
                    [importance_score],
                    [datetime.now().timestamp()],
                    [json.dumps(metadata or {})],
                    [embedding]
                ]

                self.memory_collection.insert(data)
                self.memory_collection.flush()

            return True

        except Exception as e:
            self.logger.error(f"Error storing {memory_type} memory: {e}")
            return False

    def search_memory(self, query: str, memory_type: str | None = None, limit: int = 5) -> list[dict]:
        """Search conversation memory."""
        try:
            # Generate query embedding
            query_embedding = self._generate_embeddings([query])[0]

            # Load collection
            self.memory_collection.load()

            # Search parameters
            search_params = {"metric_type": "COSINE", "params": {"nprobe": 10}}

            # Add filter for memory type if specified
            expr = f'memory_type == "{memory_type}"' if memory_type else None

            # Perform search
            results = self.memory_collection.search(
                data=[query_embedding],
                anns_field="embedding",
                param=search_params,
                limit=limit,
                expr=expr,
                output_fields=["content", "memory_type", "importance_score", "timestamp", "metadata"]
            )

            # Process results
            memories = []
            for hit in results[0]:
                memories.append({
                    "id": hit.id,
                    "content": hit.entity.get("content"),
                    "memory_type": hit.entity.get("memory_type"),
                    "importance_score": hit.entity.get("importance_score"),
                    "timestamp": hit.entity.get("timestamp"),
                    "metadata": json.loads(hit.entity.get("metadata", "{}")),
                    "similarity_score": hit.score
                })

            return memories

        except Exception as e:
            self.logger.error(f"Error searching memory: {e}")
            return []

    def clear_short_term_memory(self) -> bool:
        """Clear short-term memory entries."""
        try:
            expr = 'memory_type == "short_term"'
            self.memory_collection.delete(expr)
            return True
        except Exception as e:
            self.logger.error(f"Error clearing short-term memory: {e}")
            return False

    def cleanup_old_entries(self, days_old: int = 30) -> bool:
        """Remove old entries from collections."""
        try:
            cutoff_timestamp = datetime.now().timestamp() - (days_old * 24 * 3600)

            # Remove old file entries
            expr = f"timestamp < {cutoff_timestamp}"
            self.files_collection.delete(expr)

            # Remove old short-term memories (keep long-term)
            expr = f'timestamp < {cutoff_timestamp} and memory_type == "short_term"'
            self.memory_collection.delete(expr)

            return True
        except Exception as e:
            self.logger.error(f"Error during cleanup: {e}")
            return False

    def get_collection_stats(self) -> dict[str, Any]:
        """Get statistics about the collections."""
        try:
            if self.use_milvus_lite:
                # For Milvus Lite, get stats using client
                collections = self.client.list_collections()
                files_stats = 0
                memory_stats = 0

                if self.files_collection_name in collections:
                    # Note: Milvus Lite might not have direct entity count,
                    # but we can try to get collection info
                    files_stats = "Available"

                if self.memory_collection_name in collections:
                    memory_stats = "Available"

                return {
                    "files_indexed": files_stats,
                    "memory_entries": memory_stats,
                    "embedding_dimension": self.embedding_dim,
                    "storage_type": "Milvus Lite",
                    "database_path": self.db_path,
                    "model_name": type(self.embedding_model).__name__
                }
            else:
                files_stats = self.files_collection.num_entities
                memory_stats = self.memory_collection.num_entities

                return {
                    "files_indexed": files_stats,
                    "memory_entries": memory_stats,
                    "embedding_dimension": self.embedding_dim,
                    "storage_type": "Milvus Server",
                    "model_name": type(self.embedding_model).__name__
                }
        except Exception as e:
            self.logger.error(f"Error getting stats: {e}")
            return {}

    def health_check(self) -> bool:
        """Check if vector database is healthy."""
        try:
            if self.use_milvus_lite:
                # For Milvus Lite, check if we can list collections
                collections = self.client.list_collections()
                return isinstance(collections, list)
            else:
                return utility.get_server_version(using=self.connection_alias) is not None
        except Exception:
            return False

    def close(self):
        """Close database connections."""
        try:
            if self.use_milvus_lite:
                if hasattr(self.client, 'close'):
                    self.client.close()
            else:
                connections.disconnect(self.connection_alias)
        except Exception as e:
            self.logger.error(f"Error closing connection: {e}")
