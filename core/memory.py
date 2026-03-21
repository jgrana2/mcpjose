import os
import sqlite3
import chromadb
from pathlib import Path
from typing import Any, Dict, List, Optional
from langchain_chroma import Chroma
from langchain_openai import OpenAIEmbeddings
from core.config import get_config


class MemoryService:
    def __init__(self):
        self.config = get_config()
        # Ensure repo_root is a Path object
        if not isinstance(self.config.repo_root, Path):
            self.data_dir = Path(self.config.repo_root) / "data"
        else:
            self.data_dir = self.config.repo_root / "data"
        self.data_dir.mkdir(exist_ok=True)

        # Initialize SQLite
        self.db_path = self.data_dir / "memory.db"
        self._init_sqlite()

        # Initialize ChromaDB
        self.chroma_path = self.data_dir / "chroma"
        self.chroma_client = chromadb.PersistentClient(path=str(self.chroma_path))
        # Use openai_api_key directly from config if available, otherwise fallback
        api_key = self.config.openai_api_key or os.environ.get("OPENAI_API_KEY")

        # OpenAIEmbeddings might need the key passed via api_key
        # If it fails, langchain_openai might be configured to pick up OPENAI_API_KEY from env
        self.embeddings = OpenAIEmbeddings(openai_api_key=api_key)
        self.vector_store = Chroma(
            client=self.chroma_client,
            collection_name="interaction_history",
            embedding_function=self.embeddings,
        )

    def _init_sqlite(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS user_prefs (
                    key TEXT PRIMARY KEY,
                    value TEXT,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS project_ctx (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    filename TEXT,
                    summary TEXT,
                    tags TEXT
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    vector_id TEXT,
                    summary TEXT
                )
            """)

    def save_interaction(
        self, summary: str, content: str, metadata: Optional[Dict[str, Any]] = None
    ):
        """Save interaction to both VectorDB and SQLite."""
        # Save to VectorDB
        if metadata is None:
            metadata = {}
        vector_id = self.vector_store.add_texts(texts=[content], metadatas=[metadata])[
            0
        ]

        # Save to SQLite
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT INTO history (vector_id, summary) VALUES (?, ?)",
                (vector_id, summary),
            )

    def query_memory(self, query: str, n_results: int = 3) -> List[Dict[str, Any]]:
        """Query memory using semantic search."""
        results = self.vector_store.similarity_search(query, k=n_results)
        return [{"content": r.page_content, "metadata": r.metadata} for r in results]
