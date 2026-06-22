# ============================================================
# scoring_agent.py
# ============================================================
# Purpose: Score a candidate against a job description using GPT-4.
#
# Scoring weights (must match what we show recruiters in the UI):
#   Skills Match           40%
#   Experience Relevance   25%
#   Role Fit               20%
#   Industry Match         10%
#   CV Quality             5%
#
# Main function: score_candidate(candidate, job_description)
#   → Returns a dict with score, status, reason, and breakdown
# ============================================================

import json
import re
import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


# ------------------------------------------------------------
# SCORING PROMPT
# ------------------------------------------------------------
# This prompt is the heart of the product.
# It instructs GPT-4 to behave like a senior recruiter and
# evaluate the candidate using the exact weighted criteria.
# ------------------------------------------------------------

SCORING_PROMPT = """
You are a senior recruiter with 15 years of experience evaluating candidates.

Your job is to score the candidate below against the provided job description.
Be practical, fair, and human — avoid over-technical analysis.

SCORING CRITERIA (must add up to 10):
1. Skills Match           (40%) — How well do the candidate's skills match the JD requirements?
2. Experience Relevance   (25%) — Is their work history relevant to this role?
3. Role Fit               (20%) — Does their seniority, background and career direction fit?
4. Industry Match         (10%) — Have they worked in a relevant industry or sector?
5. CV Quality              (5%) — Is the CV clear, professional, and well-communicated?

SCORING RULES:
- Score out of 10 (decimals allowed, e.g. 7.5)
- Be realistic — do not inflate scores
- Strong Fit   = 8.0 to 10.0
- Moderate Fit = 5.0 to 7.9
- Weak Fit     = below 5.0

OUTPUT FORMAT:
Return a valid JSON object — nothing else, no markdown, no explanation outside the JSON.

{{
  "score": <number between 0 and 10>,
  "status": "<Strong Fit | Moderate Fit | Weak Fit>",
  "reason": [
    "<bullet point 1 — most important observation>",
    "<bullet point 2>",
    "<bullet point 3>",
    "<bullet point 4 — optional>"
  ],
  "breakdown": {{
    "skills_match": <score out of 4.0>,
    "experience_relevance": <score out of 2.5>,
    "role_fit": <score out of 2.0>,
    "industry_match": <score out of 1.0>,
    "cv_quality": <score out of 0.5>
  }}
}}

---

JOB DESCRIPTION:
{job_description}

---

CANDIDATE PROFILE:
Name: {name}
Current Role: {current_role}
Skills: {skills}
Years of Experience: {experience_years}
Education: {education}
Professional Summary: {summary}

CV TEXT (first 3000 characters):
{cv_text}
"""


# ------------------------------------------------------------
# STATUS HELPER
# ------------------------------------------------------------

def get_status_from_score(score: float) -> str:
    """
    Converts a numeric score into a human-readable status label.
    Used both here and in the dashboard to ensure consistency.
    """
    if score >= 8.0:
        return "Strong Fit"
    elif score >= 5.0:
        return "Moderate Fit"
    else:
        return "Weak Fit"


# ------------------------------------------------------------
# MAIN SCORING FUNCTION
# ------------------------------------------------------------

def score_candidate(candidate: dict, job_description: str) -> dict:
    """
    Scores one candidate against a job description.

    Args:
        candidate       : dict from cv_parser.process_uploaded_cv()
        job_description : string pasted by recruiter in the app

    Returns a dict like:
    {
        "score": 8.4,
        "status": "Strong Fit",
        "reason": ["Strong skills match...", "Relevant experience..."],
        "breakdown": {
            "skills_match": 3.4,
            "experience_relevance": 2.1,
            "role_fit": 1.8,
            "industry_match": 0.7,
            "cv_quality": 0.4
        },
        "error": None   ← populated only if something goes wrong
    }
    """

    if not job_description or len(job_description.strip()) < 30:
        return _error_result("Job description is too short. Please paste a full job description.")

    if not candidate.get("raw_text") and not candidate.get("skills"):
        return _error_result("Candidate data is empty. CV may not have been parsed correctly.")

    try:
        prompt = SCORING_PROMPT.format(
            job_description=job_description[:3000],
            name=candidate.get("name", "Unknown"),
            current_role=candidate.get("current_role", "Not specified"),
            skills=candidate.get("skills", "Not specified"),
            experience_years=candidate.get("experience_years", "Unknown"),
            education=candidate.get("education", "Not specified"),
            summary=candidate.get("summary", ""),
            cv_text=candidate.get("raw_text", "")[:3000]
        )

        response = client.chat.completions.create(
            model="gpt-4o",          # Full GPT-4o for scoring — quality matters here
            messages=[
                {
                    "role": "system",
                    "content": "You are a senior recruiter. Always return valid JSON only."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=0.2,         # Slightly creative but mostly consistent
            max_tokens=700
        )

        raw = response.choices[0].message.content.strip()

        # Strip markdown fences if GPT wraps output in ```json ... ```
        raw = re.sub(r"```json|```", "", raw).strip()

        result = json.loads(raw)

        # Validate score is a number and clamp between 0 and 10
        score = float(result.get("score", 0))
        score = max(0.0, min(10.0, score))
        result["score"] = round(score, 1)

        # Always re-derive status from score so it's consistent
        result["status"] = get_status_from_score(result["score"])

        # Ensure reason is a list
        if isinstance(result.get("reason"), str):
            result["reason"] = [result["reason"]]

        result["error"] = None
        return result

    except json.JSONDecodeError:
        return _error_result("AI response could not be parsed. Please try again.")

    except Exception as e:
        return _error_result(str(e))


# ------------------------------------------------------------
# BATCH SCORING
# ------------------------------------------------------------

def score_all_candidates(candidates: list, job_description: str) -> list:
    """
    Scores a list of candidates against the same job description.
    Returns the same list with a 'scoring_result' key added to each.

    Usage in app.py:
        scored = score_all_candidates(candidates, job_description)
    """
    results = []
    for candidate in candidates:
        result = score_candidate(candidate, job_description)
        candidate["scoring_result"] = result
        results.append(candidate)
    return results


# ------------------------------------------------------------
# FORMAT FOR DISPLAY
# ------------------------------------------------------------

def format_score_for_display(scoring_result: dict) -> str:
    """
    Returns a clean multi-line string for showing score results in the UI.

    Example output:
        Score: 8.4 / 10
        Status: Strong Fit

        - Strong match with required sales skills
        - Relevant B2B experience in a similar role
        - Career direction aligns with the position
    """
    if scoring_result.get("error"):
        return f"Scoring failed: {scoring_result['error']}"

    score = scoring_result.get("score", 0)
    status = scoring_result.get("status", "Unknown")
    reasons = scoring_result.get("reason", [])

    lines = [
        f"Score: {score} / 10",
        f"Status: {status}",
        "",
    ]

    for point in reasons:
        lines.append(f"- {point}")

    return "\n".join(lines)


# ------------------------------------------------------------
# ERROR HELPER
# ------------------------------------------------------------

def _error_result(message: str) -> dict:
    """Returns a safe blank result when scoring fails."""
    return {
        "score": 0,
        "status": "Weak Fit",
        "reason": ["Scoring could not be completed."],
        "breakdown": {
            "skills_match": 0,
            "experience_relevance": 0,
            "role_fit": 0,
            "industry_match": 0,
            "cv_quality": 0
        },
        "error": message
    }
