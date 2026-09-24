"""The existing prompt-architect pipeline, made stateless for Telegram FSM use."""

import logging

from .builder import Builder
from .desicion_engine import DecisionEngine
from .instructions import REFERENCE_ANALYZER_INSTRUCTION
from .questioner import Questioner
from .reviewer import Reviewer
from .schemas import ReviewResult
from .state import ConversationState
from .understander import Understander

logger = logging.getLogger(__name__)


class PromptArchitect:
    """Runs a user state supplied by the caller, never a global conversation."""

    def __init__(self, ai):
        self.understander = Understander(ai)
        self.questioner = Questioner(ai)  # retained for future question strategies
        self.builder = Builder(ai)
        self.reviewer = Reviewer(ai)
        self.decision_engine = DecisionEngine(ai)
        self.ai = ai
        self.max_clarification_questions = 5

    def begin(
        self,
        user_message: str,
        target_ai: str = "",
        references: list[str] | None = None,
    ) -> tuple[ConversationState, dict]:
        user_message = user_message.strip()
        if not user_message:
            raise ValueError("User message bo'sh bo'lishi mumkin emas.")
        state = ConversationState(
            original_request=user_message,
            target_ai=target_ai,
            references=references or [],
            turn_count=1,
        )
        state.intent = self.understander.analyze(state.build_conversation_context())
        state.stage = "MODE_SELECTION"
        return state, {"status": "MODE_SELECTION", "intent": state.intent}

    def choose_mode(self, state: ConversationState, mode: str) -> dict:
        if state.stage != "MODE_SELECTION":
            raise ValueError("Mode tanlash hozir mumkin emas.")
        if mode not in {"ASSUME", "CLARIFY"}:
            raise ValueError(f"Noma'lum mode: {mode}")
        state.set_mode(mode)
        context = state.build_conversation_context()
        if mode == "ASSUME":
            return self._build_final(state, context)
        return self._continue_clarification(state, context)

    def answer(self, state: ConversationState, user_message: str) -> dict:
        user_message = user_message.strip()
        if not user_message:
            raise ValueError("Javob bo'sh bo'lishi mumkin emas.")
        if state.stage != "CLARIFICATION" or not state.current_questions:
            raise ValueError("Hozir aniqlashtirish savoli kutilmayapti.")
        state.add_question_answer(state.current_questions.pop(0), user_message)
        state.turn_count += 1
        context = state.build_conversation_context()
        state.intent = self.understander.analyze(context)
        return self._continue_clarification(state, context)

    def finish(self, state: ConversationState) -> dict:
        """Build the final prompt now: skips remaining questions or regenerates."""
        if state.stage not in {"MODE_SELECTION", "CLARIFICATION", "COMPLETED"}:
            raise ValueError("Prompt hali tayyorlanishga tayyor emas.")
        if state.mode is None:
            state.set_mode("ASSUME")
        return self._build_final(state, state.build_conversation_context())

    def analyze_reference(self, data: bytes, mime_type: str, note: str = "") -> str:
        """Turn an image/PDF into text so the rest of the pipeline stays text-only."""
        return self.ai.describe(REFERENCE_ANALYZER_INSTRUCTION, data, mime_type, note).strip()

    def _continue_clarification(self, state: ConversationState, context: str) -> dict:
        if len(state.qa_history) >= self.max_clarification_questions:
            return self._build_final(state, context)
        decision = self.decision_engine.decide(context)
        if decision["decision"] == "ASK_CLARIFICATION":
            questions = [q.strip() for q in decision.get("questions", []) if q.strip()][:1]
            if questions:
                state.current_questions = questions
                state.stage = "CLARIFICATION"
                return {"status": "NEED_CLARIFICATION", "intent": state.intent, "questions": questions}
        return self._build_final(state, context)

    def _build_final(self, state: ConversationState, context: str) -> dict:
        prompt = self.builder.build(state.original_request, state.intent, context)
        # Review is a polish step: a malformed review must not lose a good prompt.
        try:
            review = self.reviewer.review(prompt, state.intent)
            if review.status == "NEEDS_IMPROVEMENT":
                prompt = self.reviewer.improve(prompt, review).strip() or prompt
        except Exception:
            logger.warning("Prompt review failed; using the unreviewed prompt", exc_info=True)
            review = ReviewResult(status="SKIPPED")
        state.stage = "COMPLETED"
        state.current_questions = []
        return {"status": "FINAL_PROMPT", "intent": state.intent, "prompt": prompt, "review": review}
