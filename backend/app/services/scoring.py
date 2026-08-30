from app.services.llm_client import chat_json

DEFAULT_SCORING_WEIGHTS = {
    "required_skills": 35,
    "experience": 25,
    "preferred_skills": 15,
    "education": 15,
    "certifications": 5,
    "industry_experience": 5,
}

DEFAULT_SCORE_THRESHOLDS = {"strong": 90, "good": 75, "potential": 60}

FAIRNESS_RULE = (
    "Base every judgment strictly on job-relevant qualifications (skills, experience, education, "
    "certifications). Never consider or infer race, ethnicity, religion, gender, age, disability, "
    "marital or family status, pregnancy, political affiliation, or other protected/personal "
    "characteristics — including inferring them from names, addresses, schools, photographs, or "
    "languages. Do not mention such characteristics even in passing."
)

EVIDENCE_RULE = (
    "For every claim, be clear about its basis: state it plainly when the CV explicitly says so; "
    "say \"approximately\" or \"based on listed dates/roles\" when you are reasonably deriving it "
    "(e.g. totaling experience from employment date ranges); and never convert an absence of "
    "information into a negative claim — use \"not established from CV\" instead."
)

SCORING_PROMPT = """
You are a senior recruiter with 15 years of experience evaluating candidates against a specific role.
Evaluate the candidate strictly against the REQUIREMENTS list below — do not invent additional requirements.

""" + FAIRNESS_RULE + """

""" + EVIDENCE_RULE + """

For EACH requirement, decide a result:
- "meets" — the CV clearly demonstrates this (stated or reasonably derived)
- "not_established" — the CV does not clearly say either way (default when unsure; never guess)
- "does_not_meet" — the CV explicitly contradicts or rules this out

Only use "does_not_meet" when you can quote/paraphrase specific CV evidence for it. If you cannot cite
evidence, use "not_established" instead. Never fabricate candidate experience.

Also score these categories from 0-100 (0 = no evidence at all, 100 = fully and clearly meets):
required_skills, preferred_skills, experience, education, certifications, industry_experience
(score a category 0 if the job has no requirements in that category).

List "strengths" (job-relevant qualifications clearly present) and "concerns" (missing/unclear or
weak areas — phrase missing information as "X not established from CV", not "candidate lacks X",
unless the CV explicitly rules it out).

REQUIREMENTS:
{requirements_list}

CANDIDATE PROFILE:
Name: {name}
Current Role: {current_role}
Skills: {skills}
Years of Experience: {experience_years}
Education: {education}
Certifications: {certifications}
Employment History: {employment_history}
Summary: {summary}

CV TEXT:
{cv_text}

Return valid JSON only, in this exact shape:
{{
  "breakdown": {{
    "required_skills": <0-100>, "preferred_skills": <0-100>, "experience": <0-100>,
    "education": <0-100>, "certifications": <0-100>, "industry_experience": <0-100>
  }},
  "requirements": [
    {{"id": <requirement id from the list>, "result": "meets|not_established|does_not_meet", "evidence": "<short quote/paraphrase or ''>"}}
  ],
  "strengths": ["...", "..."],
  "concerns": ["...", "..."]
}}
"""


def build_requirement_items(structured_requirements: dict) -> list[dict]:
    req = structured_requirements or {}
    items: list[dict] = []

    def add(label: str, category: str, is_hard: bool):
        if label and str(label).strip():
            items.append({"label": str(label).strip(), "category": category, "is_hard": is_hard})

    for skill in req.get("required_skills") or []:
        add(skill, "required_skills", True)
    for skill in req.get("preferred_skills") or []:
        add(skill, "preferred_skills", False)

    min_years = req.get("min_experience_years") or 0
    if min_years:
        add(f"{min_years}+ years of relevant experience", "experience", True)

    if req.get("education"):
        add(req["education"], "education", False)

    for cert in req.get("certifications") or []:
        add(cert, "certifications", False)

    if req.get("work_authorization"):
        add(f"Work authorization: {req['work_authorization']}", "location_work_auth", True)
    if req.get("location"):
        add(f"Location: {req['location']}" + (f" ({req['work_mode']})" if req.get("work_mode") else ""), "location_work_auth", False)

    if req.get("industry"):
        add(f"Industry experience: {req['industry']}", "industry_experience", False)
    if req.get("management_experience"):
        add("Management/team leadership experience", "other", False)
    for lang in req.get("languages") or []:
        add(f"Language: {lang}", "other", False)
    if req.get("notice_period"):
        add(f"Notice period: {req['notice_period']}", "other", False)

    for custom in req.get("custom_requirements") or []:
        if isinstance(custom, dict) and custom.get("label"):
            add(custom["label"], "other", bool(custom.get("is_hard")))

    if not items:
        add("Overall fit for the role as described", "other", False)

    for idx, item in enumerate(items):
        item["id"] = idx
    return items


