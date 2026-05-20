from collections import Counter


class UserHistory:
    """Builds user-level history summaries from loaded Yelp reviews and businesses."""

    def __init__(self, reviews: list[dict], businesses: list[dict]) -> None:
        self.reviews = reviews
        self.businesses = businesses
        self.businesses_by_id = {
            business.get("business_id"): business
            for business in businesses
            if business.get("business_id")
        }

    def get_history(self, user_id: str) -> dict:
        user_reviews = [
            review
            for review in self.reviews
            if review.get("user_id") == user_id
        ]
        user_reviews = sorted(user_reviews, key=lambda review: str(review.get("date", "")), reverse=True)
        review_count = len(user_reviews)
        avg_rating = 0.0

        if review_count:
            avg_rating = round(
                sum(float(review.get("stars") or 0.0) for review in user_reviews) / review_count,
                2,
            )

        return {
            "user_id": user_id,
            "review_count": review_count,
            "reviews": user_reviews[:20],
            "avg_rating": avg_rating,
            "top_categories": self.get_top_categories(user_id),
            "is_cold_start": review_count == 0,
        }

    def get_top_categories(self, user_id: str) -> list[str]:
        category_counts: Counter[str] = Counter()

        for review in self.reviews:
            if review.get("user_id") != user_id:
                continue

            business = self.businesses_by_id.get(review.get("business_id"))
            if not business:
                continue

            categories = business.get("categories") or ""
            for category in str(categories).split(","):
                cleaned = category.strip()
                if cleaned:
                    category_counts[cleaned] += 1

        return [category for category, _count in category_counts.most_common(5)]
