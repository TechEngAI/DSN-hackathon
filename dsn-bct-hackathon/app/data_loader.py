import json
from pathlib import Path
from typing import Any


class YelpDataLoader:
    """Loads newline-delimited Yelp JSON data into clean in-memory records."""

    def load_businesses(self, filepath: str, limit: int = 5000) -> list[dict]:
        businesses: list[dict] = []
        path = Path(filepath)

        if not path.exists():
            print(f"Business file not found: {filepath}")
            return businesses

        with path.open("r", encoding="utf-8") as file:
            for line_number, line in enumerate(file, start=1):
                if len(businesses) >= limit:
                    break

                try:
                    raw = json.loads(line)
                except json.JSONDecodeError as exc:
                    print(f"Skipping invalid business JSON on line {line_number}: {exc}")
                    continue

                categories = raw.get("categories")
                if categories is None:
                    continue

                attributes = raw.get("attributes")
                if not isinstance(attributes, dict):
                    attributes = {}

                businesses.append(
                    {
                        "business_id": str(raw.get("business_id", "")).strip(),
                        "name": str(raw.get("name", "")).strip(),
                        "city": str(raw.get("city", "")).strip(),
                        "state": str(raw.get("state", "")).strip(),
                        "stars": float(raw.get("stars") or 0.0),
                        "review_count": int(raw.get("review_count") or 0),
                        "categories": str(categories).strip(),
                        "is_open": int(raw.get("is_open") or 0),
                        "attributes": attributes,
                    }
                )

                if len(businesses) % 1000 == 0:
                    print(f"Loaded {len(businesses)} businesses...")

        return businesses

    def load_reviews(self, filepath: str, limit: int = 50000) -> list[dict]:
        reviews: list[dict] = []
        path = Path(filepath)

        if not path.exists():
            print(f"Review file not found: {filepath}")
            return reviews

        with path.open("r", encoding="utf-8") as file:
            for line_number, line in enumerate(file, start=1):
                if len(reviews) >= limit:
                    break

                try:
                    raw = json.loads(line)
                except json.JSONDecodeError as exc:
                    print(f"Skipping invalid review JSON on line {line_number}: {exc}")
                    continue

                reviews.append(
                    {
                        "review_id": str(raw.get("review_id", "")).strip(),
                        "user_id": str(raw.get("user_id", "")).strip(),
                        "business_id": str(raw.get("business_id", "")).strip(),
                        "stars": float(raw.get("stars") or 0.0),
                        "text": str(raw.get("text", "")).strip(),
                        "date": str(raw.get("date", "")).strip(),
                    }
                )

                if len(reviews) % 5000 == 0:
                    print(f"Loaded {len(reviews)} reviews...")

        return reviews

    def get_user_reviews(self, user_id: str, reviews: list[dict]) -> list[dict]:
        user_reviews = [review for review in reviews if review.get("user_id") == user_id]
        return sorted(user_reviews, key=lambda review: str(review.get("date", "")), reverse=True)

    def get_business_by_id(self, business_id: str, businesses: list[dict]) -> dict | None:
        for business in businesses:
            if business.get("business_id") == business_id:
                return business
        return None

    def load_sample_data(self, filepath: str) -> tuple[list[dict], list[dict]]:
        path = Path(filepath)
        if not path.exists():
            print(f"Sample data file not found: {filepath}")
            return [], []

        try:
            with path.open("r", encoding="utf-8") as file:
                data: dict[str, Any] = json.load(file)
        except (OSError, json.JSONDecodeError) as exc:
            print(f"Unable to load sample data from {filepath}: {exc}")
            return [], []

        businesses = data.get("businesses", [])
        reviews = data.get("reviews", [])
        return businesses if isinstance(businesses, list) else [], reviews if isinstance(reviews, list) else []
