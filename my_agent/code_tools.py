# code_tools.py

from pathlib import Path
from typing import List, Dict, Any, Optional
from langchain.schema import Document  # noqa: F401
from .context_builder import build_context_for_query
from .config import CONFIG, SOURCE_DIRECTORY

class CodeTools:
    """
    Tools for the LangGraph agent to interact with code files and repository.
    """
    
    def __init__(self, source_dir: Path = SOURCE_DIRECTORY):
        self.source_dir = source_dir
    
    def read_file(self, file_path: str, start_line: Optional[int] = None, end_line: Optional[int] = None) -> Dict[str, Any]:
        """
        Read a file or specific lines from a file.
        
        Args:
            file_path: Path to file (relative to source_dir or absolute)
            start_line: Optional start line number (1-indexed)
            end_line: Optional end line number (1-indexed)
            
        Returns:
            Dict with file content, metadata, and status
        """
        try:
            # Handle both relative and absolute paths
            if not Path(file_path).is_absolute():
                full_path = self.source_dir / file_path
            else:
                full_path = Path(file_path)
            
            if not full_path.exists():
                return {
                    "success": False,
                    "error": f"File not found: {file_path}",
                    "content": "",
                    "lines": 0
                }
            
            with open(full_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            total_lines = len(lines)
            
            # Extract specific lines if requested
            if start_line is not None or end_line is not None:
                start_idx = (start_line - 1) if start_line else 0
                end_idx = end_line if end_line else total_lines
                
                # Bounds checking
                start_idx = max(0, min(start_idx, total_lines))
                end_idx = max(start_idx, min(end_idx, total_lines))
                
                selected_lines = lines[start_idx:end_idx]
                content = ''.join(selected_lines)
                line_info = f"Lines {start_idx + 1}-{end_idx} of {total_lines}"
            else:
                content = ''.join(lines)
                line_info = f"All {total_lines} lines"
            
            return {
                "success": True,
                "content": content,
                "file_path": str(full_path),
                "lines": total_lines,
                "line_info": line_info,
                "size_bytes": full_path.stat().st_size
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Error reading file: {str(e)}",
                "content": "",
                "lines": 0
            }
    
    def search_code(self, query: str, top_k: int = 5) -> Dict[str, Any]:
        """
        Search for code using semantic similarity via RAG.
        
        Args:
            query: Search query
            top_k: Number of results to return
            
        Returns:
            Dict with search results and metadata
        """
        try:
            # Use existing RAG pipeline
            context_data = build_context_for_query(query, config=CONFIG)
            
            # Format results
            results = []
            for i, doc in enumerate(context_data["docs"][:top_k]):
                results.append({
                    "rank": i + 1,
                    "content": doc.page_content,
                    "file_path": doc.metadata.get("relative_path", "unknown"),
                    "score": getattr(doc, 'score', None)  # May not be available
                })
            
            return {
                "success": True,
                "query": query,
                "results": results,
                "total_tokens": context_data["tokens"],
                "num_results": len(results)
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Search failed: {str(e)}",
                "results": [],
                "total_tokens": 0,
                "num_results": 0
            }
    
    def grep_search(self, pattern: str, file_pattern: str = "*.c", case_sensitive: bool = False) -> Dict[str, Any]:
        """
        Search for exact text patterns in files using grep-like functionality.
        
        Args:
            pattern: Text pattern to search for
            file_pattern: File pattern to search in (e.g., "*.c", "*.h")
            case_sensitive: Whether search should be case sensitive
            
        Returns:
            Dict with grep results
        """
        try:
            import re
            
            # Compile regex pattern
            flags = 0 if case_sensitive else re.IGNORECASE
            regex = re.compile(pattern, flags)
            
            results = []
            search_path = self.source_dir
            
            # Find matching files
            for file_path in search_path.rglob(file_pattern):
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        for line_num, line in enumerate(f, 1):
                            if regex.search(line):
                                results.append({
                                    "file": str(file_path.relative_to(self.source_dir)),
                                    "line": line_num,
                                    "content": line.strip(),
                                    "match": regex.search(line).group()
                                })
                except (IOError, UnicodeDecodeError):
                    continue  # Skip files that can't be read
            
            return {
                "success": True,
                "pattern": pattern,
                "file_pattern": file_pattern,
                "results": results[:50],  # Limit to 50 results
                "total_matches": len(results)
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Grep search failed: {str(e)}",
                "results": [],
                "total_matches": 0
            }
    
    def propose_edit(self, file_path: str, changes: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Propose edits to a file without actually modifying it.
        
        Args:
            file_path: Path to file to edit
            changes: List of change operations
                Each change: {"type": "replace", "start_line": 10, "end_line": 12, "new_content": "..."}
                or {"type": "insert", "line": 10, "content": "..."}
                or {"type": "delete", "start_line": 10, "end_line": 12}
        
        Returns:
            Dict with proposed diff and metadata
        """
        try:
            # Read current file
            file_result = self.read_file(file_path)
            if not file_result["success"]:
                return {
                    "success": False,
                    "error": f"Cannot read file: {file_result['error']}",
                    "diff": "",
                    "changes": []
                }
            
            current_lines = file_result["content"].splitlines()
            new_lines = current_lines.copy()
            
            # Apply changes (in reverse order to maintain line numbers)
            applied_changes = []
            for change in sorted(changes, key=lambda x: x.get("start_line", x.get("line", 0)), reverse=True):
                change_type = change["type"]
                
                if change_type == "replace":
                    start = change["start_line"] - 1  # Convert to 0-indexed
                    end = change["end_line"]
                    new_content = change["new_content"].splitlines()
                    new_lines[start:end] = new_content
                    applied_changes.append(f"Replace lines {change['start_line']}-{change['end_line']}")
                
                elif change_type == "insert":
                    line = change["line"] - 1  # Convert to 0-indexed
                    content = change["content"].splitlines()
                    new_lines[line:line] = content
                    applied_changes.append(f"Insert at line {change['line']}")
                
                elif change_type == "delete":
                    start = change["start_line"] - 1  # Convert to 0-indexed
                    end = change["end_line"]
                    del new_lines[start:end]
                    applied_changes.append(f"Delete lines {change['start_line']}-{change['end_line']}")
            
            # Generate simple diff
            diff_lines = []
            diff_lines.append(f"--- {file_path}")
            diff_lines.append(f"+++ {file_path} (proposed)")
            
            # Simple line-by-line diff
            for i, (old_line, new_line) in enumerate(zip(current_lines, new_lines)):
                if old_line != new_line:
                    diff_lines.append(f"@@ -{i+1},1 +{i+1},1 @@")
                    diff_lines.append(f"-{old_line}")
                    diff_lines.append(f"+{new_line}")
            
            return {
                "success": True,
                "file_path": file_path,
                "diff": "\n".join(diff_lines),
                "changes": applied_changes,
                "num_changes": len(applied_changes),
                "warning": "This is a proposed edit. Review before applying!"
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Edit proposal failed: {str(e)}",
                "diff": "",
                "changes": []
            }

