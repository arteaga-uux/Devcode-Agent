from typing import List, Tuple
from langchain.schema import Document
from .utils.token_counter import count_tokens
from .config import CONFIG


def format_context_from_docs(
    docs: List[Document],
    config = CONFIG
) -> Tuple[str, int]:
    """
    Formats retrieved documents into a token-efficient context string.

    Args:
        docs: List of LangChain Document objects.
        config: CONFIG object with context construction parameters.

    Returns:
        Tuple of (context string, total tokens used).
    """
    used_tokens = 0
    formatted_chunks = []
    seen_chunks = set()

    for doc in docs:
        raw_content = doc.page_content.strip()

        if raw_content in seen_chunks:
            continue
        seen_chunks.add(raw_content)

        path = doc.metadata.get("relative_path") or doc.metadata.get("source", "unknown")
        header = f"\n[FILE: {path}]\n" if config.include_sources else ""

        ext = path.split(".")[-1].lower()
        if ext in {"c", "h", "cpp", "sh"}:
            chunk = f"{header}```{ext}\n{raw_content}\n```"
        else:
            chunk = f"{header}{raw_content}"

        chunk_tokens = count_tokens(chunk, model_name=getattr(config, "token_count_model", "gpt-4o-mini"))

        if used_tokens + chunk_tokens > config.max_tokens:
            break

        formatted_chunks.append(chunk)
        used_tokens += chunk_tokens

    context_string = "\n\n".join(formatted_chunks)
    return context_string, used_tokens
