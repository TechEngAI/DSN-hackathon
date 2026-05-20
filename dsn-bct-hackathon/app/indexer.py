from app.formatter import format_relational_row_for_chroma


class Indexer:
    """Indexes formatted business records into ChromaDB."""

    def __init__(self, vector_store, data_loader) -> None:
        self.vector_store = vector_store
        self.data_loader = data_loader

    def index_businesses(self, businesses: list[dict], batch_size: int = 100) -> None:
        if getattr(self.vector_store, "connection_error", None):
            print(f"Indexing skipped: {self.vector_store.connection_error}")
            print(f"ChromaDB collection count: {self.vector_store.get_collection_count()}")
            return

        indexed_so_far = 0

        for start in range(0, len(businesses), batch_size):
            batch = businesses[start : start + batch_size]
            formatted_items: list[dict] = []

            for business in batch:
                try:
                    formatted = format_relational_row_for_chroma(business)
                    metadata = formatted.get("metadata", {})
                    metadata["business_id"] = str(business.get("business_id", formatted.get("id", "")))
                    metadata["name"] = str(business.get("name", "Unknown Business"))
                    formatted_items.append(
                        {
                            "id": str(formatted["id"]),
                            "document": str(formatted["document"]),
                            "metadata": metadata,
                        }
                    )
                except Exception:
                    continue

            if not formatted_items:
                continue

            try:
                result = self.vector_store.add_items(formatted_items)
                if isinstance(result, dict) and result.get("success") is False:
                    print(f"Index batch skipped: {result.get('error', 'unknown indexing error')}")
                else:
                    indexed_so_far += len(formatted_items)
                    print(f"Indexed {indexed_so_far} businesses so far...")
            except Exception:
                continue

        print(f"ChromaDB collection count: {self.vector_store.get_collection_count()}")

    def is_indexed(self) -> bool:
        try:
            return self.vector_store.get_collection_count() > 100
        except Exception:
            return False
