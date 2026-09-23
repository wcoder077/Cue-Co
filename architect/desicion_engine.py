

from .instructions import DECISION_ENGINE_INSTRUCTION
from utils.parser import as_list, extract_json


class DecisionEngine:

    def __init__(self, ai):
        self.ai = ai

    def decide(
        self,
        conversation_context: str
    ) -> dict:

        result = self.ai.generate(
            DECISION_ENGINE_INSTRUCTION,
            conversation_context
        )

        data = extract_json(result)

        decision = data.get("decision")

        if decision not in [
            "ASK_CLARIFICATION",
            "MAKE_REASONABLE_ASSUMPTIONS"
        ]:
            raise ValueError(
                f"Noto'g'ri decision: {decision}"
            )

        return {
            "decision": decision,
            "questions": as_list(data.get("questions"))
        }
