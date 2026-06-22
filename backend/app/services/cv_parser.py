import io
import json
import re
import pdfplumber
import docx
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

PARSE_PROMPT = """
You are an expert recruitment assistant.
Read the CV text below and extract the following information.
Return your answer as a valid JSON object — nothing else, no explanation.

Fields to extract:
- name, email, phone, current_role, skills (comma-separated string),
  experience_years (number), education, summary (1-2 sentences)

Rules:
- If a field cannot be found, use "" or 0
- Do not invent information
- Return only valid JSON

CV Text:
{cv_text}
"""


def extract_text_from_bytes(content: bytes, filename: str) -> str:
    filename_lower = filename.lower()
    file_obj = io.BytesIO(content)

    if filename_lower.endswith(".pdf"):
        text = ""
        with pdfplumber.open(file_obj) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
        return text.strip()

    if filename_lower.endswith(".docx"):
        document = docx.Document(file_obj)
        return "\n".join(p.text for p in document.paragraphs if p.text.strip()).strip()

    if filename_lower.endswith(".txt"):
        return content.decode("utf-8", errors="ignore").strip()

    return ""


def parse_cv(cv_text: str, filename: str) -> dict:
    if not cv_text or len(cv_text.strip()) < 50:
        return _blank(filename, "Could not extract text from this CV.")

    try:
        prompt = PARSE_PROMPT.format(cv_text=cv_text[:4000])
        response = get_client().chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
            max_tokens=600,
        )
        raw = re.sub(r"```json|```", "", response.choices[0].message.content.strip())
        data = json.loads(raw)
        data["filename"] = filename
        data["raw_text"] = cv_text[:8000]
        return data
    except Exception as exc:
        return _blank(filename, str(exc))


def process_cv_bytes(content: bytes, filename: str) -> dict:
    raw_text = extract_text_from_bytes(content, filename)
    return parse_cv(raw_text, filename)


def _blank(filename: str, error: str = "") -> dict:
    return {
        "name": "Unknown",
        "email": "",
        "phone": "",
        "current_role": "",
        "skills": "",
        "experience_years": 0,
        "education": "",
        "summary": "",
        "filename": filename,
        "raw_text": "",
        "parse_error": error,
    }
