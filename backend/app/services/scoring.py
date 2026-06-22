import json
import re
from openai import OpenAI
from app.config import settings

_client: OpenAI | None = None


def get_client() -> OpenAI:
    global _client
    if _client is None:
        if not settings.openai_api_key:
            raise RuntimeError("OPENAI_API_KEY is not configured.")
        _client = OpenAI(api_key=settings.openai_api_key)
    return _client

SCORING_PROMPT = """
You are a senior recruiter with 15 years of experience evaluating candidates.
Score the candidate against the job description. Be practical and fair.

SCORING CRITERIA (must add up to 10):
1. Skills Match (40%)
2. Experience Relevance (25%)
3. Role Fit (20%)
4. Industry Match (10%)
5. CV Quality (5%)

SCORING RULES:
- Score out of 10 (decimals allowed)
- Strong Fit = 8.0 to 10.0
- Moderate Fit = 5.0 to 7.9
- Weak Fit = below 5.0

Return valid JSON only:
{{
  "score": <number>,
  "status": "<Strong Fit | Moderate Fit | Weak Fit>",
  "reason": ["...", "...", "..."],
  "breakdown": {{
    "skills_match": <number>,
    "experience_relevance": <number>,
    "role_fit": <number>,
    "industry_match": <number>,
    "cv_quality": <number>
  }}
}}

JOB DESCRIPTION:
{job_description}

CANDIDATE PROFILE:
Name: {name}
Current Role: {current_role}
Skills: {skills}
Years of Experience: {experience_years}
Education: {education}
Summary: {summary}

CV TEXT:
{cv_text}
"""


def get_status_from_score(score: float) -> str:
    if score >= 8.0:
        return "Strong Fit"
    if score >= 5.0:
        return "Moderate Fit"
    return "Weak Fit"


def score_candidate(candidate: dict, job_description: str) -> dict:
    if not job_description or len(job_description.strip()) < 30:
        return _error("Job description is too short.")

    if not candidate.get("raw_text") and not candidate.get("cv_text") and not candidate.get("skills"):
        return _error("Candidate data is empty.")

    try:
        prompt = SCORING_PROMPT.format(
            job_description=job_description[:3000],
            name=candidate.get("name", "Unknown"),
            current_role=candidate.get("current_role", ""),
            skills=candidate.get("skills", ""),
            experience_years=candidate.get("experience_years", 0),
            education=candidate.get("education", ""),
            summary=candidate.get("summary", candidate.get("notes", "")),
            cv_text=(candidate.get("raw_text") or candidate.get("cv_text") or "")[:3000],
        )
        response = get_client().chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "Return valid JSON only."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.2,
            max_tokens=700,
        )
        raw = re.sub(r"```json|```", "", response.choices[0].message.content.strip())
        result = json.loads(raw)
        score = max(0.0, min(10.0, float(result.get("score", 0))))
        result["score"] = round(score, 1)
        result["status"] = get_status_from_score(result["score"])
        if isinstance(result.get("reason"), str):
            result["reason"] = [result["reason"]]
        result["error"] = None
        return result
    except Exception as exc:
        return _error(str(exc))


def _error(message: str) -> dict:
    return {
        "score": 0,
        "status": "Weak Fit",
        "reason": ["Scoring could not be completed."],
        "breakdown": {},
        "error": message,
    }
