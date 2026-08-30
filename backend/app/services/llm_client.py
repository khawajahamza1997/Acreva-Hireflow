import json
import re
from openai import AsyncOpenAI
from app.config import settings
from app.services.usage import record_usage

_client: AsyncOpenAI | None = None


def get_client() -> AsyncOpenAI:
    """Single seam for the AI provider. Swapping providers later means changing this
    function (and the call shape below), not every service that needs a chat completion."""
    global _client
    if _client is None:
        if not settings.openai_api_key:
            raise RuntimeError("OPENAI_API_KEY is not configured.")
        _client = AsyncOpenAI(api_key=settings.openai_api_key)
    return _client


def _strip_and_parse(raw: str) -> dict | None:
    cleaned = re.sub(r"```json|```", "", raw or "").strip()
    try:
        return json.loads(cleaned)
    except (json.JSONDecodeError, TypeError):
        return None


async def _complete(messages: list[dict], *, temperature: float, max_tokens: int) -> str:
    response = await get_client().chat.completions.create(
        model=settings.llm_model,
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens,
    )
    return response.choices[0].message.content or ""


async def chat_json(
    messages: list[dict],
    *,
    temperature: float = 0.2,
    max_tokens: int = 900,
    org_id: str = "",
) -> dict | None:
    """Call the model expecting a JSON object back. Never trusts the response as-is:
    on malformed JSON it retries once with an explicit repair instruction before
    giving up and returning None, so callers can mark the operation Failed rather
    than store garbage."""
    raw = await _complete(messages, temperature=temperature, max_tokens=max_tokens)
    record_usage(org_id, "ai_call")

    parsed = _strip_and_parse(raw)
    if parsed is not None:
        return parsed

    repair_messages = messages + [
        {"role": "assistant", "content": raw},
        {
            "role": "user",
            "content": "Your previous response was not valid JSON. Return ONLY a valid JSON object, no markdown fences, no explanation.",
        },
    ]
    repaired_raw = await _complete(repair_messages, temperature=0.0, max_tokens=max_tokens)
    record_usage(org_id, "ai_call")
    return _strip_and_parse(repaired_raw)
