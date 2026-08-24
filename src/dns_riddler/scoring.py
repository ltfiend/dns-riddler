"""Scoring math and rank titles. Pure functions."""

from __future__ import annotations

STREAK_THRESHOLD = 3
STREAK_BONUS = 5
SPEED_BONUS = 5

RANKS = [
    (0, "NXDOMAIN", "The resolver came back empty. Time to hit the RFCs."),
    (20, "Lame Delegation", "You're listed as authoritative, but the answers aren't there yet."),
    (40, "Stub Resolver", "You know who to ask, but you're forwarding the hard ones."),
    (60, "Caching Resolver", "Solid answers, mostly served warm from cache."),
    (75, "Recursive Resolver", "You chase referrals all the way down and come back with answers."),
    (90, "Authoritative Server", "AA flag set. Your answers carry weight."),
    (100, "Root Server", "The hints file points at you. Flawless."),
]


def base_points(level: int) -> int:
    return level * 10


def question_points(
    level: int,
    correct: bool,
    streak_before: int,
    elapsed: float,
    time_limit: float | None,
) -> int:
    """Points for one answer. streak_before = consecutive correct answers so far."""
    if not correct:
        return 0
    points = base_points(level)
    if streak_before + 1 >= STREAK_THRESHOLD:
        points += STREAK_BONUS
    if time_limit is not None and elapsed < time_limit / 2:
        points += SPEED_BONUS
    return points


def rank_for(score: int, max_score: int) -> tuple[str, str]:
    """Return (title, blurb) for a final score."""
    pct = 0.0 if max_score <= 0 else 100.0 * score / max_score
    title, blurb = RANKS[0][1], RANKS[0][2]
    for threshold, t, b in RANKS:
        if pct >= threshold:
            title, blurb = t, b
    return title, blurb
