from app.services.ask_router import try_deterministic_answer

CANDIDATES = [
    {"id": "1", "name": "Alice", "score": 95, "score_status": "Strong Match", "meets_required": True, "processing_status": "Completed"},
    {"id": "2", "name": "Bob", "score": 80, "score_status": "Good Match", "meets_required": False, "processing_status": "Completed"},
    {"id": "3", "name": "Carol", "score": 55, "score_status": "Low Match", "meets_required": False, "processing_status": "Failed", "processing_error": "Could not extract text"},
    # Dave has never been scored (score is null, e.g. still Queued) — must never appear in
    # score-based results, since null means "not scored" not "scored 0".
    {"id": "4", "name": "Dave", "score": None, "score_status": None, "meets_required": None, "processing_status": "Queued"},
    # Eve was genuinely scored 0/100 (a real "no match at all") — this is a legitimate score,
    # not an unscored sentinel, so she must still appear in score-based results.
    {"id": "5", "name": "Eve", "score": 0, "score_status": "Low Match", "meets_required": False, "processing_status": "Completed"},
]


def test_score_above_threshold():
    result = try_deterministic_answer("which candidates have a score above 90", CANDIDATES)
    assert result is not None
    assert result["cited_candidate_ids"] == ["1"]
    assert "Alice" in result["answer"]


def test_score_below_threshold_excludes_unscored_but_includes_zero():
    result = try_deterministic_answer("show candidates with score below 60", CANDIDATES)
    assert result is not None
    # Eve (0) and Carol (55) were genuinely scored and qualify; Dave (null / never scored) must not.
    assert result["cited_candidate_ids"] == ["5", "3"]


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
    assert set(result["cited_candidate_ids"]) == {"2", "3", "5"}


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
