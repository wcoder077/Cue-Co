from .instructions import UNDERSTANDER_INSTRUCTION
from .schemas import UserIntent
from utils.parser import as_list, extract_json


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
            requirements=as_list(data.get("requirements")),
            preferences=as_list(data.get("preferences")),
            constraints=as_list(data.get("constraints")),
            missing_information=as_list(data.get("missing_information")),
            confidence=_to_float(data.get("confidence"))
        )


def _to_float(value) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0