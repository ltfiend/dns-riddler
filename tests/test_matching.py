import pytest

from dns_riddler.matching import (
    check_choice_answer,
    check_text_answer,
    normalize,
)
from dns_riddler.models import Question


def make_text_q(accept, accept_regex=None, fuzzy=True):
    raw = {
        "id": "t-001",
        "level": 1,
        "category": "rfc",
        "prompt": "?",
        "answer_type": "text",
        "accept": accept,
        "explanation": "because",
        "fuzzy": fuzzy,
    }
    if accept_regex:
        raw["accept_regex"] = accept_regex
    return Question.from_dict(raw)


class TestNormalize:
    @pytest.mark.parametrize(
        "raw,expected",
        [
            ("  SERVFAIL  ", "servfail"),
            ("The DS record", "ds record"),
            ("example.com.", "example.com"),
            ("'NXDOMAIN'", "nxdomain"),
            ("rcode=2", "rcode=2"),
            ("2001:db8::1", "2001:db8::1"),
            ("a   lame    delegation", "lame delegation"),
            ("(truncation)", "truncation"),
        ],
    )
    def test_cases(self, raw, expected):
        assert normalize(raw) == expected

    def test_keeps_inner_dots_and_dashes(self):
        assert normalize("ns1.example.com") == "ns1.example.com"
        assert normalize("systemd-resolved") == "systemd-resolved"


class TestTextMatching:
    def test_exact_alias_case_insensitive(self):
        q = make_text_q(["SERVFAIL", "rcode 2"])
        assert check_text_answer("servfail", q).correct
        assert check_text_answer("Rcode 2", q).correct

    def test_regex_match(self):
        q = make_text_q(["truncated"], accept_regex=["\\btc\\b", "truncat"])
        assert check_text_answer("the tc bit is set", q).correct
        assert check_text_answer("response was truncation'd", q).correct
        assert not check_text_answer("etc etc", q).correct

    def test_fuzzy_typo(self):
        q = make_text_q(["servfail"])
        assert check_text_answer("srvfail", q).correct  # 1 char off, alias >= 6

    def test_fuzzy_disabled_for_short_aliases(self):
        q = make_text_q(["aaaa"])
        assert not check_text_answer("aaa", q).correct

    def test_fuzzy_opt_out(self):
        q = make_text_q(["servfail"], fuzzy=False)
        assert not check_text_answer("srvfail", q).correct

    def test_fuzzy_boundary(self):
        q = make_text_q(["lame delegation"])
        assert check_text_answer("lame delegatoin", q).correct
        assert not check_text_answer("tame relegation station", q).correct

    def test_empty_input(self):
        q = make_text_q(["anything"])
        assert not check_text_answer("", q).correct
        assert not check_text_answer("   ", q).correct

    def test_match_result_reports_rule(self):
        q = make_text_q(["servfail"], accept_regex=["rcode.{0,3}2"])
        assert "alias" in check_text_answer("SERVFAIL", q).matched_via
        assert "regex" in check_text_answer("it's rcode 2", q).matched_via
        assert "fuzzy" in check_text_answer("servfial", q).matched_via


class TestChoiceMatching:
    CHOICES = ["Alpha answer", "Bravo answer", "Charlie answer", "Delta answer"]

    def test_letter(self):
        assert check_choice_answer("b", self.CHOICES, 1).correct
        assert check_choice_answer("B", self.CHOICES, 1).correct
        assert check_choice_answer("b)", self.CHOICES, 1).correct
        assert not check_choice_answer("a", self.CHOICES, 1).correct

    def test_letter_out_of_range(self):
        assert not check_choice_answer("e", self.CHOICES, 1).correct

    def test_number_one_based(self):
        assert check_choice_answer("2", self.CHOICES, 1).correct
        assert not check_choice_answer("3", self.CHOICES, 1).correct
        assert not check_choice_answer("0", self.CHOICES, 1).correct

    def test_full_text(self):
        assert check_choice_answer("bravo answer", self.CHOICES, 1).correct

    def test_unambiguous_prefix(self):
        assert check_choice_answer("bravo", self.CHOICES, 1).correct

    def test_ambiguous_prefix_rejected(self):
        choices = ["alpha one", "alpha two", "beta"]
        assert not check_choice_answer("alpha", choices, 0).correct
