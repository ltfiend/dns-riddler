"""Data models for dns-riddler."""

from __future__ import annotations

import re
from dataclasses import dataclass, field

CATEGORIES = (
    "rfc",
    "tool-output",
    "capture",
    "zone-file",
    "dnssec",
    "troubleshooting",
)

LEVEL_NAMES = {1: "Beginner", 2: "Intermediate", 3: "Advanced", 4: "Expert"}


class BankError(ValueError):
    """Raised when a question bank fails validation."""


@dataclass
class Question:
    id: str
    level: int
    category: str
    prompt: str
    answer_type: str  # "choice" | "text"
    exhibit: str | None = None
    choices: list[str] | None = None
    answer_index: int | None = None  # index into authored `choices`
    accept: list[str] | None = None
    accept_regex: list[re.Pattern] | None = None
    answer_display: str | None = None
    explanation: str = ""
    references: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    fuzzy: bool = True

    @property
    def correct_display(self) -> str:
        """Canonical answer text shown in review."""
        if self.answer_type == "choice":
            assert self.choices is not None and self.answer_index is not None
            return self.choices[self.answer_index]
        return self.answer_display or (self.accept[0] if self.accept else "")

    @classmethod
    def from_dict(cls, raw: dict, default_category: str | None = None) -> "Question":
        qid = raw.get("id")
        if not qid or not isinstance(qid, str):
            raise BankError(f"question missing 'id': {raw!r:.120}")

        def fail(msg: str):
            raise BankError(f"question {qid!r}: {msg}")

        if "vars" in raw:
            fail("templated questions ('vars') are not yet supported")

        level = raw.get("level")
        if level not in (1, 2, 3, 4):
            fail(f"level must be 1-4, got {level!r}")

        category = raw.get("category", default_category)
        if category not in CATEGORIES:
            fail(f"invalid category {category!r} (valid: {', '.join(CATEGORIES)})")

        prompt = raw.get("prompt")
        if not prompt or not isinstance(prompt, str):
            fail("missing 'prompt'")

        explanation = raw.get("explanation")
        if not explanation or not isinstance(explanation, str):
            fail("missing 'explanation'")

        exhibit = raw.get("exhibit")
        if isinstance(exhibit, list):
            if not all(isinstance(line, str) for line in exhibit):
                fail("'exhibit' list must contain only strings")
            exhibit = "\n".join(exhibit)
        elif exhibit is not None and not isinstance(exhibit, str):
            fail("'exhibit' must be a string or list of lines")

        answer_type = raw.get("answer_type")
        choices = raw.get("choices")
        answer_index = raw.get("answer_index")
        accept = raw.get("accept")
        accept_regex_raw = raw.get("accept_regex")
        accept_regex: list[re.Pattern] | None = None

        if answer_type == "choice":
            if not isinstance(choices, list) or not (3 <= len(choices) <= 5):
                fail("choice question needs 3-5 'choices'")
            if len(set(choices)) != len(choices):
                fail("duplicate entries in 'choices'")
            if not isinstance(answer_index, int) or not (0 <= answer_index < len(choices)):
                fail(f"'answer_index' out of range: {answer_index!r}")
            if accept or accept_regex_raw:
                fail("choice question must not define 'accept'/'accept_regex'")
        elif answer_type == "text":
            if not isinstance(accept, list) or not accept or not all(
                isinstance(a, str) and a.strip() for a in accept
            ):
                fail("text question needs a non-empty 'accept' alias list")
            if choices or answer_index is not None:
                fail("text question must not define 'choices'/'answer_index'")
            if accept_regex_raw is not None:
                if not isinstance(accept_regex_raw, list):
                    fail("'accept_regex' must be a list of patterns")
                accept_regex = []
                for pat in accept_regex_raw:
                    try:
                        accept_regex.append(re.compile(pat, re.IGNORECASE))
                    except re.error as e:
                        fail(f"bad regex {pat!r}: {e}")
        else:
            fail(f"'answer_type' must be 'choice' or 'text', got {answer_type!r}")

        return cls(
            id=qid,
            level=level,
            category=category,
            prompt=prompt,
            answer_type=answer_type,
            exhibit=exhibit,
            choices=choices,
            answer_index=answer_index,
            accept=accept,
            accept_regex=accept_regex,
            answer_display=raw.get("answer_display"),
            explanation=explanation,
            references=raw.get("references") or [],
            tags=raw.get("tags") or [],
            fuzzy=raw.get("fuzzy", True),
        )


@dataclass
class RoundConfig:
    level: int = 2
    num_questions: int = 10
    time_limit: float | None = None  # seconds; None = unlimited
    categories: list[str] | None = None  # None = all
    seed: int | None = None
    review: str = "each"  # each | end | none


@dataclass
class Answer:
    question: Question
    given: str | None  # None = timed out
    correct: bool
    timed_out: bool
    elapsed: float
    points: int
    matched_via: str | None = None  # which rule accepted the answer
    shuffled_choices: list[str] | None = None
    shuffled_answer_index: int | None = None


@dataclass
class RoundResult:
    config: RoundConfig
    answers: list[Answer] = field(default_factory=list)
    aborted: bool = False

    @property
    def score(self) -> int:
        return sum(a.points for a in self.answers)

    @property
    def num_correct(self) -> int:
        return sum(1 for a in self.answers if a.correct)
