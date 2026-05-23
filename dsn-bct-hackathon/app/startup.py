from pathlib import Path
import chromadb
import time
import os

from app.amazon_indexer import AmazonIndexer
from app.amazon_loader import AmazonDataLoader
from app.chromadb_client import VectorStore
from app.cold_start import ColdStartHandler
from app.data_loader import YelpDataLoader
from app.indexer import Indexer
from app.llm_client import LLMClient
from app.user_history import UserHistory


app_state = {}


def log_chromadb_mode(client, collection):
    """
    Log ChromaDB connection mode and validate it is working.
    Run this at app startup before any requests are served.
    """
    try:
        client_type = type(client).__name__ if client is not None else "None"

        if "HttpClient" in client_type or "HTTP" in client_type:
            mode = "HTTP (remote)"
            warning = (
                "WARNING: Using HTTP ChromaDB client. "
                "Every query adds network overhead (~200-500ms). "
                "Switch to PersistentClient if data is local."
            )
        elif "Persistent" in client_type:
            mode = "PersistentClient (local)"
            warning = None
        elif "Ephemeral" in client_type or "Memory" in client_type:
            mode = "EphemeralClient (in-memory)"
            warning = (
                "WARNING: Using in-memory ChromaDB. "
                "All data will be lost on restart."
            )
        else:
            mode = f"Unknown ({client_type})"
            warning = "WARNING: Unrecognized ChromaDB client type."

        print(f"[ChromaDB] Mode       : {mode}")
        print(f"[ChromaDB] Client type: {client_type}")

        try:
            t0 = time.time()
            count = collection.count() if collection is not None else 0
            elapsed = (time.time() - t0) * 1000
            print(f"[ChromaDB] Collection : {getattr(collection, 'name', 'unknown')}")
            print(f"[ChromaDB] Documents  : {count}")
            print(f"[ChromaDB] Count query: {elapsed:.0f}ms")

            if count == 0:
                print("[ChromaDB] CRITICAL: Collection is empty.")
            elif elapsed > 500:
                print(
                    f"[ChromaDB] Count took {elapsed:.0f}ms. "
                    f"HTTP overhead detected. Consider PersistentClient."
                )
            else:
                print("[ChromaDB] Collection healthy.")

        except Exception as e:
            print(f"[ChromaDB] ERROR: Could not connect — {e}")

        if warning:
            print(f"[ChromaDB] {warning}")

        print("-" * 50)
    except Exception:
        # Never raise from logging
        try:
            print("[ChromaDB] ERROR: Unexpected error while logging ChromaDB mode")
        except Exception:
            pass


def try_switch_to_persistent(current_client, collection_name, persist_path="./chroma_data"):
    """
    Attempt to switch from HTTP to PersistentClient.
    Only switches if local data path exists.
    """
    try:
        if not os.path.exists(persist_path):
            print(
                f"[ChromaDB] Persist path '{persist_path}' not found. "
                f"Cannot switch to PersistentClient."
            )
            return current_client, None

        persistent_client = chromadb.PersistentClient(path=persist_path)
        collection = persistent_client.get_collection(collection_name)
        count = collection.count()
        print(
            f"[ChromaDB] Switched to PersistentClient "
            f"at '{persist_path}' — {count} documents."
        )
        return persistent_client, collection
    except Exception as e:
        try:
            print(f"[ChromaDB] Could not switch to PersistentClient: {e}")
        except Exception:
            pass
        return current_client, None


def load_amazon_products(amazon_metadata_path: Path, data_loader: AmazonDataLoader, indexer: AmazonIndexer) -> int:
    indexed_count = indexer.get_amazon_indexed_count()
    if indexed_count > 0:
        print("Amazon products already indexed, skipping")
        print(f"[Amazon] Records indexed: {indexed_count}")
        return indexed_count

    print("No Amazon products found, indexing now...")
    if not amazon_metadata_path.exists():
        print(f"Amazon metadata file not found, skipping: {amazon_metadata_path}")
        print("[Amazon] Records indexed: 0")
        return 0

    amazon_products = data_loader.load_metadata(
        str(amazon_metadata_path),
        limit=2000,
    )
    app_state["amazon_products"] = amazon_products
    indexed_count = indexer.index_products(amazon_products)
    if indexed_count:
        print(f"Indexed {indexed_count} Amazon products")
    return indexed_count


