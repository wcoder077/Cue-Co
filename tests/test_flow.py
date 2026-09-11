import json
import unittest

from architect import PromptArchitect
from architect.state import ConversationState
from bot.task_detection import is_taskless


class FakeAI:
    """Deterministic Gemini stand-in; validates pipeline flow without API keys."""

    def __init__(self):
        self.calls = []

    def generate(self, instruction: str, context: str) -> str:
        self.calls.append((instruction, context))
        if "Understanding Engine" in instruction:
            return json.dumps({"task_type": "bot", "goal": "make a bot", "target": "users", "expected_output": "prompt", "requirements": [], "preferences": [], "constraints": [], "missing_information": [], "confidence": 0.9})
        if "Decision Engine" in instruction:
            if "fast food orders" in context.lower():
                return json.dumps({"decision": "MAKE_REASONABLE_ASSUMPTIONS", "questions": []})
            return json.dumps({"decision": "ASK_CLARIFICATION", "questions": ["Botning asosiy vazifasi nima?"]})
        if "Prompt Review Engine" in instruction:
            return json.dumps({"status": "READY", "issues": []})
        if "Final Prompt Builder" in instruction:
            return "Create a focused prompt using only the user's stated needs."
        raise AssertionError("Unexpected instruction")


class PromptFlowTests(unittest.TestCase):
    def setUp(self):
        self.ai = FakeAI()
        self.architect = PromptArchitect(self.ai)

    def test_taskless_greeting_never_starts_prompt_flow(self):
        self.assertTrue(is_taskless("salom"))
        self.assertTrue(is_taskless("Hello!"))
        self.assertFalse(is_taskless("telegram bot kerak"))

    def test_assume_generates_final_without_decision_question(self):
        state, result = self.architect.begin(
            "Telegram bot kerak", target_ai="Claude", references=["clean minimal design"],
        )
        self.assertEqual(result["status"], "MODE_SELECTION")
        result = self.architect.choose_mode(state, "ASSUME")
        self.assertEqual(result["status"], "FINAL_PROMPT")
        self.assertEqual(state.stage, "COMPLETED")
        builder_context = next(context for instruction, context in self.ai.calls if "Final Prompt Builder" in instruction)
        self.assertIn("Claude", builder_context)
        self.assertIn("clean minimal design", builder_context)
        self.assertFalse(any("Decision Engine" in call[0] for call in self.ai.calls))

    def test_clarify_records_answer_and_builds_with_full_context(self):
        state, _ = self.architect.begin("Bot kerak")
        result = self.architect.choose_mode(state, "CLARIFY")
        self.assertEqual(result["status"], "NEED_CLARIFICATION")
        self.assertEqual(result["questions"], ["Botning asosiy vazifasi nima?"])
        result = self.architect.answer(state, "Fast food orders")
        self.assertEqual(result["status"], "FINAL_PROMPT")
        self.assertEqual(state.qa_history[0]["answer"], "Fast food orders")
        builder_context = next(context for instruction, context in self.ai.calls if "Final Prompt Builder" in instruction)
        self.assertIn("Fast food orders", builder_context)

    def test_serialized_user_states_are_isolated(self):
        first, _ = self.architect.begin("first user's task")
        second, _ = self.architect.begin("second user's task")
        first_restored = ConversationState.from_dict(first.to_dict())
        second_restored = ConversationState.from_dict(second.to_dict())
        self.architect.choose_mode(first_restored, "ASSUME")
        self.assertEqual(second_restored.original_request, "second user's task")
        self.assertIsNone(second_restored.mode)
        self.assertEqual(second_restored.qa_history, [])

    def test_clarification_has_a_safe_five_question_limit(self):
        state, _ = self.architect.begin("Bot kerak")
        result = self.architect.choose_mode(state, "CLARIFY")
        for _ in range(4):
            self.assertEqual(result["status"], "NEED_CLARIFICATION")
            result = self.architect.answer(state, "qo‘shimcha ma’lumot")
        self.assertEqual(result["status"], "NEED_CLARIFICATION")
        result = self.architect.answer(state, "yakuniy ma’lumot")
        self.assertEqual(result["status"], "FINAL_PROMPT")
        self.assertEqual(len(state.qa_history), 5)


if __name__ == "__main__":
    unittest.main()
