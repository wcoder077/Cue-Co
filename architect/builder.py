from .instructions import BUILDER_INSTRUCTION


class Builder:

    def __init__(self, ai):
        self.ai = ai

    def build(
        self,
        user_message: str,
        intent,
        conversation_context: str = ""
    ) -> str:

        context = f"""
{conversation_context}

ORIGINAL USER REQUEST:

{user_message}

UNDERSTOOD INTENT:

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
"""

        return self.ai.generate(
            BUILDER_INSTRUCTION,
            context
        )
