from app.services.processing import classify_completion_status


def test_short_cv_flagged_needs_review():
    assert classify_completion_status("only a few words here", min_words=50) == "Needs review"


def test_empty_cv_flagged_needs_review():
    assert classify_completion_status("", min_words=50) == "Needs review"


def test_long_cv_completed():
    text = " ".join(["word"] * 60)
    assert classify_completion_status(text, min_words=50) == "Completed"


def test_boundary_exactly_at_threshold_is_completed():
    text = " ".join(["word"] * 50)
    assert classify_completion_status(text, min_words=50) == "Completed"