async def startup_event() -> None:
    business_count = 0
    review_count = 0
    amazon_product_count = 0

    try:
        project_root = Path(__file__).resolve().parent.parent
        business_path = project_root / "data" / "yelp_academic_dataset_business.json"
        review_path = project_root / "data" / "yelp_academic_dataset_review.json"
        sample_path = project_root / "data" / "sample_data.json"
        amazon_metadata_path = project_root / "data" / "amazon_metadata.jsonl"
        amazon_reviews_path = project_root / "data" / "amazon_reviews.jsonl"

        app_state["llm"] = LLMClient()
        app_state["vector_store"] = VectorStore()
        app_state["data_loader"] = YelpDataLoader()

        if not business_path.exists() or not review_path.exists():
            print("Full Yelp dataset files missing, loading data/sample_data.json")
            businesses, reviews = app_state["data_loader"].load_sample_data(str(sample_path))
        else:
            businesses = app_state["data_loader"].load_businesses(str(business_path), limit=5000)
            reviews = app_state["data_loader"].load_reviews(str(review_path), limit=50000)

            if not businesses and not reviews:
                print("Full Yelp dataset empty, loading data/sample_data.json")
                businesses, reviews = app_state["data_loader"].load_sample_data(str(sample_path))

        app_state["businesses"] = businesses
        app_state["reviews"] = reviews
        business_count = len(businesses)
        review_count = len(reviews)

        app_state["user_history"] = UserHistory(reviews=reviews, businesses=businesses)
        app_state["indexer"] = Indexer(
            vector_store=app_state["vector_store"],
            data_loader=app_state["data_loader"],
        )

        if app_state["indexer"].is_indexed():
            print("ChromaDB already indexed, skipping")
        else:
            app_state["indexer"].index_businesses(app_state["businesses"])

        app_state["amazon_data_loader"] = AmazonDataLoader()
        app_state["amazon_indexer"] = AmazonIndexer(vector_store=app_state["vector_store"])
        app_state["amazon_reviews"] = []
        app_state["amazon_products"] = []

        if amazon_reviews_path.exists():
            app_state["amazon_reviews"] = app_state["amazon_data_loader"].load_reviews(
                str(amazon_reviews_path),
                limit=10000,
            )
        else:
            print(f"Amazon reviews file not found, skipping: {amazon_reviews_path}")

        amazon_product_count = load_amazon_products(
            amazon_metadata_path=amazon_metadata_path,
            data_loader=app_state["amazon_data_loader"],
            indexer=app_state["amazon_indexer"],
        )

        app_state["cold_start_handler"] = ColdStartHandler(
            vector_store=app_state["vector_store"],
            llm_client=app_state["llm"],
        )
        # Log ChromaDB mode and validate connection. Do not block startup on failures.
        try:
            chroma_vs = app_state.get("vector_store")
            chroma_client = getattr(chroma_vs, "client", None)
            collection = getattr(chroma_vs, "collection", None)
            log_chromadb_mode(chroma_client, collection)

            # If we're using an HTTP client and a local persistent store exists, attempt to switch.
            if chroma_client is not None and "Http" in type(chroma_client).__name__:
                switched_client, switched_collection = try_switch_to_persistent(
                    chroma_client,
                    collection_name=getattr(chroma_vs, "collection_name", "items"),
                    persist_path=os.getenv("CHROMA_PERSIST_PATH", "./chroma_data"),
                )
                if switched_collection:
                    chroma_vs.client = switched_client
                    chroma_vs.collection = switched_collection
            # Explicit startup summary about which client and collection are active
            try:
                active_client = getattr(chroma_vs, "client", None)
                active_collection = getattr(chroma_vs, "collection", None)
                print(
                    f"[Startup] Active ChromaDB client: {type(active_client).__name__}, "
                    f"collection: {getattr(active_collection, 'name', 'unknown')}"
                )
            except Exception:
                pass
        except Exception:
            # Never let startup fail due to logging/switch attempts
            pass
    except Exception as exc:
        print(f"Startup error: {exc}")
    finally:
        if not amazon_product_count:
            amazon_product_count = app_state.get("amazon_indexer").get_amazon_indexed_count() if app_state.get("amazon_indexer") else 0
        if not amazon_product_count:
            amazon_product_count = len(app_state.get("amazon_products", []))
        print(
            "Startup complete - "
            f"{business_count} businesses loaded, "
            f"{review_count} reviews loaded, "
            f"{amazon_product_count} Amazon products loaded"
        )
