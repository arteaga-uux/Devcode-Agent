# discovery.py

from pathlib import Path
from typing import List, Set, Optional


def find_source_files(
    base_path: Path,
    valid_extensions: Optional[Set[str]] = None,
    exclude_dirs: Optional[Set[str]] = None,
    max_file_size_kb: int = 1024
 ) -> List[Path]:
    """
    Recursively finds source files within a project directory.

    Args:
        base_path (Path): The root of the project folder.
        valid_extensions (Set[str], optional): Set of file extensions to include (e.g. {".c", ".h"}).
                                               If None, includes all extensions.
        exclude_dirs (Set[str], optional): Set of directory names to skip (e.g. {"po", ".git"}).
        max_file_size_kb (int): Maximum file size (in KB) to include.

    Returns:
        List[Path]: All matching file paths.
    """
    base_path = base_path.resolve()
    if not base_path.is_dir():
        raise ValueError(f"Provided base path is not a directory: {base_path}")

    exclude_dirs = exclude_dirs or set()
    found_files = []

    for path in base_path.rglob("*"):
        # Skip directories entirely
        if path.is_dir():
            if path.name in exclude_dirs:
                continue
            else:
                continue  # walk handles this already

        # Skip if parent is in excluded folders
        if any(excluded in path.parts for excluded in exclude_dirs):
            continue

        # Filter by extension (if given)
        if valid_extensions and path.suffix.lower() not in valid_extensions:
            continue

        # Filter by file size
        try:
            size_kb = path.stat().st_size / 1024
            if max_file_size_kb is not None and size_kb > max_file_size_kb:
                continue
        except OSError:
            continue  # ignore unreadable files

        found_files.append(path)

    return found_files