import os
from typing import Any

import chromadb
from dotenv import load_dotenv


class VectorStore:
    """ChromaDB wrapper for indexing and searching recommendation items."""

    def __init__(self) -> None:
        load_dotenv()
        self.collection_name = "items"
        self.client: Any | None = None
        self.collection: Any | None = None
        self.connection_error: str | None = None

        try:
            use_local = os.getenv("USE_LOCAL_CHROMA", "false").strip().lower() == "true"
            if use_local:
                self.client = chromadb.Client()
            else:
                self.client = chromadb.HttpClient(host="chromadb", port=8000)

            self.collection = self.client.get_or_create_collection(name=self.collection_name)
        except Exception as exc:
            self.connection_error = f"ChromaDB connection error: {exc}"

    def add_items(self, items: list[dict]) -> dict:
        if self.connection_error or self.collection is None:
            return {"success": False, "error": self.connection_error or "ChromaDB collection unavailable."}

        valid_items = [item for item in items if item.get("id") and item.get("text")]
        if not valid_items:
            return {"success": False, "error": "No valid items provided. Each item needs id and text."}

        try:
            self.collection.upsert(
                ids=[str(item["id"]) for item in valid_items],
                documents=[str(item["text"]) for item in valid_items],
                metadatas=[item.get("metadata", {}) for item in valid_items],
            )
            return {"success": True, "indexed": len(valid_items)}
        except Exception as exc:
            return {"success": False, "error": f"ChromaDB add_items error: {exc}"}

    def search(self, query: str, n_results: int = 10) -> list[dict]:
        if self.connection_error or self.collection is None:
            return [
                {
                    "id": "vector-store-unavailable",
                    "text": "",
                    "metadata": {"error": self.connection_error or "ChromaDB collection unavailable."},
                    "score": 0.0,
                }
            ]

        try:
            results = self.collection.query(query_texts=[query], n_results=max(1, n_results))
            ids = results.get("ids", [[]])[0]
            documents = results.get("documents", [[]])[0]
            metadatas = results.get("metadatas", [[]])[0]
            distances = results.get("distances", [[]])[0]

            matches: list[dict] = []
            for index, item_id in enumerate(ids):
                distance = distances[index] if index < len(distances) and distances[index] is not None else None
                score = 1.0 / (1.0 + float(distance)) if distance is not None else 0.0
                matches.append(
                    {
                        "id": item_id,
                        "text": documents[index] if index < len(documents) else "",
                        "metadata": metadatas[index] if index < len(metadatas) and metadatas[index] else {},
                        "score": round(score, 4),
                    }
                )

            return matches
        except Exception as exc:
            return [{"id": "search-error", "text": "", "metadata": {"error": f"ChromaDB search error: {exc}"}, "score": 0.0}]

    def get_collection_count(self) -> int:
        if self.connection_error or self.collection is None:
            return 0

        try:
            return int(self.collection.count())
        except Exception:
            return 0
