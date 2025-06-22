#!/usr/bin/env python3
"""
Basic usage example for the Unfold file locator.

This script demonstrates how to use Unfold programmatically to index
and search files on your system.
"""

import time
from pathlib import Path

from unfold.core.database import DatabaseManager
from unfold.core.indexer import FileIndexer
from unfold.core.searcher import FileSearcher


def main():
    """Demonstrate basic Unfold functionality."""
    print("🔍 Unfold - Basic Usage Example")
    print("=" * 40)

    # 1. Initialize components
    print("\n1. Initializing Unfold components...")
    db = DatabaseManager()
    indexer = FileIndexer(db)
    searcher = FileSearcher(db)

    # 2. Index a directory (using current directory as example)
    current_dir = Path.cwd()
    print(f"\n2. Indexing directory: {current_dir}")

    def progress_callback(count, path):
        if count % 10 == 0:  # Print every 10 files
            print(f"   Indexed {count} items...")

    try:
        indexer.index_directory(
            str(current_dir),
            recursive=False,  # Only index current level
            progress_callback=progress_callback
        )
        print("   Indexing complete!")
    except Exception as e:
        print(f"   Error during indexing: {e}")
        return

    # 3. Show indexing statistics
    print("\n3. Indexing Statistics:")
    stats = indexer.get_indexing_stats()
    print(f"   Total files indexed: {stats['total_files']}")
    print(f"   Total keywords: {stats['total_keywords']}")

    # 4. Perform some searches
    print("\n4. Search Examples:")

    # Search for Python files
    print("\n   Searching for 'py' files:")
    results = searcher.search("py", file_types=['.py'])
    for i, result in enumerate(results[:5], 1):
        print(f"   {i}. {result.name} (score: {result.score:.1f})")

    # Search for README files
    print("\n   Searching for 'readme':")
    results = searcher.search("readme")
    for i, result in enumerate(results[:3], 1):
        print(f"   {i}. {result.name} (score: {result.score:.1f})")

    # Search for config files
    print("\n   Searching for 'config':")
    results = searcher.search("config")
    for i, result in enumerate(results[:3], 1):
        print(f"   {i}. {result.name} (score: {result.score:.1f})")

    # 5. Demonstrate fuzzy search
    print("\n5. Fuzzy Search Example:")
    print("   Searching for 'readm' (fuzzy match for 'readme'):")
    results = searcher.search("readm")
    for i, result in enumerate(results[:3], 1):
        print(f"   {i}. {result.name} (score: {result.score:.1f}, type: {result.match_type})")

    # 6. File access simulation
    print("\n6. Simulating file access (for frequency/recency scoring):")
    if results:
        # Update access stats for first result
        searcher.update_access_stats(results[0].path)
        print(f"   Marked '{results[0].name}' as accessed")

        # Search again to see updated scoring
        print("   Searching again - notice the score change:")
        new_results = searcher.search("readm")
        for i, result in enumerate(new_results[:3], 1):
            print(f"   {i}. {result.name} (score: {result.score:.1f})")

    # 7. Recent files
    print("\n7. Recent Files:")
    recent = searcher.get_recent_files(limit=5)
    if recent:
        for i, result in enumerate(recent, 1):
            print(f"   {i}. {result.name}")
    else:
        print("   No recently accessed files found")

    # 8. Search performance
    print("\n8. Search Performance Test:")
    start_time = time.time()

    # Perform multiple searches
    queries = ["py", "txt", "md", "json", "test"]
    total_results = 0

    for query in queries:
        results = searcher.search(query)
        total_results += len(results)

    end_time = time.time()
    avg_time = (end_time - start_time) / len(queries) * 1000  # ms per search

    print(f"   Performed {len(queries)} searches")
    print(f"   Total results: {total_results}")
    print(f"   Average search time: {avg_time:.2f}ms")

    # 9. Cleanup
    print("\n9. Cleanup:")
    db.close()
    print("   Database connection closed")

    print("\n✅ Example completed successfully!")
    print("\nTo see more advanced features, try:")
    print("   - unfold index ~/Documents  # Index your documents")
    print("   - unfold                    # Interactive search mode")
    print("   - unfold monitor ~/         # Real-time monitoring")


if __name__ == "__main__":
    main()
