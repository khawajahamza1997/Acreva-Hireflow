from app.services.ask_router import try_deterministic_answer

CANDIDATES = [
    {"id": "1", "name": "Alice", "score": 95, "score_status": "Strong Match", "meets_required": True, "processing_status": "Completed"},
    {"id": "2", "name": "Bob", "score": 80, "score_status": "Good Match", "meets_required": False, "processing_status": "Completed"},
    {"id": "3", "name": "Carol", "score": 55, "score_status": "Low Match", "meets_required": False, "processing_status": "Failed", "processing_error": "Could not extract text"},
    {"id": "4", "name": "Dave", "score": 0, "score_status": None, "meets_required": None, "processing_status": "Queued"},
]


def test_score_above_threshold():
    result = try_deterministic_answer("which candidates have a score above 90", CANDIDATES)
    assert result is not None
    assert result["cited_candidate_ids"] == ["1"]
    assert "Alice" in result["answer"]


def test_score_below_threshold_excludes_unscored():
    result = try_deterministic_answer("show candidates with score below 60", CANDIDATES)
    assert result is not None
    # Carol (55) qualifies; Dave (0) must not, since 0 means "not scored" not "low score"
    assert result["cited_candidate_ids"] == ["3"]


def test_top_n_by_score():
    result = try_deterministic_answer("show me the top 2 candidates by score", CANDIDATES)
    assert result is not None
    assert result["cited_candidate_ids"] == ["1", "2"]
    assert result["suggested_action"]["type"] == "show_candidates"
    assert result["suggested_action"]["requires_confirmation"] is False


def test_meets_all_requirements():
    result = try_deterministic_answer("which candidates meet all mandatory requirements", CANDIDATES)
    assert result is not None
    assert result["cited_candidate_ids"] == ["1"]


def test_missing_requirements():
    result = try_deterministic_answer("which candidates are missing requirements", CANDIDATES)
    assert result is not None
    assert set(result["cited_candidate_ids"]) == {"2", "3"}


def test_failed_processing():
    result = try_deterministic_answer("which cvs failed processing", CANDIDATES)
    assert result is not None
    assert result["cited_candidate_ids"] == ["3"]


def test_mutating_question_falls_back_to_llm():
    # Anything that could change data must never be handled deterministically.
    assert try_deterministic_answer("add candidates with score above 90 to the shortlist", CANDIDATES) is None
    assert try_deterministic_answer("reject the candidates below 60", CANDIDATES) is None
    assert try_deterministic_answer("email the top 5 candidates", CANDIDATES) is None


def test_open_ended_question_returns_none():
    assert try_deterministic_answer("why was Alice ranked above Bob?", CANDIDATES) is None
    assert try_deterministic_answer("summarize the top candidates", CANDIDATES) is None