def get_tier(score: float, thresholds: dict | None = None) -> str:
    t = thresholds or DEFAULT_SCORE_THRESHOLDS
    if score >= t.get("strong", 90):
        return "Strong Match"
    if score >= t.get("good", 75):
        return "Good Match"
    if score >= t.get("potential", 60):
        return "Potential Match"
    return "Low Match"


def _error(message: str) -> dict:
    return {
        "score": 0,
        "status": "Low Match",
        "reason": ["Scoring could not be completed."],
        "breakdown": {},
        "requirement_results": [],
        "strengths": [],
        "concerns": [],
        "meets_required": None,
        "error": message,
    }


async def score_candidate(candidate: dict, job: dict) -> dict:
    description = job.get("description", "")
    if not description or len(description.strip()) < 30:
        return _error("Job description is too short.")

    cv_text = candidate.get("raw_text") or candidate.get("cv_text") or ""
    if not cv_text and not candidate.get("skills"):
        return _error("Candidate data is empty.")

    weights = job.get("scoring_weights") or DEFAULT_SCORING_WEIGHTS
    thresholds = job.get("score_thresholds") or DEFAULT_SCORE_THRESHOLDS
    items = build_requirement_items(job.get("structured_requirements") or {})
    requirements_list = "\n".join(
        f"{item['id']}. [{'HARD/mandatory' if item['is_hard'] else 'soft/preferred'}] {item['label']}"
        for item in items
    )

    prompt = SCORING_PROMPT.format(
        requirements_list=requirements_list,
        name=candidate.get("name", "Unknown"),
        current_role=candidate.get("current_role", ""),
        skills=candidate.get("skills", ""),
        experience_years=candidate.get("experience_years", 0),
        education=candidate.get("education", ""),
        certifications=", ".join(candidate.get("certifications") or []),
        employment_history=str(candidate.get("employment_history") or []),
        summary=candidate.get("summary", candidate.get("notes", "")),
        cv_text=cv_text[:5000],
    )
    result = await chat_json(
        [
            {"role": "system", "content": "Return valid JSON only."},
            {"role": "user", "content": prompt},
        ],
        temperature=0.2,
        max_tokens=1400,
        org_id=candidate.get("organization_id", ""),
    )
    if result is None:
        return _error("AI analysis temporarily failed (invalid response). Please retry.")

    try:
        breakdown = {
            cat: max(0.0, min(100.0, float((result.get("breakdown") or {}).get(cat, 0))))
            for cat in DEFAULT_SCORING_WEIGHTS
        }

        results_by_id = {r.get("id"): r for r in result.get("requirements") or [] if isinstance(r, dict)}
        requirement_results = []
        for item in items:
            llm_result = results_by_id.get(item["id"], {})
            outcome = llm_result.get("result", "not_established")
            evidence = (llm_result.get("evidence") or "").strip()
            if outcome == "does_not_meet" and not evidence:
                outcome = "not_established"
            if outcome not in ("meets", "not_established", "does_not_meet"):
                outcome = "not_established"
            requirement_results.append(
                {
                    "label": item["label"],
                    "category": item["category"],
                    "is_hard": item["is_hard"],
                    "result": outcome,
                    "evidence": evidence,
                }
            )

        meets_required = all(r["result"] == "meets" for r in requirement_results if r["is_hard"])

        total_weight = sum(weights.values()) or 1
        overall = sum(breakdown.get(cat, 0) * weights.get(cat, 0) for cat in breakdown) / total_weight
        overall = round(max(0.0, min(100.0, overall)))

        strengths = result.get("strengths") or []
        concerns = result.get("concerns") or []
        if isinstance(strengths, str):
            strengths = [strengths]
        if isinstance(concerns, str):
            concerns = [concerns]

        return {
            "score": overall,
            "status": get_tier(overall, thresholds),
            "breakdown": breakdown,
            "requirement_results": requirement_results,
            "strengths": strengths,
            "concerns": concerns,
            "reason": strengths,
            "meets_required": meets_required,
            "error": None,
        }
    except Exception as exc:
        return _error(str(exc))


def recompute_score(breakdown: dict, weights: dict, thresholds: dict | None = None) -> tuple[int, str]:
    """Recompute overall score/tier from an already-stored breakdown when weights or
    thresholds change — no LLM call needed."""
    weights = weights or DEFAULT_SCORING_WEIGHTS
    total_weight = sum(weights.values()) or 1
    overall = sum(float(breakdown.get(cat, 0) or 0) * weights.get(cat, 0) for cat in weights) / total_weight
    overall = round(max(0.0, min(100.0, overall)))
    return overall, get_tier(overall, thresholds)
