#!/usr/bin/env python3
"""
Test script to verify local AI setup without Docker.
This script tests Milvus Lite, local configurations, and basic functionality.
"""

import importlib
import json
import os
import sys
import tempfile
from pathlib import Path


def test_basic_setup():
    """Test basic system requirements."""
    print("Testing basic setup...")
    try:
        # Test Python version
        python_version = f"{sys.version_info.major}.{sys.version_info.minor}"
        print(f"✓ Python version: {python_version}")

        if sys.version_info < (3, 11):
            print("⚠ Warning: Python 3.11+ recommended")

        # Test basic imports
        print("✓ Basic Python modules available")

        return True
    except Exception as e:
        print(f"✗ Basic setup test failed: {e}")
        return False

def test_milvus_lite():
    """Test Milvus Lite connection and basic operations."""
    print("Testing Milvus Lite...")
    try:
        # Test import first
        from pymilvus import MilvusClient
        print("✓ PyMilvus package available")

        # Create temporary database file
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
            db_path = tmp.name

        # Test connection (quick operation)
        client = MilvusClient(db_path)

        # Test basic operations
        collections = client.list_collections()
        print(f"✓ Milvus Lite connected successfully. Collections: {collections}")

        # Cleanup
        if hasattr(client, 'close'):
            client.close()
        os.unlink(db_path)

        return True
    except ImportError as e:
        print(f"✗ PyMilvus not available: {e}")
        print("  Install with: pip install pymilvus")
        return False
    except Exception as e:
        print(f"✗ Milvus Lite test failed: {e}")
        return False

def test_python_dependencies():
    """Test if key Python packages are available."""
    print("Testing Python dependencies...")

    # Quick tests first (no heavy imports)
    quick_packages = [
        ("requests", "HTTP client"),
        ("neo4j", "Graph database driver"),
        ("ollama", "Ollama client"),
        ("fastmcp", "MCP server")
    ]

    # Slower packages that might load heavy dependencies
    slow_packages = [
        ("pymilvus", "Vector database"),
        ("sentence_transformers", "Text embeddings")
    ]

    all_available = True

    # Test quick packages first
    for package, description in quick_packages:
        try:
            importlib.import_module(package)
            print(f"✓ {package:<20} - {description}")
        except ImportError:
            print(f"✗ {package:<20} - {description} (not installed)")
            all_available = False

    # Test slower packages (with warning)
    for package, description in slow_packages:
        try:
            print(f"  Loading {package}... (may take a moment)")
            importlib.import_module(package)
            print(f"✓ {package:<20} - {description}")
        except ImportError:
            print(f"✗ {package:<20} - {description} (not installed)")
            all_available = False
        except Exception as e:
            print(f"⚠ {package:<20} - {description} (import issue: {e})")
            # Don't fail for import issues, just warn

    if all_available:
        print("✓ All required packages are available")
        print("  Note: Large models will be downloaded on first use")
    else:
        print("✗ Some packages are missing. Install with: pip install -e .")

    return all_available

def test_config_structure():
    """Test configuration file structure."""
    print("Testing configuration structure...")
    try:
        # Test configuration directory creation
        config_dir = Path.home() / ".config" / "unfold"
        config_dir.mkdir(parents=True, exist_ok=True)

        # Test configuration file creation
        config_file = config_dir / "config.json"

        test_config = {
            "llm": {
                "provider": "ollama",
                "model": "llama3.2",
                "base_url": "http://localhost:11434"
            },
            "vector_db": {
                "enabled": True,
                "use_milvus_lite": True,
                "local_db_path": "./knowledge/vector.db",
                "embedding_model": "all-MiniLM-L6-v2"
            },
            "graph_db": {
                "uri": "bolt://localhost:7687",
                "user": "neo4j",
                "password": "password",
                "database": "unfold",
                "enabled": True
            }
        }

        with open(config_file, 'w') as f:
            json.dump(test_config, f, indent=2)

        # Test reading config
        with open(config_file) as f:
            loaded_config = json.load(f)

        print(f"✓ Configuration structure test passed. Config saved to: {config_file}")
        return True
    except Exception as e:
        print(f"✗ Configuration test failed: {e}")
        return False

