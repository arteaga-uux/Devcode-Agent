from pathlib import Path
from typing import List, Optional
from langchain.schema import Document

from .discovery import find_source_files
from .loader import load_documents_from_paths
from .config import DEFAULT_EXTENSIONS, DEFAULT_EXCLUDES, DEFAULT_MAX_FILE_SIZE_KB, CONFIG


def ingest(
    project: Path,
    config: Optional [CONFIG] = None,
    verbose: Optional[bool] = None
) -> List[Document]:
    """
    Main ingestion function: finds and loads documents from the specified project folder.

    Args:
        project: Path to the root of the source project.
        config: CONFIG object
        verbose: Optional override for config.verbose for CLI/backwards-compat.

    Returns:
        List of LangChain Document objects.
    """
    active_config = config or CONFIG
    if verbose is not None:
        active_config.verbose = verbose

    file_paths = find_source_files(
        base_path=project,
        valid_extensions=set(DEFAULT_EXTENSIONS),
        exclude_dirs=set(DEFAULT_EXCLUDES),
        max_file_size_kb=DEFAULT_MAX_FILE_SIZE_KB
    )

    documents = load_documents_from_paths(file_paths)

    if active_config.verbose:
        print(f"\n📂 Ingested {len(documents)} files")

    return documents


# Optional: make this callable from CLI
if __name__ == "__main__":
    import argparse
    from .config import CONFIG

    parser = argparse.ArgumentParser()
    parser.add_argument("--project", "-p", type=Path, required=True)
    parser.add_argument("--verbose", "-v", action="store_true")

    args = parser.parse_args()

    # Override config verbosity from CLI flag if needed
    config = CONFIG
    config.verbose = args.verbose

    ingest(
        project=args.project,
        config=config
    )
