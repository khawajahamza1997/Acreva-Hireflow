import re

MUTATING_WORDS = ("add", "remove", "shortlist", "reject", "delete", "email", "send", "invite")

_SCORE_ABOVE = re.compile(r"score.{0,10}(?:>|>=|above|over|greater than)\s*(\d+(?:\.\d+)?)")
_SCORE_BELOW = re.compile(r"score.{0,10}(?:<|<=|below|under|less than)\s*(\d+(?:\.\d+)?)")
_TOP_N = re.compile(r"top\s+(\d+)")


def _has_mutating_word(question: str) -> bool:
    q = question.lower()
    return any(word in q for word in MUTATING_WORDS)


def _format_list(candidates: list[dict], stat_fn) -> str:
    lines = [f"{i+1}. {c.get('name', 'Candidate')} — {stat_fn(c)}" for i, c in enumerate(candidates)]
    return "\n".join(lines)


def try_deterministic_answer(question: str, candidates: list[dict]) -> dict | None:
    """Answer simple numeric/filter/sort questions directly from already-loaded candidate
    data — no LLM call, no risk of the model guessing at a comparison it should just compute.
    Returns None if the question doesn't match a safe deterministic pattern, so the caller
    falls back to the LLM path (which also owns anything that could mutate data)."""
    if _has_mutating_word(question):
        return None

    q = question.lower()

    match = _SCORE_ABOVE.search(q)
    if match:
        threshold = float(match.group(1))
        matches = sorted(
            [c for c in candidates if (c.get("score") or 0) > threshold],
            key=lambda c: c.get("score") or 0,
            reverse=True,
        )
        if not matches:
            answer = f"No candidates have a match score above {threshold:g}."
        else:
            answer = f"{len(matches)} candidate(s) have a match score above {threshold:g}:\n" + _format_list(
                matches, lambda c: f"{c.get('score')}/100"
            )
        return _result(answer, matches)

    match = _SCORE_BELOW.search(q)
    if match:
        threshold = float(match.group(1))
        matches = sorted(
            [c for c in candidates if (c.get("score") or 0) < threshold and (c.get("score") or 0) > 0],
            key=lambda c: c.get("score") or 0,
        )
        if not matches:
            answer = f"No scored candidates have a match score below {threshold:g}."
        else:
            answer = f"{len(matches)} candidate(s) have a match score below {threshold:g}:\n" + _format_list(
                matches, lambda c: f"{c.get('score')}/100"
            )
        return _result(answer, matches)

    match = _TOP_N.search(q)
    if match and ("score" in q or "match" in q or "candidate" in q):
        n = int(match.group(1))
        matches = sorted(candidates, key=lambda c: c.get("score") or 0, reverse=True)[:n]
        answer = f"Top {len(matches)} candidate(s) by match score:\n" + _format_list(
            matches, lambda c: f"{c.get('score')}/100 ({c.get('score_status', '')})"
        )
        return _result(answer, matches, action_type="show_candidates")

    if ("meet all" in q or "meets all" in q) and "requirement" in q:
        matches = [c for c in candidates if c.get("meets_required") is True]
        if not matches:
            answer = "No candidates are confirmed to meet all mandatory requirements yet."
        else:
            answer = f"{len(matches)} candidate(s) meet all mandatory requirements:\n" + _format_list(
                matches, lambda c: f"{c.get('score')}/100"
            )
        return _result(answer, matches)

    if ("missing" in q or "does not meet" in q or "don't meet" in q or "doesn't meet" in q) and "requirement" in q:
        matches = [c for c in candidates if c.get("meets_required") is False]
        if not matches:
            answer = "No candidates are currently flagged as missing a mandatory requirement."
        else:
            answer = f"{len(matches)} candidate(s) do not yet meet all mandatory requirements:\n" + _format_list(
                matches, lambda c: c.get("score_status", "")
            )
        return _result(answer, matches)

    if "failed" in q and ("process" in q or "cv" in q or "analy" in q):
        matches = [c for c in candidates if c.get("processing_status") == "Failed"]
        if not matches:
            answer = "No candidates currently have failed processing."
        else:
            answer = f"{len(matches)} candidate(s) failed processing:\n" + _format_list(
                matches, lambda c: c.get("processing_error", "") or "Unknown error"
            )
        return _result(answer, matches)

    return None


def _result(answer: str, matches: list[dict], action_type: str = "none") -> dict:
    ids = [c["id"] for c in matches]
    return {
        "answer": answer,
        "cited_candidate_ids": ids,
        "suggested_action": {
            "type": "show_candidates" if (action_type == "show_candidates" or ids) else "none",
            "candidate_ids": ids,
            "requires_confirmation": False,
        },
    }
