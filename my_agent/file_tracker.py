# file_tracker.py

import hashlib
import json
from pathlib import Path
from typing import Dict, Set, List, Optional
from datetime import datetime

class FileModificationTracker:
    """
    Tracks file modifications to enable incremental vectorization.
    Only re-processes files that have changed since last indexing.
    """
    
    def __init__(self, tracker_file: Path = None):
        self.tracker_file = tracker_file or Path("vectorstore/file_tracker.json")
        self.tracker_file.parent.mkdir(parents=True, exist_ok=True)
        self.file_metadata = self._load_tracker()
    
    def _load_tracker(self) -> Dict[str, Dict]:
        """Load existing file metadata from disk."""
        if self.tracker_file.exists():
            try:
                with open(self.tracker_file, 'r') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                return {}
        return {}
    
    def _save_tracker(self):
        """Save file metadata to disk."""
        with open(self.tracker_file, 'w') as f:
            json.dump(self.file_metadata, f, indent=2)
    
    def _get_file_hash(self, file_path: Path) -> str:
        """Calculate SHA256 hash of file content."""
        try:
            with open(file_path, 'rb') as f:
                return hashlib.sha256(f.read()).hexdigest()
        except (IOError, OSError):
            return ""
    
    def _get_file_metadata(self, file_path: Path) -> Dict:
        """Get current file metadata."""
        try:
            stat = file_path.stat()
            return {
                "mtime": stat.st_mtime,
                "size": stat.st_size,
                "hash": self._get_file_hash(file_path)
            }
        except (OSError, IOError):
            return {"mtime": 0, "size": 0, "hash": ""}
    
    def get_modified_files(self, file_paths: List[Path]) -> List[Path]:
        """
        Return list of files that have been modified since last tracking.
        
        Args:
            file_paths: List of file paths to check
            
        Returns:
            List of modified file paths
        """
        modified_files = []
        
        for file_path in file_paths:
            file_str = str(file_path)
            current_metadata = self._get_file_metadata(file_path)
            
            # File is new or modified if:
            # 1. Not in tracker
            # 2. Hash changed
            # 3. Size changed
            # 4. Modification time changed significantly
            if (file_str not in self.file_metadata or
                current_metadata["hash"] != self.file_metadata[file_str].get("hash", "") or
                current_metadata["size"] != self.file_metadata[file_str].get("size", 0) or
                abs(current_metadata["mtime"] - self.file_metadata[file_str].get("mtime", 0)) > 1.0):
                
                modified_files.append(file_path)
        
        return modified_files
    
    def update_tracker(self, file_paths: List[Path]):
        """
        Update tracker with current metadata for given files.
        
        Args:
            file_paths: List of file paths to update in tracker
        """
        for file_path in file_paths:
            file_str = str(file_path)
            self.file_metadata[file_str] = self._get_file_metadata(file_path)
        
        self._save_tracker()
    
    def get_tracker_stats(self) -> Dict:
        """Get statistics about tracked files."""
        total_files = len(self.file_metadata)
        total_size = sum(meta.get("size", 0) for meta in self.file_metadata.values())
        last_updated = max(
            (meta.get("mtime", 0) for meta in self.file_metadata.values()),
            default=0
        )
        
        return {
            "total_files": total_files,
            "total_size_bytes": total_size,
            "last_updated": datetime.fromtimestamp(last_updated).isoformat() if last_updated else None,
            "tracker_file": str(self.tracker_file)
        }
    
    def cleanup_missing_files(self, existing_files: Set[Path]):
        """
        Remove entries for files that no longer exist.
        
        Args:
            existing_files: Set of file paths that currently exist
        """
        existing_strs = {str(f) for f in existing_files}
        to_remove = [f for f in self.file_metadata.keys() if f not in existing_strs]
        
        for file_str in to_remove:
            del self.file_metadata[file_str]
        
        if to_remove:
            self._save_tracker()
            print(f"🧹 Cleaned up {len(to_remove)} missing files from tracker")

