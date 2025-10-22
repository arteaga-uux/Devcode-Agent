
import os
from dotenv import load_dotenv
from typing import Any

from .config import EMBEDDING_MODEL_NAME

# Load .env variables into environment
load_dotenv()

def get_embedding_model() -> Any:
	"""Return a placeholder embedding model or actual model based on config.
	This is a minimal stub to keep imports working; replace with real impl as needed.
	"""
	try:
		from langchain_openai import OpenAIEmbeddings
		return OpenAIEmbeddings(model=EMBEDDING_MODEL_NAME)
	except Exception:
		class _Dummy:
			def embed_query(self, text: str):
				return [0.0]
		return _Dummy()