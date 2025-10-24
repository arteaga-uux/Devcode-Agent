#!/usr/bin/env python3
"""
Local test script for my_agent module.
Tests the complete pipeline and agent functionality.
"""

import sys
from pathlib import Path

# Add parent directory to path to enable package imports
current_dir = Path(__file__).parent
parent_dir = current_dir.parent
sys.path.insert(0, str(parent_dir))

# Set package context
import os
os.chdir(str(current_dir))

def test_imports():
    """Test that all imports work correctly."""
    print("=" * 60)
    print("TEST 1: Checking imports...")
    print("=" * 60)
    
    try:
        from my_agent.config import CONFIG, SOURCE_DIRECTORY, VECTORSTORE_PATH
        print("✅ Config imports OK")
        
        from my_agent.embedder import get_embedding_model
        print("✅ Embedder imports OK")
        
        from my_agent.discovery import find_source_files
        print("✅ Discovery imports OK")
        
        from my_agent.loader import load_documents_from_paths
        print("✅ Loader imports OK")
        
        from my_agent.code_splitter import split_c_code_by_function
        print("✅ Code splitter imports OK")
        
        from my_agent.chunking import chunk_documents
        print("✅ Chunking imports OK")
        
        from my_agent.build_vectorstore import build_vectorstore
        print("✅ Vectorstore imports OK")
        
        from my_agent.retriever import load_retriever
        print("✅ Retriever imports OK")
        
        from my_agent.context_formatter import format_context_from_docs
        print("✅ Context formatter imports OK")
        
        from my_agent.context_builder import build_context_for_query
        print("✅ Context builder imports OK")
        
        from my_agent.code_tools import CodeTools
        print("✅ Code tools imports OK")
        
        from my_agent.agent import GnomeCodeAgent
        print("✅ Agent imports OK")
        
        from my_agent.incremental_pipeline import IncrementalPipeline
        print("✅ Incremental pipeline imports OK")
        
        from my_agent.file_tracker import FileModificationTracker
        print("✅ File tracker imports OK")
        
        print("\n✅ All imports successful!\n")
        return True
        
    except ImportError as e:
        print(f"\n❌ Import failed: {e}\n")
        import traceback
        traceback.print_exc()
        return False


def test_config():
    """Test configuration."""
    print("=" * 60)
    print("TEST 2: Checking configuration...")
    print("=" * 60)
    
    try:
        from my_agent.config import CONFIG, SOURCE_DIRECTORY, VECTORSTORE_PATH, OPENAI_API_KEY
        
        print(f"📁 Source directory: {SOURCE_DIRECTORY}")
        print(f"📁 Vectorstore path: {VECTORSTORE_PATH}")
        print(f"🔑 OpenAI API key configured: {'Yes' if OPENAI_API_KEY else 'No (set OPENAI_API_KEY env var)'}")
        print(f"🤖 Model: {CONFIG.model_name}")
        print(f"📊 Chunk size: {CONFIG.chunk_size}")
        print(f"📊 Top K: {CONFIG.top_k}")
        print(f"🔧 Debug mode: {CONFIG.verbose}")
        
        print("\n✅ Configuration loaded successfully!\n")
        return True
        
    except Exception as e:
        print(f"\n❌ Configuration error: {e}\n")
        return False


def test_discovery():
    """Test file discovery."""
    print("=" * 60)
    print("TEST 3: Testing file discovery...")
    print("=" * 60)
    
    try:
        from my_agent.discovery import find_source_files
        from my_agent.config import SOURCE_DIRECTORY, DEFAULT_EXTENSIONS, DEFAULT_EXCLUDES, DEFAULT_MAX_FILE_SIZE_KB
        
        print(f"🔍 Searching in: {SOURCE_DIRECTORY}")
        
        if not SOURCE_DIRECTORY.exists():
            print(f"⚠️  Source directory does not exist: {SOURCE_DIRECTORY}")
            print("   This is OK for testing imports, but you'll need a valid directory for full operation.")
            return True
        
        files = find_source_files(
            base_path=SOURCE_DIRECTORY,
            valid_extensions=set(DEFAULT_EXTENSIONS),
            exclude_dirs=set(DEFAULT_EXCLUDES),
            max_file_size_kb=DEFAULT_MAX_FILE_SIZE_KB
        )
        
        print(f"📂 Found {len(files)} source files")
        if files:
            print(f"   Sample files:")
            for f in files[:5]:
                print(f"   - {f.name}")
        
        print("\n✅ File discovery successful!\n")
        return True
        
    except Exception as e:
        print(f"\n❌ Discovery error: {e}\n")
        import traceback
        traceback.print_exc()
        return False


