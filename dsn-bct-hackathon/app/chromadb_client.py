import os
import hashlib
from typing import Any

import chromadb
from dotenv import load_dotenv
from chromadb.utils import embedding_functions


_ef = embedding_functions.DefaultEmbeddingFunction()
_embed_cache: dict[str, list[float]] = {}


def _embedding_cache_key(text: str) -> str:
    normalized = " ".join(str(text or "").lower().strip().split())
    return hashlib.md5(normalized.encode()).hexdigest()


def get_cached_embedding(text: str) -> list[float]:
    clean_text = " ".join(str(text or "").strip().split())
    key = _embedding_cache_key(clean_text)
    print(f"[EMBED] key: '{key[:16]}...' query: '{clean_text[:40]}'")
    print(f"[EMBED] cache size: {len(_embed_cache)}, key hit: {key in _embed_cache}")
    if key in _embed_cache:
        print("[EMBED] CACHE HIT - skipping embedding generation")
        return _embed_cache[key]

    print("[EMBED] CACHE MISS - generating embedding")
    _embed_cache[key] = _ef([clean_text])[0]
    return _embed_cache[key]


def clear_embedding_cache() -> None:
    _embed_cache.clear()


def prewarm_embedding_model() -> None:
    _ef(["warmup"])
    print("[Startup] Embedding model pre-warmed")


def _distance_to_similarity(distance: float, collection: Any | None = None) -> float:
    metadata = getattr(collection, "metadata", None) or {}
    space = str(metadata.get("hnsw:space") or metadata.get("space") or "").lower()
    if space == "cosine":
        score = 1.0 - distance
    else:
        score = 1.0 / (1.0 + (distance / 4.0))
    return max(0.0, min(1.0, score))


class VectorStore:
    """ChromaDB wrapper for indexing and searching recommendation items."""

    def __init__(self) -> None:
        load_dotenv()
        self.collection_name = "items"
        self.client: Any | None = None
        self.collection: Any | None = None
        self.connection_error: str | None = None

        self._connect()

    def _connect(self) -> None:
        use_local = os.getenv("USE_LOCAL_CHROMA", "true").strip().lower() in ("true", "1", "yes")
        persist_path = os.getenv("CHROMA_PERSIST_PATH", "./chroma")

        try:
            if use_local:
                self.client = chromadb.PersistentClient(path=persist_path)
                self.collection = self.client.get_or_create_collection(name=self.collection_name)
                self.connection_error = None
                print(f"Connected to local ChromaDB persistent store at {persist_path}")
                return

            host = os.getenv("CHROMA_HOST", "chromadb").strip() or "chromadb"
            port = int(os.getenv("CHROMA_PORT", "8000"))
            self._connect_http(host=host, port=port)
        except Exception as exc:
            if not use_local and os.getenv("CHROMA_HOST") is None:
                try:
                    self._connect_http(host="localhost", port=8000)
                    print("Connected to ChromaDB at localhost:8000")
                    return
                except Exception as fallback_exc:
                    self.connection_error = f"ChromaDB connection error: {fallback_exc}"
                    return

            self.connection_error = f"ChromaDB connection error: {exc}"

    def _connect_http(self, host: str, port: int) -> None:
        self.client = chromadb.HttpClient(host=host, port=port)
        self.collection = self.client.get_or_create_collection(name=self.collection_name)
        self.connection_error = None
        print(f"Connected to ChromaDB at {host}:{port}")

    def add_items(self, items: list[dict]) -> dict:
        if self.connection_error or self.collection is None:
            return {"success": False, "error": self.connection_error or "ChromaDB collection unavailable."}

        valid_items = [
            item
            for item in items
            if item.get("id") and (item.get("document") or item.get("text"))
        ]
        if not valid_items:
            return {"success": False, "error": "No valid items provided. Each item needs id and document."}

        try:
            self.collection.upsert(
                ids=[str(item["id"]) for item in valid_items],
                documents=[str(item.get("document") or item.get("text")) for item in valid_items],
                metadatas=[item.get("metadata", {}) for item in valid_items],
            )
            return {"success": True, "indexed": len(valid_items)}
        except Exception as exc:
            return {"success": False, "error": f"ChromaDB add_items error: {exc}"}

    def search(
        self,
        query: str,
        n_results: int = 10,
        where: dict | None = None,
        min_score: float | None = None,
    ) -> list[dict]:
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
            embedding = get_cached_embedding(query)
            query_kwargs: dict[str, Any] = {
                "query_embeddings": [embedding],
                "n_results": max(1, n_results),
                "include": ["documents", "metadatas", "distances"],
            }
            if where:
                query_kwargs["where"] = where

            results = self.collection.query(**query_kwargs)
            ids = results.get("ids", [[]])[0]
            documents = results.get("documents", [[]])[0]
            metadatas = results.get("metadatas", [[]])[0]
            distances = results.get("distances", [[]])[0]

            matches: list[dict] = []
            for index, item_id in enumerate(ids):
                distance = distances[index] if index < len(distances) and distances[index] is not None else None
                score = _distance_to_similarity(float(distance), self.collection) if distance is not None else 0.0
                metadata = metadatas[index] if index < len(metadatas) and metadatas[index] else {}
                name = metadata.get("name") or metadata.get("title") or item_id
                if distance is not None:
                    print(f"  {name}: dist={float(distance):.4f} sim={score:.4f}")
                if min_score is not None and score < min_score:
                    continue
                matches.append(
                    {
                        "id": item_id,
                        "document": documents[index] if index < len(documents) else "",
                        "text": documents[index] if index < len(documents) else "",
                        "metadata": metadata,
                        "score": round(score, 4),
                        "distance": distance,
                    }
                )

            return matches
        except Exception as exc:
            return [
                {
                    "id": "search-error",
                    "document": "",
                    "text": "",
                    "metadata": {"error": f"ChromaDB search error: {exc}"},
                    "score": 0.0,
                }
            ]

    def get_collection_count(self) -> int:
        if self.connection_error or self.collection is None:
            return 0

        try:
            return int(self.collection.count())
        except Exception:
            return 0
