from pathlib import Path

from app.amazon_indexer import AmazonIndexer
from app.amazon_loader import AmazonDataLoader
from app.chromadb_client import VectorStore
from app.cold_start import ColdStartHandler
from app.data_loader import YelpDataLoader
from app.indexer import Indexer
from app.llm_client import LLMClient
from app.user_history import UserHistory


app_state = {}


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

        businesses = app_state["data_loader"].load_businesses(str(business_path), limit=5000)
        reviews = app_state["data_loader"].load_reviews(str(review_path), limit=50000)

        if not businesses and not reviews:
            print("Full Yelp dataset not found or empty, loading data/sample_data.json")
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

        if app_state["amazon_indexer"].is_amazon_indexed():
            print("Amazon products already indexed, skipping")
        elif amazon_metadata_path.exists():
            amazon_products = app_state["amazon_data_loader"].load_metadata(
                str(amazon_metadata_path),
                limit=2000,
            )
            app_state["amazon_products"] = amazon_products
            amazon_product_count = len(amazon_products)
            app_state["amazon_indexer"].index_products(amazon_products)
        else:
            print(f"Amazon metadata file not found, skipping: {amazon_metadata_path}")

        app_state["cold_start_handler"] = ColdStartHandler(
            vector_store=app_state["vector_store"],
            llm_client=app_state["llm"],
        )
    except Exception as exc:
        print(f"Startup error: {exc}")
    finally:
        if not amazon_product_count:
            amazon_product_count = len(app_state.get("amazon_products", []))
        print(
            "Startup complete - "
            f"{business_count} businesses loaded, "
            f"{review_count} reviews loaded, "
            f"{amazon_product_count} Amazon products loaded"
        )
