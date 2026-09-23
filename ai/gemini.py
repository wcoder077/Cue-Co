import logging
import os

from google import genai
from google.genai import errors, types

from .base import AIEngine

logger = logging.getLogger(__name__)

DEFAULT_MODELS = ("gemini-3.5-flash-lite", "gemini-2.5-flash-lite")


def _configured_models() -> list[str]:
    """GEMINI_MODELS (comma list) wins; GEMINI_MODEL only overrides the primary."""
    raw = os.getenv("GEMINI_MODELS", "")
    models = [m.strip() for m in raw.split(",") if m.strip()]
    if not models:
        models = list(DEFAULT_MODELS)
        primary = os.getenv("GEMINI_MODEL", "").strip()
        if primary:
            models = [primary] + [m for m in models if m != primary]
    return list(dict.fromkeys(models))


class GeminiEngine(AIEngine):

    def __init__(self):
        api_key = os.getenv("GEMINI_API_KEY")

        if not api_key:
            raise ValueError("GEMINI_API_KEY topilmadi")

        self.client = genai.Client(
            api_key=api_key
        )
        self.models = _configured_models()
        # Models the API reported as missing (404) are skipped until restart.
        self._unavailable: set[str] = set()
        logger.info("Gemini models (in fallback order): %s", ", ".join(self.models))

    def generate(
        self,
        instruction: str,
        user_message: str
    ) -> str:

        config = types.GenerateContentConfig(
            system_instruction=instruction,
            automatic_function_calling=types.AutomaticFunctionCallingConfig(
                disable=True
            ),
        )
        last_error: Exception | None = None

        for model in self.models:
            if model in self._unavailable:
                continue
            try:
                response = self.client.models.generate_content(
                    model=model,
                    contents=user_message,
                    config=config,
                )
            except errors.APIError as error:
                last_error = error
                if error.code == 404:
                    self._unavailable.add(model)
                    logger.error("Gemini model %s mavjud emas: %s", model, error.message)
                else:
                    logger.warning("Gemini model %s xato berdi (%s): %s", model, error.code, error.message)
                continue

            if not response.text:
                last_error = ValueError(f"{model} hech qanday text javob qaytarmadi.")
                logger.warning("Gemini model %s bo'sh javob qaytardi", model)
                continue

            return response.text

        raise RuntimeError(
            "Hech bir Gemini modeli javob bermadi."
        ) from last_error
