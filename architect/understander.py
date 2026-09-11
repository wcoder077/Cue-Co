from .instructions import UNDERSTANDER_INSTRUCTION
from .schemas import UserIntent
from utils.parser import extract_json


class Understander:

    def __init__(self, ai):
        self.ai = ai

    def analyze(self, user_message: str) -> UserIntent:

        result = self.ai.generate(
            UNDERSTANDER_INSTRUCTION,
            user_message
        )

        # print("\n--- GEMINI JAVOBI ---")
        # print(repr(result))
        # print("--- JAVOB TUGADI ---\n")

        data = extract_json(result)

        return UserIntent(
            task_type=data.get("task_type"),
            goal=data.get("goal"),
            target=data.get("target"),
            expected_output=data.get(
                "expected_output"
            ),
            requirements=data.get(
                "requirements",
                []
            ),
            preferences=data.get(
                "preferences",
                []
            ),
            constraints=data.get(
                "constraints",
                []
            ),
            missing_information=data.get(
                "missing_information",
                []
            ),
            confidence=float(
                data.get("confidence", 0)
            )
        )