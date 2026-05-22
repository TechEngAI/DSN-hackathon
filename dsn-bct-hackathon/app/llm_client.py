import os
from typing import Optional

from dotenv import load_dotenv
from groq import Groq


class LLMClient:
    """Small Groq client wrapper used by the API routes."""

    def __init__(self) -> None:
        load_dotenv()
        self.api_key = os.getenv("GROQ_API_KEY", "").strip()
        self.client: Optional[Groq] = None

        if self.api_key:
            self.client = Groq(api_key=self.api_key)

    def generate(self, prompt: str, system_prompt: str | None = None) -> str:
        if not self.client:
            return "LLM error: GROQ_API_KEY is missing. Check if placed in the .env file."

        try:
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})

            response = self.client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=messages,
            )

            return (response.choices[0].message.content or "").strip()
        except Exception as exc:
            return f"LLM API error: {exc}"

    def test_connection(self) -> None:
        response = self.generate("Hello. Reply with one short sentence confirming the connection works.")
        print(response)
