# loader.py

from pathlib import Path
from typing import List
from langchain.schema import Document


def load_documents_from_paths(paths: List[Path]) -> List[Document]:
    """
    Reads content from a list of file paths and returns them as LangChain Documents.

    Args:
        paths (List[Path]): List of source file paths to read.

    Returns:
        List[Document]: Each Document contains file content and metadata.
    """
    documents = []

    for path in paths:
        try:
            with open(path, "r", encoding="utf-8", errors="replace") as f:
                text = f.read()
        except Exception as e:
            print(f"⚠️ Could not read file: {path} — {e}")
            continue

        # Derive metadata
        relative_path = path.relative_to(path.anchor) if path.is_absolute() else path
        metadata = {
         "file_path": str(path.resolve()),
         "relative_path": str(relative_path),
         "extension": path.suffix.lower(),
         "folder": path.parent.name,
          "filename": path.name,
          "source": str(path.resolve()),  # 👈 necesario para chunking por headers
        }

        documents.append(Document(page_content=text, metadata=metadata))

    return documents