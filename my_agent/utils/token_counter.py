# token_counter.py

import tiktoken
from typing import Optional


def count_tokens(text: str, model_name: str = "gpt-4o-mini") -> int:
    """
    Count the number of tokens in a text string for a given model.
    
    Args:
        text: The text to count tokens for.
        model_name: The model name to use for tokenization (default: gpt-4o-mini).
        
    Returns:
        Number of tokens in the text.
    """
    try:
        encoding = tiktoken.encoding_for_model(model_name)
    except KeyError:
        # Fallback to cl100k_base encoding (used by gpt-4, gpt-3.5-turbo, etc.)
        encoding = tiktoken.get_encoding("cl100k_base")
    
    return len(encoding.encode(text))

