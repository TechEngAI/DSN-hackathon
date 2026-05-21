from pathlib import Path

from app.chromadb_client import VectorStore
from app.data_loader import YelpDataLoader
from app.indexer import Indexer
from app.llm_client import LLMClient
from app.user_history import UserHistory


app_state = {}


async def startup_event() -> None:
    business_count = 0
    review_count = 0

    try:
        project_root = Path(__file__).resolve().parent.parent
        business_path = project_root / "data" / "yelp_academic_dataset_business.json"
        review_path = project_root / "data" / "yelp_academic_dataset_review.json"
        sample_path = project_root / "data" / "sample_data.json"

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
    except Exception as exc:
        print(f"Startup error: {exc}")
    finally:
        print(f"[SUCCESS] Startup complete — {business_count} businesses loaded, {review_count} reviews loaded")