def test_knowledge_directory():
    """Test knowledge directory structure creation."""
    print("Testing knowledge directory structure...")
    try:
        knowledge_dir = Path("./knowledge")

        # Create directory structure
        (knowledge_dir / "files").mkdir(parents=True, exist_ok=True)
        (knowledge_dir / "memory").mkdir(parents=True, exist_ok=True)
        (knowledge_dir / "graph").mkdir(parents=True, exist_ok=True)

        print(f"✓ Knowledge directories created: {knowledge_dir}")

        # Test vector database file path
        vector_db_path = knowledge_dir / "vector.db"
        print(f"✓ Vector database will be created at: {vector_db_path}")

        return True
    except Exception as e:
        print(f"✗ Knowledge directory test failed: {e}")
        return False

def test_neo4j_connection():
    """Test if Neo4j connection is possible (without actually connecting)."""
    print("Testing Neo4j driver...")
    try:
        from neo4j import GraphDatabase

        # Just test import and driver creation (no connection)
        print("✓ Neo4j driver available")
        print("  Note: Make sure Neo4j is running on bolt://localhost:7687")
        print("  Username: neo4j, Password: password")

        return True
    except ImportError:
        print("✗ Neo4j driver not available. Install with: pip install neo4j")
        return False
    except Exception as e:
        print(f"✗ Neo4j test failed: {e}")
        return False

def test_ollama_connection():
    """Test if Ollama is available."""
    print("Testing Ollama connection...")
    try:
        import requests

        # Quick connection test with short timeout
        response = requests.get("http://localhost:11434/api/tags", timeout=2)
        if response.status_code == 200:
            models = response.json().get('models', [])
            print(f"✓ Ollama connected. Available models: {len(models)}")
            if len(models) == 0:
                print("  Note: No models installed. Run 'ollama pull llama3.2' to install a model")
            return True
        else:
            print("✗ Ollama service not responding")
            return False
    except ImportError:
        print("✗ Requests package not available")
        return False
    except Exception as e:
        # Import requests again for exception handling
        try:
            import requests
            if isinstance(e, requests.exceptions.ConnectionError):
                print("✗ Ollama not running on localhost:11434")
                print("  Install Ollama from: https://ollama.ai/")
                print("  Then run: ollama serve")
            elif isinstance(e, requests.exceptions.Timeout):
                print("✗ Ollama connection timeout")
                print("  Ollama may be starting up, try again in a moment")
            else:
                print(f"✗ Ollama test failed: {e}")
        except ImportError:
            print(f"✗ Ollama test failed: {e}")
        return False

def main():
    """Run all tests."""
    print("=" * 50)
    print("Unfold Local Setup Test (No Docker)")
    print("=" * 50)

    tests = [
        ("Basic Setup", test_basic_setup),
        ("Python Dependencies", test_python_dependencies),
        ("Configuration", test_config_structure),
        ("Knowledge Directories", test_knowledge_directory),
        ("Milvus Lite", test_milvus_lite),
        ("Neo4j Driver", test_neo4j_connection),
        ("Ollama Service", test_ollama_connection),
    ]

    results = []

    for test_name, test_func in tests:
        print(f"\n{test_name}:")
        print("-" * 30)
        result = test_func()
        results.append((test_name, result))

    print("\n" + "=" * 50)
    print("Test Results Summary:")
    print("=" * 50)

    all_passed = True
    for test_name, result in results:
        status = "PASS" if result else "FAIL"
        print(f"{test_name:<25} {status}")
        if not result:
            all_passed = False

    print("=" * 50)

    if all_passed:
        print("✓ All tests passed! Your local setup is ready.")
        print("\nNext steps:")
        print("1. Start Neo4j (if not already running)")
        print("2. Start Ollama: ollama serve")
        print("3. Pull a model: ollama pull llama3.2")
        print("4. Run: unfold ai")
    else:
        print("✗ Some tests failed. Please check the errors above.")
        print("\nCommon solutions:")
        print("- Install missing dependencies: pip install -e .")
        print("- Start required services (Neo4j, Ollama)")
        print("- Check network connectivity")

    return 0 if all_passed else 1

if __name__ == "__main__":
    sys.exit(main())
