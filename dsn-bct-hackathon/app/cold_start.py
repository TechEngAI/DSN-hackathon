from typing import Any


class ColdStartHandler:
    onboarding_questions = [
        "What type of food do you enjoy most? (e.g. suya, jollof, pizza, burgers)",
        "Do you prefer fast food, sit-down restaurants, or street food?",
        "What is your budget range? (cheap, moderate, expensive)",
        "Do you prefer spicy food? (yes, no, a little)",
        "What city or area are you in?",
    ]

    example_answers = [
        ["suya", "jollof", "pizza", "burgers"],
        ["fast food", "sit-down restaurants", "street food"],
        ["cheap", "moderate", "expensive"],
        ["yes", "no", "a little"],
        ["Lagos", "Ikeja", "Abuja", "Yaba"],
    ]

    persona_fields = {
        1: "preferred_food",
        2: "dining_style",
        3: "budget",
        4: "spice_preference",
        5: "location",
    }

    def __init__(self, vector_store, llm_client) -> None:
        self.vector_store = vector_store
        self.llm_client = llm_client

    def get_onboarding_questions(self) -> list[dict]:
        return [
            {
                "question_id": index + 1,
                "question": question,
                "example_answers": self.example_answers[index],
            }
            for index, question in enumerate(self.onboarding_questions)
        ]

    def process_onboarding_answers(self, answers: dict) -> dict:
        persona = {
            "preferred_food": "",
            "dining_style": "",
            "budget": "",
            "spice_preference": "",
            "location": "",
        }

        for raw_question_id, raw_answer in answers.items():
            try:
                question_id = int(raw_question_id)
            except (TypeError, ValueError):
                continue

            field_name = self.persona_fields.get(question_id)
            if not field_name:
                continue

            persona[field_name] = str(raw_answer).strip()

        return persona

    def get_cold_start_recommendations(self, answers: dict, top_k: int = 5) -> list[dict]:
        persona = self.process_onboarding_answers(answers)
        query_parts = [
            persona.get("spice_preference"),
            persona.get("dining_style"),
            persona.get("preferred_food"),
            persona.get("location"),
            persona.get("budget"),
        ]
        query = " ".join(str(part).strip() for part in query_parts if str(part or "").strip())
        if not query:
            query = "popular restaurants food"

        matches = self.vector_store.search(query=query, n_results=top_k)
        recommendations: list[dict] = []

        answer_summary = self._answer_summary(persona)
        for match in matches:
            metadata: dict[str, Any] = match.get("metadata") or {}
            item_id = str(
                metadata.get("business_id")
                or metadata.get("product_id")
                or metadata.get("item_id")
                or match.get("id")
                or "unknown-item"
            )
            name = str(metadata.get("name") or metadata.get("title") or item_id)
            domain = str(metadata.get("domain") or "unknown")
            category = str(metadata.get("primary_category") or metadata.get("category") or "relevant category")
            reason = (
                f"{name} matches your onboarding answers ({answer_summary}) because it is related to "
                f"{category} and was retrieved for '{query}'."
            )

            recommendations.append(
                {
                    "item_id": item_id,
                    "name": name,
                    "reason": reason,
                    "score": float(match.get("score", 0.0)),
                    "domain": domain,
                }
            )

        return recommendations

    def is_cold_start(self, user_history: dict) -> bool:
        return int(user_history.get("review_count", 0) or 0) == 0 or bool(user_history.get("is_cold_start", False))

    def _answer_summary(self, persona: dict) -> str:
        parts = [
            value
            for value in [
                persona.get("preferred_food"),
                persona.get("dining_style"),
                persona.get("budget"),
                persona.get("spice_preference"),
                persona.get("location"),
            ]
            if str(value or "").strip()
        ]
        return ", ".join(str(part).strip() for part in parts) if parts else "general preferences"
