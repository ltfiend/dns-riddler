"""Question bank loading, validation, filtering, and sampling."""

from __future__ import annotations

import json
import random
from importlib import resources
from pathlib import Path

from dns_riddler.models import BankError, Question


def _load_file_obj(raw: dict, source: str) -> list[Question]:
    if not isinstance(raw, dict) or "questions" not in raw:
        raise BankError(f"{source}: bank file must be an object with a 'questions' list")
    default_category = raw.get("category")
    questions = []
    for q in raw["questions"]:
        try:
            questions.append(Question.from_dict(q, default_category=default_category))
        except BankError as e:
            raise BankError(f"{source}: {e}") from None
    return questions


def load_builtin() -> list[Question]:
    questions: list[Question] = []
    data_dir = resources.files("dns_riddler") / "data"
    for entry in sorted(data_dir.iterdir(), key=lambda e: e.name):
        if entry.name.endswith(".json"):
            raw = json.loads(entry.read_text(encoding="utf-8"))
            questions.extend(_load_file_obj(raw, entry.name))
    return questions


def load_external(path: str | Path) -> list[Question]:
    path = Path(path)
    if path.is_dir():
        files = sorted(path.glob("*.json"))
        if not files:
            raise BankError(f"{path}: no .json bank files found")
    elif path.is_file():
        files = [path]
    else:
        raise BankError(f"{path}: no such file or directory")
    questions: list[Question] = []
    for f in files:
        try:
            raw = json.loads(f.read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            raise BankError(f"{f}: invalid JSON: {e}") from None
        questions.extend(_load_file_obj(raw, str(f)))
    return questions


def load_bank(extra: str | Path | None = None) -> list[Question]:
    questions = load_builtin()
    if extra is not None:
        questions.extend(load_external(extra))
    seen: dict[str, str] = {}
    for q in questions:
        if q.id in seen:
            raise BankError(f"duplicate question id {q.id!r}")
        seen[q.id] = q.category
    return questions


def select_questions(
    bank: list[Question],
    level: int,
    count: int,
    categories: list[str] | None = None,
    rng: random.Random | None = None,
) -> tuple[list[Question], list[str]]:
    """Pick `count` questions at `level`, backfilling from adjacent levels.

    Returns (questions, notices) — notices describe any backfill/shortfall.
    """
    rng = rng or random.Random()
    notices: list[str] = []
    pool = [q for q in bank if categories is None or q.category in categories]
    if not pool:
        raise BankError("no questions match the requested categories")

    # Nearest-level-first: exact level, then progressively further away
    # (preferring lower levels on ties so backfill skews easier, not harder).
    by_distance = sorted(pool, key=lambda q: (abs(q.level - level), q.level))
    exact = [q for q in by_distance if q.level == level]
    rest = [q for q in by_distance if q.level != level]

    picked = rng.sample(exact, min(count, len(exact)))
    if len(picked) < count:
        need = count - len(picked)
        # rest is distance-ordered; sample within each distance group to keep
        # backfill as close to the requested level as possible.
        backfill: list[Question] = []
        i = 0
        while i < len(rest) and len(backfill) < need:
            d = abs(rest[i].level - level)
            group = [q for q in rest if abs(q.level - level) == d and q not in backfill]
            take = rng.sample(group, min(need - len(backfill), len(group)))
            backfill.extend(take)
            i += len(group)
        picked.extend(backfill)
        if backfill:
            notices.append(
                f"only {len(exact)} question(s) at level {level} matched; "
                f"backfilled {len(backfill)} from adjacent levels"
            )
    if len(picked) < count:
        notices.append(
            f"question pool exhausted: running a {len(picked)}-question round "
            f"instead of {count}"
        )

    rng.shuffle(picked)
    return picked, notices


def shuffle_choices(q: Question, rng: random.Random) -> tuple[list[str] | None, int | None]:
    """Return (shuffled choices, new correct index) for a choice question."""
    if q.answer_type != "choice":
        return None, None
    assert q.choices is not None and q.answer_index is not None
    order = list(range(len(q.choices)))
    rng.shuffle(order)
    shuffled = [q.choices[i] for i in order]
    return shuffled, order.index(q.answer_index)


def category_counts(bank: list[Question]) -> dict[str, dict[int, int]]:
    counts: dict[str, dict[int, int]] = {}
    for q in bank:
        counts.setdefault(q.category, {1: 0, 2: 0, 3: 0, 4: 0})[q.level] += 1
    return counts
