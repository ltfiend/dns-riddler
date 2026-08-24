"""Game loop: ask questions, judge answers, keep score."""

from __future__ import annotations

import random
import time
from typing import Callable

from dns_riddler import bank as bank_mod
from dns_riddler import scoring
from dns_riddler.matching import check_answer
from dns_riddler.models import Answer, Question, RoundConfig, RoundResult
from dns_riddler.render import Renderer
from dns_riddler.timer import flush_stdin, timed_input

InputFn = Callable[[str, float | None], str | None]


def max_possible_score(questions: list[Question], time_limit: float | None) -> int:
    """Best case: all correct (streak bonus from question 3 on) and fast."""
    total = sum(scoring.base_points(q.level) for q in questions)
    n = len(questions)
    total += scoring.STREAK_BONUS * max(0, n - (scoring.STREAK_THRESHOLD - 1))
    if time_limit is not None:
        total += scoring.SPEED_BONUS * n
    return total


def run_round(
    config: RoundConfig,
    questions: list[Question],
    renderer: Renderer,
    input_fn: InputFn = timed_input,
    rng: random.Random | None = None,
) -> RoundResult:
    rng = rng or random.Random(config.seed)
    result = RoundResult(config=config)
    streak = 0
    total = len(questions)

    for num, q in enumerate(questions, 1):
        choices, answer_idx = bank_mod.shuffle_choices(q, rng)
        renderer.question(num, total, q, result.score, streak, choices)

        if q.answer_type == "choice":
            prompt = "Your answer (letter): "
        else:
            prompt = "Your answer: "
        if config.time_limit is not None:
            prompt = f"[{config.time_limit:g}s] {prompt}"

        start = time.monotonic()
        try:
            given = input_fn(prompt, config.time_limit)
        except KeyboardInterrupt:
            result.aborted = True
            break
        elapsed = time.monotonic() - start

        timed_out = given is None
        if timed_out:
            match_correct, matched_via = False, None
            flush_stdin()
        else:
            m = check_answer(given, q, choices, answer_idx)
            match_correct, matched_via = m.correct, m.matched_via

        points = scoring.question_points(
            q.level, match_correct, streak, elapsed, config.time_limit
        )
        streak = streak + 1 if match_correct else 0

        answer = Answer(
            question=q,
            given=given,
            correct=match_correct,
            timed_out=timed_out,
            elapsed=elapsed,
            points=points,
            matched_via=matched_via,
            shuffled_choices=choices,
            shuffled_answer_index=answer_idx,
        )
        result.answers.append(answer)
        renderer.verdict(answer, show_explanation=(config.review == "each"))

    max_score = max_possible_score(questions[: len(result.answers)] if result.aborted else questions,
                                   config.time_limit)
    renderer.summary(result, max_score)
    if config.review == "end":
        _end_review(result, renderer)
    return result


def _end_review(result: RoundResult, renderer: Renderer) -> None:
    hits = [a for a in result.answers if a.correct]
    if not hits:
        return
    renderer.console.print("\n[bold]The ones you nailed:[/bold]")
    for i, a in enumerate(result.answers, 1):
        if not a.correct:
            continue
        refs = f" [dim]({', '.join(a.question.references)})[/dim]" if a.question.references else ""
        renderer.console.print(f"  [green]#{i}[/green] {a.question.explanation}{refs}")
