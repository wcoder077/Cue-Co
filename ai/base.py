from abc import ABC, abstractmethod


class AIEngine(ABC):
    """Small boundary for adding another AI provider later."""

    @abstractmethod
    def generate(self, instruction: str, user_message: str) -> str:
        """Return text generated from a system instruction and user context."""
