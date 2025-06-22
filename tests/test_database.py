"""
Tests for the database manager.
"""

import os
import tempfile

from unfold.core.database import DatabaseManager


class TestDatabaseManager:
    """Test cases for DatabaseManager."""

    def setup_method(self):
        """Set up test database."""
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.temp_db.close()
        self.db = DatabaseManager(self.temp_db.name)

    def teardown_method(self):
        """Clean up test database."""
        self.db.close()
        if os.path.exists(self.temp_db.name):
            os.unlink(self.temp_db.name)

    def test_database_creation(self):
        """Test database and table creation."""
        stats = self.db.get_stats()
        assert stats['total_files'] == 0
        assert stats['total_keywords'] == 0
        assert stats['cached_searches'] == 0

    def test_file_insertion(self):
        """Test file information insertion."""
        file_info = {
            'path': '/test/path/file.txt',
            'name': 'file.txt',
            'size': 1024,
            'created_time': 1234567890.0,
            'modified_time': 1234567890.0,
            'file_type': '.txt',
            'is_directory': False,
            'indexed_time': 1234567890.0
        }

        file_id = self.db.insert_file(file_info)
        assert file_id > 0

        stats = self.db.get_stats()
        assert stats['total_files'] == 1

    def test_keyword_insertion(self):
        """Test keyword insertion for inverted index."""
        file_info = {
            'path': '/test/path/example.py',
            'name': 'example.py',
            'indexed_time': 1234567890.0
        }

        file_id = self.db.insert_file(file_info)
        keywords = ['example', 'py', 'test', 'python']
        self.db.insert_keywords(file_id, keywords)

        stats = self.db.get_stats()
        assert stats['total_keywords'] == len(keywords)

    def test_file_search(self):
        """Test basic file search functionality."""
        file_info = {
            'path': '/test/path/test_file.py',
            'name': 'test_file.py',
            'indexed_time': 1234567890.0
        }

        file_id = self.db.insert_file(file_info)
        keywords = ['test', 'file', 'py']
        self.db.insert_keywords(file_id, keywords)

        # Test exact match
        results = self.db.search_files('test_file.py')
        assert len(results) == 1
        assert results[0]['name'] == 'test_file.py'

        # Test partial match
        results = self.db.search_files('test')
        assert len(results) == 1

    def test_access_stats_update(self):
        """Test access statistics updating."""
        file_info = {
            'path': '/test/path/accessed_file.txt',
            'name': 'accessed_file.txt',
            'indexed_time': 1234567890.0
        }

        self.db.insert_file(file_info)
        self.db.update_access_stats('/test/path/accessed_file.txt')

        results = self.db.search_files('accessed_file.txt')
        assert len(results) == 1
        assert results[0]['access_count'] == 1

    def test_search_caching(self):
        """Test search result caching."""
        query = "test_query"
        results = [{"path": "/test", "name": "test", "score": 100}]

        # Cache results
        self.db.cache_search(query, results)

        # Retrieve cached results
        cached = self.db.get_cached_search(query)
        assert cached is not None
        assert len(cached) == 1
        assert cached[0]['name'] == 'test'

    def test_file_removal(self):
        """Test file removal from database."""
        file_info = {
            'path': '/test/path/to_remove.txt',
            'name': 'to_remove.txt',
            'indexed_time': 1234567890.0
        }

        file_id = self.db.insert_file(file_info)
        self.db.insert_keywords(file_id, ['remove', 'test'])

        # Verify file exists
        stats_before = self.db.get_stats()
        assert stats_before['total_files'] == 1

        # Remove file
        self.db.remove_file('/test/path/to_remove.txt')

        # Verify file removed
        stats_after = self.db.get_stats()
        assert stats_after['total_files'] == 0
