from app.services.llm_client import chat_json

EXTRACT_PROMPT = """
You are an expert recruiter. Read the job description below and extract structured
screening criteria as a valid JSON object — nothing else, no explanation.

Return this exact shape:
{{
  "required_skills": ["...", "..."],
  "preferred_skills": ["...", "..."],
  "min_experience_years": <number>,
  "education": "<short text, e.g. 'Bachelor's degree in Computer Science'>",
  "certifications": ["...", "..."],
  "location": "<short text or ''>",
  "work_mode": "<'remote' | 'hybrid' | 'onsite' | ''>",
  "work_authorization": "<short text or ''>",
  "salary_min": <number or null>,
  "salary_max": <number or null>,
  "industry": "<short text or ''>",
  "management_experience": <true | false>,
  "languages": ["...", "..."],
  "notice_period": "<short text or ''>",
  "custom_requirements": [{{"label": "...", "is_hard": <true|false>}}]
}}

Rules:
- required_skills are things the description states as mandatory ("must have", "required").
- preferred_skills are things described as a plus/nice-to-have.
- If a field cannot be determined, use "" / 0 / null / an empty array as appropriate — never invent details.
- Return only valid JSON.

JOB DESCRIPTION:
{description}
"""


def _blank() -> dict:
    return {
        "required_skills": [],
        "preferred_skills": [],
        "min_experience_years": 0,
        "education": "",
        "certifications": [],
        "location": "",
        "work_mode": "",
        "work_authorization": "",
        "salary_min": None,
        "salary_max": None,
        "industry": "",
        "management_experience": False,
        "languages": [],
        "notice_period": "",
        "custom_requirements": [],
    }


async def extract_requirements(description: str, org_id: str = "") -> dict:
    if not description or len(description.strip()) < 30:
        return _blank()

    prompt = EXTRACT_PROMPT.format(description=description[:6000])
    data = await chat_json(
        [{"role": "user", "content": prompt}],
        temperature=0.1,
        max_tokens=900,
        org_id=org_id,
    )
    if data is None:
        return _blank()

    blank = _blank()
    blank.update({k: v for k, v in data.items() if k in blank})
    return blank
