from typing import List
from langchain.schema import Document
from langchain.text_splitter import (
    RecursiveCharacterTextSplitter,
    MarkdownHeaderTextSplitter,
)

from .code_splitter import split_c_code_by_function
from .config import CONFIG # 👈 importás el tipo, no la instancia

def chunk_documents(
    documents: List[Document],
    config: CONFIG,
    verbose: bool = False
) -> List[Document]:
    """
    Splits documents into LLM-sized chunks using appropriate strategies.
    - Markdown files: markdown-aware splitting
    - C/C++ source files: function-aware chunking
    - Everything else: recursive character-based splitting

    Args:
        documents: Raw file-level documents to chunk.
        config: CONFIG object with chunking parameters.
        verbose: Whether to log chunking operations.

    Returns:
        Smaller chunked documents with inherited metadata.
    """
    if verbose or config.verbose:
        print(f"🔹 Chunking {len(documents)} documents with chunk size {config.chunk_size} and overlap {config.chunk_overlap}...")

    recursive_splitter = RecursiveCharacterTextSplitter(
        chunk_size=config.chunk_size,
        chunk_overlap=config.chunk_overlap
    )

    headers = [
        ("#", "Header 1"),
        ("##", "Header 2"),
        ("###", "Header 3"),
    ]

    all_chunks = []

    for doc in documents:
        ext = doc.metadata.get("extension", "").lower()

        if ext == ".md":
            md_splitter = MarkdownHeaderTextSplitter(headers_to_split_on=headers)
            header_chunks = md_splitter.split_text(doc.page_content)

            chunks = [
                Document(page_content=chunk.page_content, metadata=doc.metadata.copy())
                for chunk in header_chunks
            ]

        elif ext in [".c", ".h"]:
            chunks = split_c_code_by_function(doc)

        else:
            chunks = recursive_splitter.split_documents([doc])

        for chunk in chunks:
            chunk.metadata.update(doc.metadata)

        all_chunks.extend(chunks)

    return all_chunks
