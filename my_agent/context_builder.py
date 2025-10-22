from typing import Dict, Any
from langchain.schema import Document  # noqa: F401

from .retriever import load_retriever
from .context_formatter import format_context_from_docs
from .config import CONFIG


def build_context_for_query(
    query: str,
    config = CONFIG
) -> Dict[str, Any]:
    """
    Retrieves relevant chunks and formats them into a prompt-ready context string.

    Args:
        query: The user's question or task.
        config: CONFIG object containing retrieval and formatting parameters.

    Returns:
        {
            "context_string": str,
            "tokens": int,
            "docs": List[Document]
        }
    """
    retriever = load_retriever(config=config)
    retrieved_docs = retriever.get_relevant_documents(query)

    context_string, total_tokens = format_context_from_docs(
        docs=retrieved_docs,
        config=config
    )

    return {
        "context_string": context_string,
        "tokens": total_tokens,
        "docs": retrieved_docs
    }
