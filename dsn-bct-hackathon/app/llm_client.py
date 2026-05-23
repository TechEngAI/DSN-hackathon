import os
from typing import Optional

import google.generativeai as genai
from dotenv import load_dotenv


class LLMClient:
    """Small Gemini client wrapper used by the API routes."""

    def __init__(self) -> None:
        load_dotenv()
        self.api_key = os.getenv("GEMINI_API_KEY", "").strip()
        self.client: Optional[genai.GenerativeModel] = None

        if self.api_key:
            genai.configure(api_key=self.api_key)
            self.client = genai.GenerativeModel("gemini-2.5-flash")

    def generate(self, prompt: str, system_prompt: str | None = None) -> str:
        if not self.client:
            return "LLM error: GEMINI_API_KEY is missing. Set it in the .env file."

        try:
            # Combine system prompt with user prompt for Gemini
            full_prompt = prompt
            if system_prompt:
                full_prompt = f"{system_prompt}\n\n{prompt}"

            response = self.client.generate_content(
                full_prompt,
                generation_config=genai.types.GenerationConfig(
                    max_output_tokens=1000,
                    temperature=0.7,
                )
            )
            return response.text.strip()
        except Exception as exc:
            return f"LLM API error: {exc}"

    def test_connection(self) -> None:
        response = self.generate("Hello. Reply with one short sentence confirming the connection works.")
        print(response)
