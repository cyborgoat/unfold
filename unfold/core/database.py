"""
Database management for file indexing using SQLite.
"""

import json
import os
import sqlite3
from typing import Any

import appdirs


class DatabaseManager:
    """Manages SQLite database for file indexing and metadata storage."""

    def __init__(self, db_path: str | None = None):
        if db_path is None:
            app_dir = appdirs.user_data_dir("unfold", "unfold")
            os.makedirs(app_dir, exist_ok=True)
            db_path = os.path.join(app_dir, "unfold.db")

        self.db_path = db_path
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._create_tables()

    def _create_tables(self) -> None:
        """Create necessary tables for file indexing."""
        cursor = self.conn.cursor()

        # Files table for storing file metadata
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS files (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                path TEXT UNIQUE NOT NULL,
                name TEXT NOT NULL,
                size INTEGER,
                created_time REAL,
                modified_time REAL,
                file_type TEXT,
                is_directory BOOLEAN,
                access_count INTEGER DEFAULT 0,
                last_accessed REAL,
                indexed_time REAL
            )
        """)

        # Inverted index table for keyword mapping
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS inverted_index (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                keyword TEXT NOT NULL,
                file_id INTEGER,
                weight REAL DEFAULT 1.0,
                FOREIGN KEY (file_id) REFERENCES files (id),
                UNIQUE(keyword, file_id)
            )
        """)

        # Search cache for frequently accessed searches
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS search_cache (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                query TEXT UNIQUE NOT NULL,
                results TEXT,
                access_count INTEGER DEFAULT 1,
                last_accessed REAL,
                created_time REAL
            )
        """)

        # Create indexes for performance
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_files_name ON files (name)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_files_path ON files (path)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_files_type ON files (file_type)")
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_inverted_keyword ON inverted_index (keyword)"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_search_cache_query ON search_cache (query)"
        )

        self.conn.commit()

    def insert_file(self, file_info: dict[str, Any]) -> int:
        """Insert or update file information."""
        cursor = self.conn.cursor()

        cursor.execute(
            """
            INSERT OR REPLACE INTO files 
            (path, name, size, created_time, modified_time, file_type, is_directory, indexed_time)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
            (
                file_info["path"],
                file_info["name"],
                file_info.get("size"),
                file_info.get("created_time"),
                file_info.get("modified_time"),
                file_info.get("file_type"),
                file_info.get("is_directory", False),
                file_info.get("indexed_time"),
            ),
        )

        file_id = cursor.lastrowid
        self.conn.commit()
        return file_id

    def insert_keywords(self, file_id: int, keywords: list[str]) -> None:
        """Insert keywords for inverted index."""
        cursor = self.conn.cursor()

        # Remove existing keywords for this file
        cursor.execute("DELETE FROM inverted_index WHERE file_id = ?", (file_id,))

        # Insert new keywords
        for keyword in keywords:
            cursor.execute(
                """
                INSERT OR IGNORE INTO inverted_index (keyword, file_id)
                VALUES (?, ?)
            """,
                (keyword.lower(), file_id),
            )

        self.conn.commit()

    def search_files(self, query: str, limit: int = 50) -> list[sqlite3.Row]:
        """Search files by query using various matching strategies."""
        cursor = self.conn.cursor()

        # Exact name match (highest priority)
        cursor.execute(
            """
            SELECT * FROM files 
            WHERE name = ? 
            ORDER BY access_count DESC, last_accessed DESC
            LIMIT ?
        """,
            (query, limit),
        )
        exact_matches = cursor.fetchall()

        # Partial name match
        cursor.execute(
            """
            SELECT * FROM files 
            WHERE name LIKE ? AND name != ?
            ORDER BY access_count DESC, last_accessed DESC
            LIMIT ?
        """,
            (f"%{query}%", query, limit),
        )
        partial_matches = cursor.fetchall()

        # Keyword-based search through inverted index
        cursor.execute(
            """
            SELECT f.*, COUNT(i.keyword) as keyword_matches
            FROM files f
            JOIN inverted_index i ON f.id = i.file_id
            WHERE i.keyword LIKE ?
            GROUP BY f.id
            ORDER BY keyword_matches DESC, f.access_count DESC
            LIMIT ?
        """,
            (f"%{query.lower()}%", limit),
        )
        keyword_matches = cursor.fetchall()

        # Combine results while avoiding duplicates
        seen_paths = set()
        results = []

        for match in exact_matches + partial_matches + keyword_matches:
            if match["path"] not in seen_paths:
                seen_paths.add(match["path"])
                results.append(match)
                if len(results) >= limit:
                    break

        return results

    def update_access_stats(self, file_path: str) -> None:
        """Update access statistics for a file."""
        import time

        cursor = self.conn.cursor()

        cursor.execute(
            """
            UPDATE files 
            SET access_count = access_count + 1, last_accessed = ?
            WHERE path = ?
        """,
            (time.time(), file_path),
        )

        self.conn.commit()

    def cache_search(self, query: str, results: list[dict]) -> None:
        """Cache search results for faster retrieval."""
        import time

        cursor = self.conn.cursor()

        cursor.execute(
            """
            INSERT OR REPLACE INTO search_cache 
            (query, results, access_count, last_accessed, created_time)
            VALUES (?, ?, COALESCE((SELECT access_count FROM search_cache WHERE query = ?), 0) + 1, ?, ?)
        """,
            (query, json.dumps(results), query, time.time(), time.time()),
        )

        self.conn.commit()

    def get_cached_search(self, query: str) -> list[dict] | None:
        """Retrieve cached search results."""
        cursor = self.conn.cursor()

        cursor.execute(
            """
            SELECT results FROM search_cache 
            WHERE query = ?
        """,
            (query,),
        )

        result = cursor.fetchone()
        if result:
            return json.loads(result["results"])
        return None

    def remove_file(self, file_path: str) -> None:
        """Remove file from database."""
        cursor = self.conn.cursor()

        # Get file ID first
        cursor.execute("SELECT id FROM files WHERE path = ?", (file_path,))
        file_record = cursor.fetchone()

        if file_record:
            file_id = file_record["id"]

            # Remove from inverted index
            cursor.execute("DELETE FROM inverted_index WHERE file_id = ?", (file_id,))

            # Remove from files
            cursor.execute("DELETE FROM files WHERE id = ?", (file_id,))

            self.conn.commit()

    def cleanup_old_cache(self, max_age_days: int = 30) -> None:
        """Clean up old cache entries."""
        import time

        cursor = self.conn.cursor()

        cutoff_time = time.time() - (max_age_days * 24 * 60 * 60)
        cursor.execute(
            """
            DELETE FROM search_cache 
            WHERE last_accessed < ?
        """,
            (cutoff_time,),
        )

        self.conn.commit()

    def get_stats(self) -> dict[str, int]:
        """Get database statistics."""
        cursor = self.conn.cursor()

        cursor.execute("SELECT COUNT(*) as total_files FROM files")
        total_files = cursor.fetchone()["total_files"]

        cursor.execute("SELECT COUNT(*) as total_keywords FROM inverted_index")
        total_keywords = cursor.fetchone()["total_keywords"]

        cursor.execute("SELECT COUNT(*) as cached_searches FROM search_cache")
        cached_searches = cursor.fetchone()["cached_searches"]

        return {
            "total_files": total_files,
            "total_keywords": total_keywords,
            "cached_searches": cached_searches,
        }

    def clear_all(self) -> None:
        """Clear all tables in the database and remove the DB file, then recreate it."""
        original_db_path = self.db_path
        self.close()  # Close the connection first

        try:
            if os.path.exists(original_db_path):
                os.remove(original_db_path)
            # Re-initialize to create a new empty DB and tables
            self.__init__(db_path=original_db_path)
        except OSError as e:
            # If removal or re-initialization fails, attempt to restore a basic connection
            # or at least log the error. For now, we'll re-raise to indicate a critical issue.
            # A more robust solution might try to re-establish a connection to a potentially existing (but not deleted) file.
            print(f"Error during database clearing and recreation: {e}")
            # Attempt to reconnect or leave in a defined state if possible
            # For simplicity here, we are re-raising. Consider more advanced error handling for production.
            self.conn = None  # Ensure conn is None if re-init failed
            raise

    def close(self) -> None:
        """Close database connection."""
        if self.conn:
            self.conn.close()
