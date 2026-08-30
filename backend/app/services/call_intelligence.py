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


CALL_EXTRACT_PROMPT = """
You are an expert recruitment assistant.
Read the call transcript below and extract the following information.
Return your answer as a valid JSON object — nothing else, no explanation.

Fields to extract:
- salary_expectation (short text, e.g. "£45,000" or "AED 20,000/month"),
  notice_period (short text, e.g. "1 month"),
  availability (short text, e.g. "Immediately" or "From 1 Sept"),
  flight_risk_notes (1-2 sentences on motivation, competing offers, or hesitation),
  summary (1-2 sentence summary of the call)

Rules:
- If a field cannot be found, use ""
- Do not invent information
- Return only valid JSON

Call transcript:
{transcript}
"""


def transcribe_audio(content: bytes, filename: str) -> str:
    response = get_client().audio.transcriptions.create(
        model="whisper-1",
        file=(filename, content),
    )
    return (response.text or "").strip()


def extract_call_data(transcript: str) -> dict:
    prompt = CALL_EXTRACT_PROMPT.format(transcript=transcript[:6000])
    response = get_client().chat.completions.create(
        model=settings.llm_model,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.1,
        max_tokens=500,
    )
    raw = re.sub(r"```json|```", "", response.choices[0].message.content.strip())
    return json.loads(raw)


def process_call_recording(content: bytes, filename: str) -> dict:
    try:
        transcript = transcribe_audio(content, filename)
    except Exception as exc:
        return _blank(str(exc))

    if not transcript or len(transcript.strip()) < 10:
        return _blank("Could not transcribe this recording.")

    try:
        data = extract_call_data(transcript)
        data["transcript"] = transcript
        data["parse_error"] = None
        return data
    except Exception as exc:
        return _blank(str(exc), transcript=transcript)


def _blank(error: str, transcript: str = "") -> dict:
    return {
        "salary_expectation": "",
        "notice_period": "",
        "availability": "",
        "flight_risk_notes": "",
        "summary": "",
        "transcript": transcript,
        "parse_error": error,
    }
