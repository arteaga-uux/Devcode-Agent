from pathlib import Path
from langchain_community.vectorstores import FAISS
from langchain.vectorstores.base import VectorStoreRetriever

from .config import VECTORSTORE_PATH, CONFIG
from .embedder import get_embedding_model


def load_retriever(config = CONFIG, index_path: str = VECTORSTORE_PATH) -> VectorStoreRetriever:
    """
    Loads a FAISS vectorstore and returns a retriever with top_k from config.

    Args:
        config: CONFIG object with retrieval parameters.
        index_path: Optional path to vectorstore directory.

    Returns:
        A LangChain-compatible VectorStoreRetriever
    """
    index_dir = Path(index_path)
    if not index_dir.exists():
        raise FileNotFoundError(f"❌ Vectorstore not found at: {index_dir.resolve()}")

    embedding = get_embedding_model()
    vectorstore = FAISS.load_local(
        str(index_dir),
        embeddings=embedding,
        allow_dangerous_deserialization=True
    )

    retriever = vectorstore.as_retriever(search_kwargs={"k": config.top_k})
    return retriever
