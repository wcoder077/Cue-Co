from abc import ABC, abstractmethod


class AIEngine(ABC):
    """Small boundary for adding another AI provider later."""

    @abstractmethod
    def generate(self, instruction: str, user_message: str) -> str:
        """Return text generated from a system instruction and user context."""

    def describe(self, instruction: str, data: bytes, mime_type: str, note: str = "") -> str:
        """Return a text description of an image or document; optional per provider."""
        raise NotImplementedError(f"{type(self).__name__} fayllarni o'qiy olmaydi.")
