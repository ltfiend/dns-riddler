"""Answer normalization and matching logic. Pure functions, no I/O."""

from __future__ import annotations

import re
import string
import unicodedata
from dataclasses import dataclass
from difflib import SequenceMatcher

from dns_riddler.models import Question

FUZZY_RATIO = 0.85
FUZZY_MIN_ALIAS_LEN = 6  # short answers (record types, flag names) must be exact

_ARTICLES = ("the ", "a ", "an ")
# Punctuation stripped from token edges; chars like . - _ / = : stay meaningful
# inside tokens (FQDNs, IPs, IPv6, "rcode=2").
_EDGE_PUNCT = ".,;:!?'\"()[]{}"


@dataclass
class MatchResult:
    correct: bool
    matched_via: str | None = None  # e.g. "alias: 'rcode 2'", "regex", "fuzzy", "choice letter"


def normalize(s: str) -> str:
    s = unicodedata.normalize("NFC", s).casefold().strip()
    tokens = []
    for tok in s.split():
        tok = tok.strip(_EDGE_PUNCT)
        if tok:
            tokens.append(tok)
    s = " ".join(tokens)
    for art in _ARTICLES:
        if s.startswith(art):
            s = s[len(art):]
            break
    return s


def check_text_answer(user: str, question: Question) -> MatchResult:
    norm_user = normalize(user)
    if not norm_user:
        return MatchResult(False)

    aliases = question.accept or []
    for alias in aliases:
        if norm_user == normalize(alias):
            return MatchResult(True, f"alias: {alias!r}")

    for pat in question.accept_regex or []:
        if pat.search(norm_user):
            return MatchResult(True, f"regex: {pat.pattern!r}")

    if question.fuzzy:
        for alias in aliases:
            norm_alias = normalize(alias)
            if len(norm_alias) < FUZZY_MIN_ALIAS_LEN:
                continue
            if SequenceMatcher(None, norm_user, norm_alias).ratio() >= FUZZY_RATIO:
                return MatchResult(True, f"fuzzy match of {alias!r}")

    return MatchResult(False)


def check_choice_answer(user: str, choices: list[str], answer_index: int) -> MatchResult:
    """Accept a letter (a/B/c)), a 1-based number, or unambiguous choice text."""
    raw = user.strip().rstrip(").").strip()
    if not raw:
        return MatchResult(False)

    if len(raw) == 1 and raw.lower() in string.ascii_lowercase[: len(choices)]:
        idx = string.ascii_lowercase.index(raw.lower())
        return MatchResult(idx == answer_index, "choice letter")

    if raw.isdigit():
        idx = int(raw) - 1
        if 0 <= idx < len(choices):
            return MatchResult(idx == answer_index, "choice number")
        return MatchResult(False)

    norm_user = normalize(user)
    if not norm_user:
        return MatchResult(False)
    exact = [i for i, c in enumerate(choices) if normalize(c) == norm_user]
    if len(exact) == 1:
        return MatchResult(exact[0] == answer_index, "choice text")
    prefix = [i for i, c in enumerate(choices) if normalize(c).startswith(norm_user)]
    if len(prefix) == 1:
        return MatchResult(prefix[0] == answer_index, "choice text prefix")
    return MatchResult(False)


def check_answer(user: str, question: Question,
                 shuffled_choices: list[str] | None = None,
                 shuffled_answer_index: int | None = None) -> MatchResult:
    if question.answer_type == "choice":
        choices = shuffled_choices if shuffled_choices is not None else question.choices
        idx = shuffled_answer_index if shuffled_answer_index is not None else question.answer_index
        assert choices is not None and idx is not None
        return check_choice_answer(user, choices, idx)
    return check_text_answer(user, question)
