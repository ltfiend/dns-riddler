from dns_riddler import scoring


class TestQuestionPoints:
    def test_base_points_by_level(self):
        for level, expected in [(1, 10), (2, 20), (3, 30), (4, 40)]:
            assert scoring.question_points(level, True, 0, 10.0, None) == expected

    def test_wrong_answer_scores_zero(self):
        assert scoring.question_points(4, False, 5, 1.0, 30.0) == 0

    def test_streak_bonus_kicks_in_at_third_consecutive(self):
        assert scoring.question_points(1, True, 1, 10.0, None) == 10  # streak becomes 2
        assert scoring.question_points(1, True, 2, 10.0, None) == 15  # streak becomes 3
        assert scoring.question_points(1, True, 7, 10.0, None) == 15

    def test_speed_bonus_only_when_timed(self):
        assert scoring.question_points(1, True, 0, 5.0, 30.0) == 15  # under half budget
        assert scoring.question_points(1, True, 0, 20.0, 30.0) == 10  # over half budget
        assert scoring.question_points(1, True, 0, 0.1, None) == 10  # untimed: no bonus


class TestRanks:
    def test_boundaries(self):
        assert scoring.rank_for(19, 100)[0] == "NXDOMAIN"
        assert scoring.rank_for(20, 100)[0] == "Lame Delegation"
        assert scoring.rank_for(59, 100)[0] == "Stub Resolver"
        assert scoring.rank_for(60, 100)[0] == "Caching Resolver"
        assert scoring.rank_for(89, 100)[0] == "Recursive Resolver"
        assert scoring.rank_for(99, 100)[0] == "Authoritative Server"
        assert scoring.rank_for(100, 100)[0] == "Root Server"

    def test_zero_max_score_is_safe(self):
        title, _ = scoring.rank_for(0, 0)
        assert title == "NXDOMAIN"

    def test_over_100_percent_is_root_server(self):
        assert scoring.rank_for(120, 100)[0] == "Root Server"
