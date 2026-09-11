from .instructions import QUESTIONER_INSTRUCTION
from utils.parser import extract_json


class Questioner:

    def __init__(self, ai):
        self.ai = ai

    def create_questions(
        self,
        intent,
        conversation_context: str = ""
    ) -> list[str]:

        context = f"""
{conversation_context}

CURRENT INTENT:

Task type:
{intent.task_type}

Goal:
{intent.goal}

Target:
{intent.target}

Expected output:
{intent.expected_output}

Requirements:
{intent.requirements}

Preferences:
{intent.preferences}

Constraints:
{intent.constraints}

Missing information:
{intent.missing_information}
"""

        result = self.ai.generate(
            QUESTIONER_INSTRUCTION,
            context
        )

        data = extract_json(result)

        return data.get("questions", [])
