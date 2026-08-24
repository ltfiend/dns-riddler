"""Validates every shipped question — the content author's safety net."""

import pytest

from dns_riddler import bank
from dns_riddler.models import CATEGORIES, BankError, Question


@pytest.fixture(scope="module")
def questions():
    return bank.load_builtin()


def test_bank_loads_and_is_reasonably_sized(questions):
    assert len(questions) >= 50


def test_unique_ids(questions):
    ids = [q.id for q in questions]
    assert len(ids) == len(set(ids))


def test_every_level_has_questions(questions):
    for level in (1, 2, 3, 4):
        assert any(q.level == level for q in questions), f"no questions at level {level}"


def test_every_category_has_questions(questions):
    present = {q.category for q in questions}
    assert present == set(CATEGORIES)


def test_choice_questions_well_formed(questions):
    for q in questions:
        if q.answer_type == "choice":
            assert 3 <= len(q.choices) <= 5, q.id
            assert 0 <= q.answer_index < len(q.choices), q.id
            assert len(set(q.choices)) == len(q.choices), q.id


def test_text_questions_well_formed(questions):
    for q in questions:
        if q.answer_type == "text":
            assert q.accept, q.id
            # Every alias must actually match its own question.
            from dns_riddler.matching import check_text_answer

            for alias in q.accept:
                assert check_text_answer(alias, q).correct, (
                    f"{q.id}: alias {alias!r} doesn't match its own question"
                )


def test_explanations_present(questions):
    for q in questions:
        assert len(q.explanation) > 20, f"{q.id}: explanation too thin"


def test_exhibits_have_no_tabs(questions):
    for q in questions:
        if q.exhibit:
            assert "\t" not in q.exhibit, f"{q.id}: tabs break exhibit alignment"


def test_duplicate_id_across_banks_rejected(tmp_path):
    extra = tmp_path / "extra.json"
    extra.write_text(
        '{"category": "rfc", "questions": [{"id": "rfc-001", "level": 1,'
        ' "prompt": "dup", "answer_type": "text", "accept": ["x"],'
        ' "explanation": "duplicate id should be rejected"}]}'
    )
    with pytest.raises(BankError, match="duplicate"):
        bank.load_bank(extra)


def test_vars_rejected():
    raw = {
        "id": "x-1", "level": 1, "category": "rfc", "prompt": "p",
        "answer_type": "text", "accept": ["a"], "explanation": "e" * 30,
        "vars": {"ip": "ipv4"},
    }
    with pytest.raises(BankError, match="not yet supported"):
        Question.from_dict(raw)


def test_bad_regex_rejected():
    raw = {
        "id": "x-2", "level": 1, "category": "rfc", "prompt": "p",
        "answer_type": "text", "accept": ["a"], "accept_regex": ["("],
        "explanation": "e" * 30,
    }
    with pytest.raises(BankError, match="bad regex"):
        Question.from_dict(raw)
