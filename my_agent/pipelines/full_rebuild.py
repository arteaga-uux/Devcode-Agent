# pipeline.py

from pathlib import Path

from ingest_project import ingest as ingest_documents
from chunking import chunk_documents
from build_vectorstore import build_vectorstore
from config import CONFIG, SOURCE_DIRECTORY, VECTORSTORE_PATH

# === Configuration ===
PROJECT_PATH = SOURCE_DIRECTORY  # Root of the GNOME code/docs project
REBUILD = True  # Force fresh embedding + indexing every run

def main():
    print("🚀 Phase 1: Ingesting project files...")
    documents = ingest_documents(project=PROJECT_PATH, config=CONFIG)

    print("\n🧩 Phase 2: Chunking documents...")
    chunks = chunk_documents(documents, config=CONFIG, verbose=True)

    print("\n🧠 Phase 3: Building vectorstore...")
    vectorstore = build_vectorstore(documents=chunks, persist_path=str(VECTORSTORE_PATH), rebuild=REBUILD)

    print("✅ Vectorstore ready. You can now use retriever or agent modules.")

if __name__ == "__main__":
    main()