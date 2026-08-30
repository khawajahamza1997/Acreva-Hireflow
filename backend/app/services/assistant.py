import json
from app.services.llm_client import chat_json
from app.services.scoring import FAIRNESS_RULE, EVIDENCE_RULE

NOT_ESTABLISHED = "This information was not established from the uploaded CVs."

ACTION_TYPES = ("show_candidates", "add_to_shortlist", "remove_from_shortlist", "compare", "none")
ACTIONS_REQUIRING_CONFIRMATION = {"add_to_shortlist", "remove_from_shortlist"}


ASK_PROMPT = """
You are "Ask HireFlow", a recruiter assistant answering questions about candidates for ONE specific job.
You are an assistant, not a decision-maker — you never say a candidate "should be hired."

""" + FAIRNESS_RULE + """

""" + EVIDENCE_RULE + """

Answer ONLY using the JOB and CANDIDATES data below. If the answer isn't clearly supported by this
data, say so explicitly using this exact phrase: "{not_established}"
Never invent candidate details, scores, or CV content. When you reference a candidate, use their name
exactly as given. When listing multiple candidates, use a numbered list with the specific supporting
stat for each (e.g. "1. Candidate A — 7 years").

You may optionally suggest ONE follow-up action the recruiter could take, chosen from:
- "show_candidates": highlight a set of candidates in the UI (read-only)
- "compare": open a side-by-side comparison of 2-10 candidates (read-only)
- "add_to_shortlist": add candidates to the shortlist (changes data — always needs confirmation)
- "remove_from_shortlist": remove candidates from the shortlist (changes data — always needs confirmation)
- "none": no action

Only reference candidate ids that appear in the CANDIDATES list below — never invent an id.

JOB: {job_title}
JOB REQUIREMENTS SOURCE: {requirements_version}

CANDIDATES (id, name, score, tier, meets_all_mandatory_requirements, breakdown, requirement_results,
strengths, concerns, skills, experience_years, education, certifications, employment_history,
shortlisted, processing_status):
{candidates_json}

QUESTION: {question}

Return valid JSON only, in this exact shape:
{{
  "answer": "...",
  "cited_candidate_ids": ["..."],
  "suggested_action": {{"type": "show_candidates|compare|add_to_shortlist|remove_from_shortlist|none", "candidate_ids": ["..."]}}
}}
"""


def _condense(candidate: dict) -> dict:
    return {
        "id": candidate.get("id"),
        "name": candidate.get("name"),
        "score": candidate.get("score"),
        "tier": candidate.get("score_status"),
        "meets_all_mandatory_requirements": candidate.get("meets_required"),
        "breakdown": candidate.get("score_breakdown") or {},
        "requirement_results": [
            {"label": r.get("label"), "is_hard": r.get("is_hard"), "result": r.get("result"), "evidence": r.get("evidence")}
            for r in (candidate.get("requirement_results") or [])
        ],
        "strengths": candidate.get("strengths") or [],
        "concerns": candidate.get("concerns") or [],
        "skills": candidate.get("skills") or "",
        "experience_years": candidate.get("experience_years") or 0,
        "education": candidate.get("education") or "",
        "certifications": candidate.get("certifications") or [],
        "employment_history": [
            {"title": e.get("title"), "company": e.get("company")} for e in (candidate.get("employment_history") or [])
        ],
        "shortlisted": bool(candidate.get("shortlisted")),
        "processing_status": candidate.get("processing_status"),
    }


def _fallback(message: str) -> dict:
    return {"answer": message, "cited_candidate_ids": [], "suggested_action": {"type": "none", "candidate_ids": []}}


async def ask(question: str, job: dict, candidates: list[dict]) -> dict:
    if not candidates:
        return _fallback("There are no candidates in this job's pool yet.")

    valid_ids = {c["id"] for c in candidates}
    condensed = [_condense(c) for c in candidates]

    prompt = ASK_PROMPT.format(
        not_established=NOT_ESTABLISHED,
        job_title=job.get("title", "this role"),
        requirements_version=f"v{job.get('requirements_version', 1)}",
        candidates_json=json.dumps(condensed, indent=2)[:60000],
        question=question,
    )
    result = await chat_json(
        [
            {"role": "system", "content": "Return valid JSON only."},
            {"role": "user", "content": prompt},
        ],
        temperature=0.2,
        max_tokens=800,
        org_id=job.get("organization_id", ""),
    )
    if result is None:
        return _fallback("Ask HireFlow could not answer that just now — please try again.")

    cited = [cid for cid in (result.get("cited_candidate_ids") or []) if cid in valid_ids]

    action = result.get("suggested_action") or {}
    action_type = action.get("type") if action.get("type") in ACTION_TYPES else "none"
    action_ids = [cid for cid in (action.get("candidate_ids") or []) if cid in valid_ids]
    if action_type == "none":
        action_ids = []

    return {
        "answer": result.get("answer") or NOT_ESTABLISHED,
        "cited_candidate_ids": cited,
        "suggested_action": {
            "type": action_type,
            "candidate_ids": action_ids,
            "requires_confirmation": action_type in ACTIONS_REQUIRING_CONFIRMATION,
        },
    }
