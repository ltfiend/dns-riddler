import random

import pytest
from rich.console import Console

from dns_riddler import bank as bank_mod
from dns_riddler import engine
from dns_riddler.models import Question, RoundConfig
from dns_riddler.render import Renderer


def make_question(qid, level=1, answer_type="text"):
    raw = {
        "id": qid,
        "level": level,
        "category": "rfc",
        "prompt": f"prompt for {qid}",
        "answer_type": answer_type,
        "explanation": "a sufficiently long explanation for testing",
    }
    if answer_type == "text":
        raw["accept"] = ["right"]
    else:
        raw["choices"] = ["right", "wrong-1", "wrong-2"]
        raw["answer_index"] = 0
    return Question.from_dict(raw)


def quiet_renderer():
    return Renderer(Console(file=open("/dev/null", "w"), force_terminal=False))


def scripted_input(answers):
    it = iter(answers)

    def fn(prompt, timeout):
        return next(it)

    return fn


class TestRunRound:
    def test_scoring_and_verdicts(self):
        questions = [make_question(f"q-{i}") for i in range(3)]
        config = RoundConfig(num_questions=3, seed=1)
        result = engine.run_round(
            config, questions, quiet_renderer(),
            input_fn=scripted_input(["right", "wrong", "right"]),
        )
        assert [a.correct for a in result.answers] == [True, False, True]
        assert result.score == 20  # 10 + 0 + 10, no streak of 3
        assert result.num_correct == 2

    def test_timeout_recorded(self):
        questions = [make_question("q-t")]
        config = RoundConfig(num_questions=1, time_limit=5.0)
        result = engine.run_round(
            config, questions, quiet_renderer(), input_fn=scripted_input([None])
        )
        a = result.answers[0]
        assert a.timed_out and not a.correct and a.points == 0

    def test_choice_answered_by_letter_after_shuffle(self):
        q = make_question("q-c", answer_type="choice")
        rng = random.Random(42)
        # Determine where the correct choice lands with this seed.
        probe_rng = random.Random(42)
        shuffled, idx = bank_mod.shuffle_choices(q, probe_rng)
        letter = "abc"[idx]
        result = engine.run_round(
            RoundConfig(num_questions=1, seed=42),
            [q], quiet_renderer(), input_fn=scripted_input([letter]), rng=rng,
        )
        assert result.answers[0].correct

    def test_streak_bonus_applied(self):
        questions = [make_question(f"q-{i}") for i in range(4)]
        result = engine.run_round(
            RoundConfig(num_questions=4),
            questions, quiet_renderer(),
            input_fn=scripted_input(["right"] * 4),
        )
        # 10 + 10 + 15 + 15
        assert result.score == 50

    def test_keyboard_interrupt_gives_partial_result(self):
        questions = [make_question(f"q-{i}") for i in range(3)]

        answers = iter(["right"])

        def fn(prompt, timeout):
            try:
                return next(answers)
            except StopIteration:
                raise KeyboardInterrupt

        result = engine.run_round(
            RoundConfig(num_questions=3), questions, quiet_renderer(), input_fn=fn
        )
        assert result.aborted
        assert len(result.answers) == 1


class TestSelection:
    def test_seed_reproducibility(self):
        bank = bank_mod.load_builtin()
        picked1, _ = bank_mod.select_questions(bank, 2, 10, rng=random.Random(99))
        picked2, _ = bank_mod.select_questions(bank, 2, 10, rng=random.Random(99))
        assert [q.id for q in picked1] == [q.id for q in picked2]

    def test_level_filtering_prefers_exact(self):
        bank = bank_mod.load_builtin()
        exact_count = sum(1 for q in bank if q.level == 3)
        n = min(5, exact_count)
        picked, notices = bank_mod.select_questions(bank, 3, n, rng=random.Random(1))
        assert all(q.level == 3 for q in picked)
        assert not notices

    def test_backfill_when_pool_small(self):
        bank = bank_mod.load_builtin()
        pool = [q for q in bank if q.category == "troubleshooting"]
        # Request more than the whole category holds: expect every question
        # back, plus both a backfill notice and a shortfall notice.
        picked, notices = bank_mod.select_questions(
            bank, 4, len(pool) + 5, categories=["troubleshooting"], rng=random.Random(1)
        )
        assert len(picked) == len(pool)
        assert len(notices) == 2

    def test_bad_category_pool(self):
        with pytest.raises(Exception):
            bank_mod.select_questions([], 1, 5)
