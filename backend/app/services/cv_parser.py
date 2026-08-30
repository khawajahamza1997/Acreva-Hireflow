import io
import pdfplumber
import docx
from app.services.llm_client import chat_json

PARSE_PROMPT = """
You are an expert recruitment assistant.
Read the CV text below and extract the following information.
Return your answer as a valid JSON object — nothing else, no explanation.

Fields to extract:
- name, email, phone, location (city/region the candidate is based in, or ""), current_role,
  skills (comma-separated string), experience_years (number), education, summary (1-2 sentences)
- employment_history: array of objects {{"title": "", "company": "", "start": "", "end": ""}},
  most recent first. Use "" for any part you cannot determine. Use "Present" for an ongoing role's end date.
- certifications: array of strings (professional certifications/licenses only, not degrees)

Rules:
- If a field cannot be found, use "" or 0, or an empty array for employment_history/certifications
- Distinguish what the CV explicitly states from what you reasonably derive (e.g. computing
  experience_years from employment date ranges) — but only report values you can support either way.
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
        try:
            with pdfplumber.open(file_obj) as pdf:
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n"
        except Exception:
            return ""
        return text.strip()

    if filename_lower.endswith(".docx"):
        try:
            document = docx.Document(file_obj)
        except Exception:
            return ""
        return "\n".join(p.text for p in document.paragraphs if p.text.strip()).strip()

    if filename_lower.endswith(".txt"):
        return content.decode("utf-8", errors="ignore").strip()

    return ""


def is_supported_filename(filename: str) -> bool:
    return filename.lower().endswith((".pdf", ".docx", ".txt"))


async def parse_cv(cv_text: str, filename: str, org_id: str = "") -> dict:
    if not cv_text or len(cv_text.strip()) < 50:
        return _blank(filename, "Could not extract text from this CV. It may be empty, image-only, or corrupted.")

    prompt = PARSE_PROMPT.format(cv_text=cv_text[:6000])
    data = await chat_json(
        [{"role": "user", "content": prompt}],
        temperature=0.1,
        max_tokens=900,
        org_id=org_id,
    )
    if data is None:
        return _blank(filename, "AI analysis temporarily failed (invalid response). Please retry.")

    data.setdefault("employment_history", [])
    data.setdefault("certifications", [])
    data["filename"] = filename
    data["raw_text"] = cv_text[:8000]
    data["parse_error"] = None
    return data


async def process_cv_bytes(content: bytes, filename: str, org_id: str = "") -> dict:
    if not is_supported_filename(filename):
        return _blank(filename, "Unsupported file type. Upload PDF, DOCX, or TXT.")
    raw_text = extract_text_from_bytes(content, filename)
    return await parse_cv(raw_text, filename, org_id)


def _blank(filename: str, error: str = "") -> dict:
    return {
        "name": "Unknown",
        "email": "",
        "phone": "",
        "location": "",
        "current_role": "",
        "skills": "",
        "experience_years": 0,
        "education": "",
        "summary": "",
        "employment_history": [],
        "certifications": [],
        "filename": filename,
        "raw_text": "",
        "parse_error": error,
    }
