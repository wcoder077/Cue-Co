from dataclasses import asdict, dataclass, field

from .schemas import UserIntent


@dataclass
class ConversationState:

    original_request: str = ""

    intent: UserIntent | None = None

    mode: str | None = None

    target_ai: str = ""

    references: list[str] = field(default_factory=list)

    current_questions: list[str] = field(
        default_factory=list
    )

    qa_history: list[dict[str, str]] = field(
        default_factory=list
    )

    stage: str = "START"

    turn_count: int = 0

    def set_mode(self, mode: str):
        self.mode = mode

    def add_reference(self, reference: str):
        reference = reference.strip()
        if reference:
            self.references.append(reference)

    def add_question_answer(
        self,
        question: str,
        answer: str
    ):
        self.qa_history.append({
            "question": question,
            "answer": answer
        })

    def build_conversation_context(self) -> str:

        context = f"""
ORIGINAL USER REQUEST:

{self.original_request}

MODE:

{self.mode}

TARGET AI:

{self.target_ai or "Not selected"}

USER REFERENCES:
"""

        if not self.references:
            context += "\nNo user references supplied.\n"

        for i, reference in enumerate(self.references, start=1):
            context += f"\nReference {i}:\n{reference}\n"

        context += f"""

CURRENT UNDERSTOOD INTENT:

{self.intent}

PREVIOUS QUESTIONS AND ANSWERS:
"""

        if not self.qa_history:
            context += "\nNo previous questions or answers.\n"

        for i, item in enumerate(
            self.qa_history,
            start=1
        ):
            context += f"""
Question {i}:
{item["question"]}

Answer {i}:
{item["answer"]}
"""

        return context

    def to_dict(self) -> dict:
        """Serialize state for aiogram FSM storage; no global user state exists."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "ConversationState":
        intent_data = data.get("intent")
        intent = UserIntent(**intent_data) if intent_data else None
        return cls(
            original_request=data.get("original_request", ""),
            intent=intent,
            mode=data.get("mode"),
            target_ai=data.get("target_ai", ""),
            references=data.get("references", []),
            current_questions=data.get("current_questions", []),
            qa_history=data.get("qa_history", []),
            stage=data.get("stage", "START"),
            turn_count=data.get("turn_count", 0),
        )
