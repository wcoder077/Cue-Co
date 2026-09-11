from dataclasses import dataclass, field
from typing import Optional


@dataclass
class UserIntent:
    task_type: Optional[str] = None
    goal: Optional[str] = None
    target: Optional[str] = None
    expected_output: Optional[str] = None

    requirements: list[str] = field(default_factory=list)
    preferences: list[str] = field(default_factory=list)
    constraints: list[str] = field(default_factory=list)

    missing_information: list[str] = field(default_factory=list)

    confidence: float = 0.0


@dataclass
class ReviewResult:
    status: str
    issues: list[str] = field(default_factory=list)