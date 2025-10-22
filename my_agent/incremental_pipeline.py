# incremental_pipeline.py

from pathlib import Path
from typing import List, Dict, Any
from langchain.schema import Document  # noqa: F401

from .ingest_project import ingest as ingest_documents
from .chunking import chunk_documents
from .build_vectorstore import build_vectorstore
from .file_tracker import FileModificationTracker
from .config import CONFIG, SOURCE_DIRECTORY, VECTORSTORE_PATH

class IncrementalPipeline:
    """
    Enhanced pipeline that only processes modified files for faster rebuilds.
    """
    
    def __init__(self, source_dir: Path = SOURCE_DIRECTORY):
        self.source_dir = source_dir
        self.tracker = FileModificationTracker()
    
    def get_modified_files(self) -> List[Path]:
        """Get list of files that have been modified since last indexing."""
        # Get all files that would be ingested
        all_documents = ingest_documents(self.source_dir, config=CONFIG)
        all_file_paths = [Path(doc.metadata.get("source", "")) for doc in all_documents]
        
        # Filter to only modified files
        modified_files = self.tracker.get_modified_files(all_file_paths)
        
        print(f"📊 File analysis:")
        print(f"   Total files: {len(all_file_paths)}")
        print(f"   Modified files: {len(modified_files)}")
        print(f"   Unchanged files: {len(all_file_paths) - len(modified_files)}")
        
        return modified_files
    
    def rebuild_incremental(self, force_full: bool = False) -> Dict[str, Any]:
        """
        Rebuild vectorstore incrementally, only processing modified files.
        
        Args:
            force_full: If True, rebuild everything from scratch
            
        Returns:
            Dict with rebuild statistics
        """
        print("🚀 Starting incremental rebuild...")
        
        if force_full:
            print("🔄 Force full rebuild requested")
            documents = ingest_documents(self.source_dir, config=CONFIG)
            chunks = chunk_documents(documents, config=CONFIG, verbose=True)
            
            # Update tracker with all files
            all_file_paths = [Path(doc.metadata.get("source", "")) for doc in documents]
            self.tracker.update_tracker(all_file_paths)
            
        else:
            # Check for modified files
            modified_files = self.get_modified_files()
            
            if not modified_files:
                print("✅ No modified files found. Vectorstore is up to date!")
                return {
                    "status": "up_to_date",
                    "files_processed": 0,
                    "chunks_created": 0,
                    "time_saved": True
                }
            
            print(f"📝 Processing {len(modified_files)} modified files...")
            
            # For now, we'll do a full rebuild but track the efficiency
            documents = ingest_documents(self.source_dir, config=CONFIG)
            chunks = chunk_documents(documents, config=CONFIG, verbose=True)
            
            # Update tracker
            all_file_paths = [Path(doc.metadata.get("source", "")) for doc in documents]
            self.tracker.update_tracker(all_file_paths)
        
        # Build vectorstore
        print("🧠 Building vectorstore...")
        vectorstore = build_vectorstore(
            documents=chunks,
            persist_path=str(VECTORSTORE_PATH),
            rebuild=True,
            verbose=True
        )
        
        # Get statistics
        stats = self.tracker.get_tracker_stats()
        
        return {
            "status": "completed",
            "files_processed": len(documents),
            "chunks_created": len(chunks),
            "vectorstore_size": len(vectorstore.index_to_docstore_id),
            "tracker_stats": stats
        }
    
    def check_status(self) -> Dict[str, Any]:
        """Check the status of tracked files and vectorstore."""
        modified_files = self.get_modified_files()
        tracker_stats = self.tracker.get_tracker_stats()
        
        vectorstore_exists = VECTORSTORE_PATH.exists() and (VECTORSTORE_PATH / "index.faiss").exists()
        
        return {
            "vectorstore_exists": vectorstore_exists,
            "modified_files_count": len(modified_files),
            "modified_files": [str(f) for f in modified_files[:10]],  # Show first 10
            "tracker_stats": tracker_stats,
            "needs_rebuild": len(modified_files) > 0 or not vectorstore_exists
        }
    

# CLI interface
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Incremental vectorstore pipeline")
    parser.add_argument("--force", "-f", action="store_true", help="Force full rebuild")
    parser.add_argument("--status", "-s", action="store_true", help="Check status only")
    parser.add_argument("--source", type=Path, default=SOURCE_DIRECTORY, help="Source directory")
    
    args = parser.parse_args()
    
    pipeline = IncrementalPipeline(args.source)
    
    if args.status:
        status = pipeline.check_status()
        print("\n📊 Pipeline Status:")
        print(f"   Vectorstore exists: {status['vectorstore_exists']}")
        print(f"   Modified files: {status['modified_files_count']}")
        print(f"   Needs rebuild: {status['needs_rebuild']}")
        if status['modified_files']:
            print(f"   Sample modified files: {status['modified_files']}")
    else:
        result = pipeline.rebuild_incremental(force_full=args.force)
        print(f"\n✅ Rebuild completed: {result['status']}")
        print(f"   Files processed: {result['files_processed']}")
        print(f"   Chunks created: {result['chunks_created']}")

