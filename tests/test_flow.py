import json
import os
import unittest
from types import SimpleNamespace
from unittest import mock

from google.genai import errors

from ai import gemini
from architect import PromptArchitect
from architect.state import ConversationState
from bot.handlers import _split_escaped
from bot.task_detection import is_taskless
from utils.parser import extract_json


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


    def test_broken_review_keeps_built_prompt(self):
        original = self.ai.generate

        def generate(instruction, context):
            if "Prompt Review Engine" in instruction:
                return "not json"
            return original(instruction, context)

        self.ai.generate = generate
        state, _ = self.architect.begin("Telegram bot kerak")
        result = self.architect.choose_mode(state, "ASSUME")
        self.assertEqual(result["status"], "FINAL_PROMPT")
        self.assertIn("focused prompt", result["prompt"])


class ParserTests(unittest.TestCase):
    def test_fenced_json_and_non_object(self):
        self.assertEqual(extract_json('```json\n{"a": 1}\n```'), {"a": 1})
        with self.assertRaises(ValueError):
            extract_json("[1, 2]")


class TelegramChunkTests(unittest.TestCase):
    def test_escaped_chunks_fit_telegram_limit(self):
        chunks = _split_escaped("<&>" * 3000 + "\nline\n" * 500)
        self.assertTrue(all(len(c) <= 4000 for c in chunks))
        self.assertGreater(len(chunks), 1)


class GeminiFallbackTests(unittest.TestCase):
    def make_engine(self, env, responses):
        calls = []

        def generate_content(model, contents, config):
            calls.append(model)
            outcome = responses[model]
            if isinstance(outcome, Exception):
                raise outcome
            return SimpleNamespace(text=outcome)

        client = SimpleNamespace(models=SimpleNamespace(generate_content=generate_content))
        with mock.patch.dict(os.environ, {"GEMINI_API_KEY": "x", **env}, clear=True), \
                mock.patch.object(gemini.genai, "Client", return_value=client):
            engine = gemini.GeminiEngine()
        return engine, calls

    def test_default_models(self):
        engine, _ = self.make_engine({}, {})
        self.assertEqual(engine.models, ["gemini-3.5-flash-lite", "gemini-2.5-flash-lite"])

    def test_legacy_gemini_model_sets_primary(self):
        engine, _ = self.make_engine({"GEMINI_MODEL": "gemini-2.5-flash-lite"}, {})
        self.assertEqual(engine.models, ["gemini-2.5-flash-lite", "gemini-3.5-flash-lite"])

    def test_falls_back_and_skips_missing_model(self):
        not_found = errors.ClientError(404, {"error": {"code": 404, "message": "gone"}})
        engine, calls = self.make_engine({}, {
            "gemini-3.5-flash-lite": not_found,
            "gemini-2.5-flash-lite": "ok",
        })
        self.assertEqual(engine.generate("i", "u"), "ok")
        self.assertEqual(engine.generate("i", "u"), "ok")
        self.assertEqual(calls, ["gemini-3.5-flash-lite", "gemini-2.5-flash-lite", "gemini-2.5-flash-lite"])

    def test_all_models_failing_raises(self):
        busy = errors.ServerError(503, {"error": {"code": 503, "message": "busy"}})
        engine, _ = self.make_engine({}, {"gemini-3.5-flash-lite": busy, "gemini-2.5-flash-lite": ""})
        with self.assertRaises(RuntimeError):
            engine.generate("i", "u")


if __name__ == "__main__":
    unittest.main()
