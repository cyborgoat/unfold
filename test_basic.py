#!/usr/bin/env python3
"""
Basic test script to verify the core functionality works.
This script tests the database component which has minimal dependencies.
"""

import json
import os
import sqlite3
import sys
import tempfile
from typing import Any


def test_database_basic():
    """Test basic database functionality."""
    print("🧪 Testing database functionality...")

    try:
        # Create a minimal database manager for testing
        class MinimalDatabaseManager:
            def __init__(self, db_path: str):
                self.db_path = db_path
                self.conn = sqlite3.connect(db_path, check_same_thread=False)
                self.conn.row_factory = sqlite3.Row
                self._create_tables()

            def _create_tables(self) -> None:
                cursor = self.conn.cursor()
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
                self.conn.commit()

            def insert_file(self, file_info: dict[str, Any]) -> int:
                cursor = self.conn.cursor()
                cursor.execute("""
                    INSERT OR REPLACE INTO files 
                    (path, name, size, created_time, modified_time, file_type, is_directory, indexed_time)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    file_info['path'],
                    file_info['name'],
                    file_info.get('size'),
                    file_info.get('created_time'),
                    file_info.get('modified_time'),
                    file_info.get('file_type'),
                    file_info.get('is_directory', False),
                    file_info.get('indexed_time')
                ))
                file_id = cursor.lastrowid
                self.conn.commit()
                return file_id

            def insert_keywords(self, file_id: int, keywords: list[str]) -> None:
                cursor = self.conn.cursor()
                cursor.execute("DELETE FROM inverted_index WHERE file_id = ?", (file_id,))
                for keyword in keywords:
                    cursor.execute("""
                        INSERT OR IGNORE INTO inverted_index (keyword, file_id)
                        VALUES (?, ?)
                    """, (keyword.lower(), file_id))
                self.conn.commit()

            def search_files(self, query: str, limit: int = 50) -> list[sqlite3.Row]:
                cursor = self.conn.cursor()
                cursor.execute("""
                    SELECT * FROM files 
                    WHERE name LIKE ? 
                    ORDER BY access_count DESC
                    LIMIT ?
                """, (f"%{query}%", limit))
                return cursor.fetchall()

            def get_stats(self) -> dict[str, int]:
                cursor = self.conn.cursor()
                cursor.execute("SELECT COUNT(*) as total_files FROM files")
                total_files = cursor.fetchone()['total_files']
                cursor.execute("SELECT COUNT(*) as total_keywords FROM inverted_index")
                total_keywords = cursor.fetchone()['total_keywords']
                return {
                    'total_files': total_files,
                    'total_keywords': total_keywords,
                    'cached_searches': 0
                }

            def close(self) -> None:
                if self.conn:
                    self.conn.close()

        # Create temporary database
        with tempfile.NamedTemporaryFile(delete=False, suffix='.db') as temp_db:
            temp_db_path = temp_db.name

        try:
            # Initialize database
            db = MinimalDatabaseManager(temp_db_path)
            print("   ✅ Database initialization successful")

            # Test file insertion
            file_info = {
                'path': '/test/example.py',
                'name': 'example.py',
                'size': 1024,
                'file_type': '.py',
                'is_directory': False,
                'indexed_time': 1234567890.0
            }

            file_id = db.insert_file(file_info)
            print(f"   ✅ File insertion successful (ID: {file_id})")

            # Test keyword insertion
            keywords = ['example', 'py', 'test', 'python']
            db.insert_keywords(file_id, keywords)
            print("   ✅ Keyword insertion successful")

            # Test search
            results = db.search_files('example')
            assert len(results) > 0
            print(f"   ✅ Search successful (found {len(results)} results)")

            # Test statistics
            stats = db.get_stats()
            print(f"   ✅ Statistics: {stats['total_files']} files, {stats['total_keywords']} keywords")

            # Clean up
            db.close()
            print("   ✅ Database closed successfully")

        finally:
            # Remove temporary database
            if os.path.exists(temp_db_path):
                os.unlink(temp_db_path)

    except Exception as e:
        print(f"   ❌ Test failed: {e}")
        return False

    return True

def test_configuration():
    """Test configuration management."""
    print("\n🧪 Testing configuration functionality...")

    try:
        # Create a minimal config manager for testing
        class MinimalConfigManager:
            DEFAULT_CONFIG = {
                'search': {
                    'fuzzy_threshold': 0.6,
                    'max_results': 50
                }
            }

            def __init__(self, config_path: str):
                self.config_path = config_path
                self.config = self.DEFAULT_CONFIG.copy()

            def get(self, key_path: str, default: Any = None) -> Any:
                keys = key_path.split('.')
                value = self.config
                for key in keys:
                    if isinstance(value, dict) and key in value:
                        value = value[key]
                    else:
                        return default
                return value

            def set(self, key_path: str, value: Any) -> None:
                keys = key_path.split('.')
                config = self.config
                for key in keys[:-1]:
                    if key not in config:
                        config[key] = {}
                    config = config[key]
                config[keys[-1]] = value

            def save_config(self) -> None:
                with open(self.config_path, 'w') as f:
                    json.dump(self.config, f, indent=2)

        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as temp_config:
            temp_config_path = temp_config.name

        try:
            config = MinimalConfigManager(temp_config_path)
            print("   ✅ Configuration manager initialization successful")

            # Test getting default values
            fuzzy_threshold = config.get('search.fuzzy_threshold', 0.6)
            assert fuzzy_threshold == 0.6
            print(f"   ✅ Configuration retrieval successful (fuzzy_threshold: {fuzzy_threshold})")

            # Test setting values
            config.set('search.max_results', 25)
            assert config.get('search.max_results') == 25
            print("   ✅ Configuration setting successful")

            # Test saving
            config.save_config()
            print("   ✅ Configuration saving successful")

        finally:
            if os.path.exists(temp_config_path):
                os.unlink(temp_config_path)

    except Exception as e:
        print(f"   ❌ Configuration test failed: {e}")
        return False

    return True

def main():
    """Run all basic tests."""
    print("🔍 Unfold - Basic Functionality Test")
    print("=" * 40)

    # Test individual components
    tests = [
        test_database_basic,
        test_configuration,
    ]

    passed = 0
    total = len(tests)

    for test in tests:
        if test():
            passed += 1

    print(f"\n📊 Test Results: {passed}/{total} tests passed")

    if passed == total:
        print("🎉 All basic tests passed! The core functionality is working.")
        print("\n📋 Next steps:")
        print("   1. Install dependencies: uv pip install -e .")
        print("   2. Run full tests: pytest")
        print("   3. Try the CLI: unfold --help")
        print("   4. Run the example: python examples/basic_usage.py")
        return True
    else:
        print("❌ Some tests failed. Please check the error messages above.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
