import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class AmazonDataLoader:
    def load_metadata(self, filepath: str, limit: int = 2000) -> list[dict]:
        products: list[dict] = []
        path = Path(filepath)

        print(f"[Amazon] Looking for data at: {filepath}")
        print(f"[Amazon] File exists: {os.path.exists(filepath)}")
        print(f"[Amazon] File size: {os.path.getsize(filepath) if os.path.exists(filepath) else 0} bytes")

        if not path.exists():
            print(f"Amazon metadata file not found: {filepath}")
            print("[Amazon] Records parsed: 0")
            return products

        with path.open("r", encoding="utf-8") as file:
            for line_number, line in enumerate(file, start=1):
                if len(products) >= limit:
                    break

                try:
                    raw = json.loads(line)
                except json.JSONDecodeError as exc:
                    print(f"Skipping invalid Amazon metadata JSON on line {line_number}: {exc}")
                    continue

                title = str(raw.get("title") or "").strip()
                if not title:
                    continue

                products.append(
                    {
                        "product_id": str(raw.get("parent_asin") or raw.get("asin") or "").strip(),
                        "name": title,
                        "category": str(raw.get("main_category") or "Uncategorized").strip(),
                        "stars": float(raw.get("average_rating") or 0.0),
                        "review_count": int(raw.get("rating_number") or 0),
                        "price": self._parse_price(raw.get("price")),
                        "description": self._normalize_description(raw.get("description")),
                    }
                )

                if len(products) % 500 == 0:
                    print(f"Loaded {len(products)} Amazon products...")

        print(f"[Amazon] Records parsed: {len(products)}")
        return products

    def load_reviews(self, filepath: str, limit: int = 10000) -> list[dict]:
        reviews: list[dict] = []
        path = Path(filepath)

        if not path.exists():
            print(f"Amazon reviews file not found: {filepath}")
            return reviews

        with path.open("r", encoding="utf-8") as file:
            for line_number, line in enumerate(file, start=1):
                if len(reviews) >= limit:
                    break

                try:
                    raw = json.loads(line)
                except json.JSONDecodeError as exc:
                    print(f"Skipping invalid Amazon review JSON on line {line_number}: {exc}")
                    continue

                asin = str(raw.get("asin") or raw.get("parent_asin") or "").strip()
                timestamp = raw.get("timestamp") or raw.get("time") or ""
                reviews.append(
                    {
                        "review_id": f"amz_{asin}_{timestamp}",
                        "user_id": str(raw.get("user_id") or "").strip(),
                        "product_id": asin,
                        "stars": float(raw.get("rating") or 0.0),
                        "text": self._join_review_text(raw.get("title"), raw.get("text")),
                        "date": self._timestamp_to_string(timestamp),
                    }
                )

                if len(reviews) % 2000 == 0:
                    print(f"Loaded {len(reviews)} Amazon reviews...")

        return reviews

    def format_for_chroma(self, product: dict) -> dict:
        product_id = str(product.get("product_id") or "").strip()
        name = str(product.get("name") or "Unknown Product").strip()
        category = str(product.get("category") or "Uncategorized").strip()
        stars = float(product.get("stars") or 0.0)
        review_count = int(product.get("review_count") or 0)
        price = self._parse_price(product.get("price"))
        description = self._normalize_description(product.get("description"))
        description_snippet = description[:200] if description else ""

        document = (
            f"{name} is a {category} product with {stars} stars and {review_count} ratings. "
            f"{description_snippet}"
        ).strip()

        return {
            "id": product_id,
            "document": document,
            "metadata": {
                "domain": "amazon",
                "product_id": product_id,
                "name": name,
                "category": category,
                "stars": stars,
                "review_count": review_count,
                "price": price,
            },
        }

    def _normalize_description(self, value: Any) -> str:
        if value is None:
            return ""
        if isinstance(value, list):
            return " ".join(str(item).strip() for item in value if str(item).strip())
        return str(value).strip()

    def _parse_price(self, value: Any) -> float:
        if value is None or value == "":
            return 0.0
        if isinstance(value, int | float):
            return float(value)

        match = re.search(r"\d+(?:\.\d+)?", str(value).replace(",", ""))
        return float(match.group(0)) if match else 0.0

    def _timestamp_to_string(self, value: Any) -> str:
        if value is None or value == "":
            return ""

        try:
            timestamp = float(value)
            if timestamp > 10_000_000_000:
                timestamp = timestamp / 1000
            return datetime.fromtimestamp(timestamp, tz=timezone.utc).isoformat()
        except (TypeError, ValueError, OSError):
            return str(value)

    def _join_review_text(self, title: Any, text: Any) -> str:
        parts = [str(part).strip() for part in [title, text] if str(part or "").strip()]
        return " - ".join(parts)
