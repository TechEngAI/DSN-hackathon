from app.amazon_loader import AmazonDataLoader


class AmazonIndexer:
    def __init__(self, vector_store) -> None:
        self.vector_store = vector_store
        self.loader = AmazonDataLoader()

    def index_products(self, products: list[dict], batch_size: int = 100) -> None:
        if getattr(self.vector_store, "connection_error", None):
            print(f"Amazon indexing skipped: {self.vector_store.connection_error}")
            print(f"ChromaDB collection count: {self.vector_store.get_collection_count()}")
            return

        indexed_so_far = 0
        for start in range(0, len(products), batch_size):
            batch = products[start : start + batch_size]
            formatted_items: list[dict] = []

            for product in batch:
                try:
                    formatted = self.loader.format_for_chroma(product)
                    raw_id = str(formatted.get("id") or "").strip()
                    if not raw_id:
                        continue
                    formatted["id"] = f"amz_{raw_id}" if not raw_id.startswith("amz_") else raw_id
                    formatted["metadata"]["product_id"] = raw_id
                    formatted_items.append(formatted)
                except Exception:
                    continue

            if not formatted_items:
                continue

            try:
                result = self.vector_store.add_items(formatted_items)
                if isinstance(result, dict) and result.get("success") is False:
                    print(f"Amazon index batch skipped: {result.get('error', 'unknown indexing error')}")
                else:
                    indexed_so_far += len(formatted_items)
                    print(f"Indexed {indexed_so_far} Amazon products so far...")
            except Exception:
                continue

        print(f"ChromaDB collection count: {self.vector_store.get_collection_count()}")

    def is_amazon_indexed(self) -> bool:
        try:
            results = self.vector_store.search("amazon product", n_results=1)
        except Exception:
            return False

        return any((result.get("metadata") or {}).get("domain") == "amazon" for result in results)
