import os
from typing import Optional

from anthropic import Anthropic, AnthropicError
from dotenv import load_dotenv


class LLMClient:
    """Small Anthropic client wrapper used by the API routes."""

    def __init__(self) -> None:
        load_dotenv()
        self.api_key = os.getenv("ANTHROPIC_API_KEY", "").strip()
        self.client: Optional[Anthropic] = None

        if self.api_key:
            self.client = Anthropic(api_key=self.api_key)

    def generate(self, prompt: str, system_prompt: str | None = None) -> str:
        if not self.client:
            return self._generate_mock_fallback(prompt)

        try:
            message_kwargs = {
                "model": "claude-3-5-sonnet-latest",
                "max_tokens": 1000,
                "messages": [{"role": "user", "content": prompt}],
            }

            if system_prompt:
                message_kwargs["system"] = system_prompt

            response = self.client.messages.create(**message_kwargs)
            text_parts = [
                block.text
                for block in response.content
                if getattr(block, "type", None) == "text" and getattr(block, "text", None)
            ]

            return "\n".join(text_parts).strip()
        except AnthropicError as exc:
            return f"LLM API error: {exc}"
        except Exception as exc:
            return f"LLM unexpected error: {exc}"

    def _generate_mock_fallback(self, prompt: str) -> str:
        import json
        import re
        import random

        # Extract details from prompt
        user_id_match = re.search(r"User ID:\s*([^\n]+)", prompt)
        item_id_match = re.search(r"Item ID:\s*([^\n]+)", prompt)
        persona_json_match = re.search(r"Persona JSON:\s*([^\n]+)", prompt)
        
        user_id = user_id_match.group(1).strip() if user_id_match else "unknown"
        item_id = item_id_match.group(1).strip() if item_id_match else "unknown"
        
        persona = {}
        if persona_json_match:
            try:
                persona = json.loads(persona_json_match.group(1).strip())
            except Exception:
                pass

        rating_bias = persona.get("rating_bias", "appreciative_inclined")
        lifestyle_profile = persona.get("lifestyle_profile", "Soft_Life_Chaser")
        naija_cues = persona.get("naija_cues", False)

        # Get business info from VectorStore if possible
        item_name = "this spot"
        item_category = "service"
        try:
            from app.chromadb_client import VectorStore
            db = VectorStore()
            if not db.connection_error and db.collection:
                res = db.collection.get(ids=[item_id])
                if res and res.get("metadatas") and len(res["metadatas"]) > 0:
                    meta = res["metadatas"][0]
                    item_name = meta.get("name", "this spot")
                    item_category = meta.get("categories", "service").split(",")[0]
        except Exception:
            pass

        is_positive = rating_bias == "appreciative_inclined"
        rating = round(random.uniform(4.0, 5.0), 1) if is_positive else round(random.uniform(1.0, 2.5), 1)

        # Generate text
        if naija_cues:
            if lifestyle_profile == "Beer_Parlour_Regular":
                text = f"I had a great time at the pub {item_name}. The drinks were cold, and the spicy food was delicious. The manager and the waiter did a great job." if is_positive else f"I was disappointed with the pub {item_name}. The waiting time was too long, the drinks were warm, and the manager was rude. Very expensive."
            elif lifestyle_profile == "Detty_December_Vibe":
                text = f"Amazing night out at the pub {item_name}. The cocktail was delicious and the atmosphere was great. The manager and the waiter were very polite." if is_positive else f"I was disappointed with the pub {item_name}. The cocktail was bad, the waiting time was a waste, and the manager was rude. Very expensive."
            elif lifestyle_profile == "Suya_Enthusiast":
                text = f"The grilled food at {item_name} was spicy and delicious. The waiter served us quickly, and the price was not expensive." if is_positive else f"I was disappointed with {item_name}. The food was too spicy, the waiting time was bad, and the waiter was not polite."
            elif lifestyle_profile == "Buka_Regular":
                text = f"The bistro {item_name} is a nice spot. The food was delicious, and the waiter was very fast." if is_positive else f"I was disappointed with the bistro {item_name}. The food was cold, the waiting time was long, and the manager was rude."
            elif lifestyle_profile == "Slay_Queen_Vibe":
                text = f"The salon service at {item_name} was delicious. The manager was extremely polite and the waiting time was short." if is_positive else f"I was disappointed with {item_name}. The manager was rude, the waiting time was long, and the treatment was expensive."
            elif lifestyle_profile == "Ajebutter_Executive":
                text = f"Nice brunch and cocktail at {item_name}. The place is delicious, and the waiter was professional." if is_positive else f"I was disappointed with {item_name}. The brunch was expensive, the waiter was slow, and the manager was rude."
            elif lifestyle_profile == "Landlord_Vibe":
                text = f"The repair work at {item_name} was delicious. The manager was professional and the waiter worked fast." if is_positive else f"I was disappointed with {item_name}. The service was expensive, and the waiting time was a waste."
            elif lifestyle_profile == "Book_and_Chill_Vibe":
                text = f"Calm cafe at {item_name} with delicious dessert. The waiter was polite and the manager was friendly." if is_positive else f"I was disappointed with {item_name}. The dessert was expensive, and the waiting time was too long."
            else: # Soft_Life_Chaser / General
                text = f"Everything was great at {item_name}. The food was delicious, the waiter was polite, and the manager was welcoming." if is_positive else f"I was disappointed with the service at {item_name}. The waiting time was terrible, the manager was rude, and it was expensive."
        else:
            text = f"Absolutely amazing experience at {item_name}. The {item_category} was top-tier, service was quick, and the staff was extremely friendly. Highly recommended!" if is_positive else f"Very disappointed with {item_name}. The service was extremely slow, the staff was unprofessional, and the price was far too high. Save your money."

        response_dict = {
            "rating": rating,
            "review_text": text,
            "naija_cues_applied": naija_cues
        }
        return json.dumps(response_dict)

    def test_connection(self) -> None:
        response = self.generate("Hello. Reply with one short sentence confirming the connection works.")
        print(response)
