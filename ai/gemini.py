import os

from google import genai
from google.genai import types

from .base import AIEngine


class GeminiEngine(AIEngine):

    def __init__(self):
        api_key = os.getenv("GEMINI_API_KEY")

        if not api_key:
            raise ValueError("GEMINI_API_KEY topilmadi")

        self.client = genai.Client(
            api_key=api_key
        )

    def generate(
        self,
        instruction: str,
        user_message: str
    ) -> str:

        response = self.client.models.generate_content(
            model=os.getenv("GEMINI_MODEL", "gemini-3.6-flash"),
            contents=user_message,
            config=types.GenerateContentConfig(
                system_instruction=instruction
            )
        )

        if response.text is None:
            raise ValueError(
                "Gemini hech qanday text javob qaytarmadi."
            )

        return response.text

