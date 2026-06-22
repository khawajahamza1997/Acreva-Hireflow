# ============================================================
# cv_parser.py
# ============================================================
# Purpose: Read a CV file (PDF or Word) and extract structured
# candidate information using OpenAI.
#
# Two stages:
#   Stage 1 — extract_text()   : Get raw text from the file
#   Stage 2 — parse_cv()       : Send text to OpenAI, get back
#                                 a clean structured dictionary
# ============================================================

import pdfplumber
import docx
import json
import re
from openai import OpenAI
from dotenv import load_dotenv
import os

# Load environment variables from .env file
load_dotenv()

# Initialise the OpenAI client once (reused across all calls)
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


# ------------------------------------------------------------
# STAGE 1: Extract raw text from the uploaded file
# ------------------------------------------------------------

def extract_text_from_pdf(file) -> str:
    """
    Reads a PDF file and returns all its text as a single string.
    'file' is a file-like object (from Streamlit's file uploader).
    """
    text = ""
    with pdfplumber.open(file) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:  # Some pages may be empty or image-only
                text += page_text + "\n"
    return text.strip()


def extract_text_from_docx(file) -> str:
    """
    Reads a Word (.docx) file and returns all its text as a single string.
    """
    document = docx.Document(file)
    paragraphs = [para.text for para in document.paragraphs if para.text.strip()]
    return "\n".join(paragraphs).strip()


def extract_text(file, filename: str) -> str:
    """
    Detects file type by extension and calls the right extractor.
    Returns raw text string from the CV.

    Supported formats: .pdf, .docx, .txt
    """
    filename_lower = filename.lower()

    if filename_lower.endswith(".pdf"):
        return extract_text_from_pdf(file)

    elif filename_lower.endswith(".docx"):
        return extract_text_from_docx(file)

    elif filename_lower.endswith(".txt"):
        # Plain text — just read it directly
        return file.read().decode("utf-8", errors="ignore").strip()

    else:
        # Unsupported format
        return ""


# ------------------------------------------------------------
# STAGE 2: Parse structured fields from raw CV text using OpenAI
# ------------------------------------------------------------

# This is the prompt we send to GPT-4.
# It tells the model exactly what fields to extract and in what format.
PARSE_PROMPT = """
You are an expert recruitment assistant.

Read the CV text below and extract the following information.
Return your answer as a valid JSON object — nothing else, no explanation.

Fields to extract:
- name         : Full name of the candidate (string)
- email        : Email address (string, or "" if not found)
- phone        : Phone number (string, or "" if not found)
- current_role : Most recent job title or current role (string)
- skills       : List of key skills as a comma-separated string
- experience_years : Estimated total years of professional experience (number, or 0 if unclear)
- education    : Highest qualification and institution (string, or "" if not found)
- summary      : 1-2 sentence summary of the candidate's professional background

Rules:
- If a field cannot be found, use an empty string "" or 0 for numbers
- Do not guess or invent information
- Return only valid JSON, no markdown formatting

CV Text:
{cv_text}
"""


def parse_cv(cv_text: str, filename: str) -> dict:
    """
    Sends raw CV text to OpenAI and returns a structured dictionary
    with all the candidate fields we need.

    Returns a dictionary like:
    {
        "name": "John Smith",
        "email": "john@example.com",
        "phone": "+44 7700 123456",
        "current_role": "Sales Executive",
        "skills": "CRM, cold calling, HubSpot, B2B sales",
        "experience_years": 4,
        "education": "BSc Business, University of Manchester",
        "summary": "Experienced B2B sales professional...",
        "filename": "john_smith_cv.pdf",
        "raw_text": "..."   <- kept for use in scoring later
    }
    """

    # Safety check — if we got no text, return a blank record
    if not cv_text or len(cv_text.strip()) < 50:
        return _blank_candidate(filename, error="Could not extract text from this CV.")

    try:
        # Build the prompt with the actual CV text inserted
        prompt = PARSE_PROMPT.format(cv_text=cv_text[:4000])  # Limit to 4000 chars to control token cost

        # Call GPT-4o-mini (fast + cheap for extraction tasks)
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "user", "content": prompt}
            ],
            temperature=0.1,  # Low temperature = more consistent, factual output
            max_tokens=600
        )

        # Get the raw text response
        raw_response = response.choices[0].message.content.strip()

        # Clean up any markdown code fences if GPT wraps in ```json ... ```
        raw_response = re.sub(r"```json|```", "", raw_response).strip()

        # Parse the JSON string into a Python dictionary
        candidate_data = json.loads(raw_response)

        # Add the filename and raw text for later use in scoring
        candidate_data["filename"] = filename
        candidate_data["raw_text"] = cv_text[:8000]  # Store up to 8000 chars for scoring

        return candidate_data

    except json.JSONDecodeError:
        # GPT returned something we couldn't parse as JSON
        return _blank_candidate(filename, error="AI response could not be parsed.")

    except Exception as e:
        # Any other error (API timeout, quota exceeded, etc.)
        return _blank_candidate(filename, error=str(e))


def _blank_candidate(filename: str, error: str = "") -> dict:
    """
    Returns a blank candidate record when parsing fails.
    This prevents the whole app from crashing on a bad CV.
    """
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
        "parse_error": error
    }


# ------------------------------------------------------------
# MAIN FUNCTION: Process one uploaded file end-to-end
# ------------------------------------------------------------

def parse_local_cv_file(filepath: str) -> dict:
    """
    Parses a CV file from disk (used for sample data and client demos).
    Supports .txt, .pdf, and .docx.
    """
    filename = os.path.basename(filepath)
    filename_lower = filename.lower()

    if filename_lower.endswith(".txt"):
        with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
            raw_text = f.read().strip()
    elif filename_lower.endswith(".pdf"):
        with open(filepath, "rb") as f:
            raw_text = extract_text_from_pdf(f)
    elif filename_lower.endswith(".docx"):
        with open(filepath, "rb") as f:
            raw_text = extract_text_from_docx(f)
    else:
        return _blank_candidate(filename, error="Unsupported file type.")

    return parse_cv(raw_text, filename)


def process_uploaded_cv(uploaded_file) -> dict:
    """
    The single function called from app.py.
    Takes a Streamlit UploadedFile object, extracts text, parses it,
    and returns a complete candidate dictionary.

    Usage in app.py:
        candidate = process_uploaded_cv(uploaded_file)
    """
    filename = uploaded_file.name

    # Stage 1: Get raw text
    raw_text = extract_text(uploaded_file, filename)

    # Stage 2: Parse with OpenAI
    candidate = parse_cv(raw_text, filename)

    return candidate
