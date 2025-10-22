# build_vectorstore.py

from pathlib import Path
from typing import List, Optional  # noqa: F401

from langchain_community.vectorstores import FAISS
from langchain.schema import Document

from .config import VECTORSTORE_PATH
from .embedder import get_embedding_model


def build_vectorstore(
    documents: List[Document],
    persist_path: str = VECTORSTORE_PATH,
    rebuild: bool = True,
    verbose: bool = True
) -> FAISS:
    """
    Builds or loads a FAISS vectorstore from provided documents.

    - If `rebuild=True`, re-embeds and creates a new index.
    - If `rebuild=False`, loads existing index from disk (if available).
    """
    persist_dir = Path(persist_path)
    index_file = persist_dir / "index.faiss"
    metadata_file = persist_dir / "index.pkl"

    if not rebuild and index_file.exists() and metadata_file.exists():
        if verbose:
            print(f"📦 Loading existing FAISS index from: {persist_dir}")
        return FAISS.load_local(
            str(persist_dir),
            embeddings=get_embedding_model(),
            allow_dangerous_deserialization=True
        )

    if verbose:
        print("🧠 Embedding and indexing documents from scratch...")

    # Build new FAISS index from document chunks
    embedding = get_embedding_model()
    vectorstore = FAISS.from_documents(documents, embedding)

    # Save to disk
    persist_dir.mkdir(parents=True, exist_ok=True)
    vectorstore.save_local(str(persist_dir))

    if verbose:
        print(f"✅ Vectorstore saved at: {persist_dir}")

    return vectorstore