def test_agent_init():
    """Test agent initialization."""
    print("=" * 60)
    print("TEST 4: Testing agent initialization...")
    print("=" * 60)
    
    try:
        from my_agent.agent import GnomeCodeAgent
        from my_agent.config import SOURCE_DIRECTORY, OPENAI_API_KEY
        
        if not OPENAI_API_KEY:
            print("⚠️  OPENAI_API_KEY not set - skipping agent init test")
            print("   Set OPENAI_API_KEY environment variable to test agent functionality")
            return True
        
        print("🤖 Initializing agent...")
        agent = GnomeCodeAgent(str(SOURCE_DIRECTORY))
        
        print(f"   ✓ Agent created")
        print(f"   ✓ Code tools initialized")
        print(f"   ✓ LLM configured: {agent.llm.model_name}")
        print(f"   ✓ Graph compiled with {len(agent.graph.nodes)} nodes")
        
        print("\n✅ Agent initialization successful!\n")
        return True
        
    except Exception as e:
        print(f"\n❌ Agent initialization error: {e}\n")
        import traceback
        traceback.print_exc()
        return False


def test_pipeline_status():
    """Test pipeline status check."""
    print("=" * 60)
    print("TEST 5: Testing pipeline status...")
    print("=" * 60)
    
    try:
        from my_agent.incremental_pipeline import IncrementalPipeline
        from my_agent.config import SOURCE_DIRECTORY
        
        if not SOURCE_DIRECTORY.exists():
            print(f"⚠️  Source directory does not exist: {SOURCE_DIRECTORY}")
            print("   Skipping pipeline status test (configure CODEBASE_DIR for full test)")
            return True
        
        print("🔧 Creating pipeline...")
        pipeline = IncrementalPipeline(SOURCE_DIRECTORY)
        
        print("📊 Checking status...")
        status = pipeline.check_status()
        
        print(f"   Vectorstore exists: {status['vectorstore_exists']}")
        print(f"   Modified files count: {status['modified_files_count']}")
        print(f"   Needs rebuild: {status['needs_rebuild']}")
        
        print("\n✅ Pipeline status check successful!\n")
        return True
        
    except Exception as e:
        print(f"\n❌ Pipeline error: {e}\n")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all tests."""
    print("\n" + "=" * 60)
    print("GNOME ASSISTANT - LOCAL TEST SUITE")
    print("=" * 60 + "\n")
    
    results = []
    
    # Run tests
    results.append(("Imports", test_imports()))
    results.append(("Configuration", test_config()))
    results.append(("File Discovery", test_discovery()))
    results.append(("Agent Initialization", test_agent_init()))
    results.append(("Pipeline Status", test_pipeline_status()))
    
    # Summary
    print("=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} - {name}")
    
    print(f"\nResults: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All tests passed! The agent is ready for local use.\n")
        print("Next steps:")
        print("1. Set OPENAI_API_KEY environment variable if not set")
        print("2. Set CODEBASE_DIR to your target codebase (default: gdm/daemon)")
        print("3. Run: python -m my_agent.pipelines.full_rebuild to build vectorstore")
        print("4. Run: python -m my_agent.app to start the API server")
        print("5. Or use the agent directly: from my_agent.agent import GnomeCodeAgent\n")
    else:
        print("\n⚠️  Some tests failed. Check the errors above.\n")
    
    return passed == total


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

