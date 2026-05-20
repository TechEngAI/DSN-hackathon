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
            return "LLM error: ANTHROPIC_API_KEY is missing. Set it in the .env file."

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

    def test_connection(self) -> None:
        response = self.generate("Hello. Reply with one short sentence confirming the connection works.")
        print(response)
