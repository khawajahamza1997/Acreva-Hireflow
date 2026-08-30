from app.services.scoring import (
    build_requirement_items,
    get_tier,
    recompute_score,
    DEFAULT_SCORING_WEIGHTS,
    DEFAULT_SCORE_THRESHOLDS,
)


def test_get_tier_default_boundaries():
    assert get_tier(100) == "Strong Match"
    assert get_tier(90) == "Strong Match"
    assert get_tier(89.9) == "Good Match"
    assert get_tier(75) == "Good Match"
    assert get_tier(74.9) == "Potential Match"
    assert get_tier(60) == "Potential Match"
    assert get_tier(59.9) == "Low Match"
    assert get_tier(0) == "Low Match"


def test_get_tier_custom_thresholds():
    thresholds = {"strong": 80, "good": 60, "potential": 40}
    assert get_tier(85, thresholds) == "Strong Match"
    assert get_tier(65, thresholds) == "Good Match"
    assert get_tier(45, thresholds) == "Potential Match"
    assert get_tier(10, thresholds) == "Low Match"


def test_build_requirement_items_hard_vs_soft():
    req = {
        "required_skills": ["Python", "SQL"],
        "preferred_skills": ["AWS"],
        "min_experience_years": 5,
        "work_authorization": "UK right to work",
    }
    items = build_requirement_items(req)
    hard = [i for i in items if i["is_hard"]]
    soft = [i for i in items if not i["is_hard"]]

    assert {"Python", "SQL"}.issubset({i["label"] for i in hard})
    assert any("5+ years" in i["label"] for i in hard)
    assert any("Work authorization" in i["label"] for i in hard)
    assert any(i["label"] == "AWS" for i in soft)
    # ids must be unique and sequential
    assert [i["id"] for i in items] == list(range(len(items)))


def test_build_requirement_items_falls_back_when_empty():
    items = build_requirement_items({})
    assert len(items) == 1
    assert items[0]["is_hard"] is False


def test_recompute_score_matches_weighted_average():
    breakdown = {
        "required_skills": 100,
        "preferred_skills": 0,
        "experience": 100,
        "education": 100,
        "certifications": 0,
        "industry_experience": 0,
    }
    score, tier = recompute_score(breakdown, DEFAULT_SCORING_WEIGHTS, DEFAULT_SCORE_THRESHOLDS)
    # required_skills(35) + experience(25) + education(15) = 75% of total weight met at 100
    expected = round(100 * (35 + 25 + 15) / 100)
    assert score == expected
    assert tier == get_tier(expected, DEFAULT_SCORE_THRESHOLDS)


def test_recompute_score_normalizes_weights_not_summing_to_100():
    breakdown = {"required_skills": 100}
    weights = {"required_skills": 50}  # only one category weighted, should normalize to full weight
    score, _ = recompute_score(breakdown, weights, DEFAULT_SCORE_THRESHOLDS)
    assert score == 100
