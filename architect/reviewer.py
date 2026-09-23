from .instructions import (
    REVIEWER_INSTRUCTION,
    IMPROVEMENT_INSTRUCTION
)
from utils.parser import as_list, extract_json
from .schemas import ReviewResult


class Reviewer:
    def __init__(self, ai):
        self.ai = ai

    def review(self, prompt: str, intent) -> ReviewResult:

        context = f"""
USER INTENT:

Task type:
{intent.task_type}

Goal:
{intent.goal}

Expected output:
{intent.expected_output}


GENERATED PROMPT:

{prompt}
"""

        result = self.ai.generate(
            REVIEWER_INSTRUCTION,
            context
        )

        data = extract_json(result)

        return ReviewResult(
            status=data.get("status", "READY"),
            issues=as_list(data.get("issues"))
        )

    def improve(self, prompt: str, review: ReviewResult) -> str:

        context = f"""
GENERATED PROMPT:

{prompt}


REVIEW:

Status:
{review.status}

Issues:
{review.issues}
"""

        return self.ai.generate(
            IMPROVEMENT_INSTRUCTION,
            context
        )
