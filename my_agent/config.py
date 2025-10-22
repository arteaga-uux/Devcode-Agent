from pathlib import Path
from typing import Set
from dataclasses import dataclass
import os

# === Environment Configuration ===
DEBUG_MODE: bool = os.getenv("DEBUG", "true").lower() == "true"
OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
OPENAI_ASSISTANT_ID: str = os.getenv("OPENAI_ASSISTANT_ID", "")

# === Paths Configuration ===
PROJECT_ROOT = Path(__file__).resolve().parent
VECTORSTORE_PATH: Path = PROJECT_ROOT / "vectorstore" / "faiss_index"
# Configurable codebase root for RAG ingestion; default to gdm/daemon
_CODEBASE_DIR = os.getenv("CODEBASE_DIR", str(PROJECT_ROOT / "gdm" / "daemon"))
SOURCE_DIRECTORY: Path = Path(_CODEBASE_DIR)
TRACKER_FILE: Path = PROJECT_ROOT / "vectorstore" / "file_tracker.json"

# === Model Configuration ===
EMBEDDING_MODEL_NAME: str = "text-embedding-3-small"
GENERATION_MODEL_NAME: str = "gpt-4o-mini"

# === Ingestion Configuration ===
DEFAULT_EXTENSIONS: Set[str] = {
    ".c", ".h", ".cpp", ".cc", ".sh", ".py",
    ".build", ".md", ".txt", ".xml", ".ini", ".conf",
    ".json", ".yaml", ".yml", ".service", ".desktop"
}

DEFAULT_EXCLUDES: Set[str] = {
    ".git", "__pycache__", "po", "docs", "locale",
    "node_modules", "dist", "build", ".venv", ".mypy_cache"
}

NOISY_EXTENSIONS: Set[str] = {
    ".po", ".mo", ".png", ".svg", ".jpg", ".log"
}

DEFAULT_MAX_FILE_SIZE_KB: int = 1024  # 1MB

# === Agent Configuration ===
@dataclass
class AgentConfig:
    # RAG settings
    top_k: int = 4 if DEBUG_MODE else 15
    max_tokens: int = 5000 if DEBUG_MODE else 100_000
    chunk_size: int = 300
    chunk_overlap: int = 50
    
    # Model settings
    model_name: str = GENERATION_MODEL_NAME
    temperature: float = 0.0
    token_count_model: str = GENERATION_MODEL_NAME
    
    # Behavior settings
    include_sources: bool = True
    verbose: bool = True
    
    # Code tools settings
    max_file_size_mb: int = 10
    max_search_results: int = 50
    max_grep_results: int = 100
    
    # Safety settings
    allow_file_modification: bool = False  # Only propose, never modify
    require_confirmation_for_edits: bool = True

# === Active Configuration ===
CONFIG = AgentConfig()