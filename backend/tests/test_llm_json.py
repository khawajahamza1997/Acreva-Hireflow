from app.services.llm_client import _strip_and_parse


def test_parses_clean_json():
    assert _strip_and_parse('{"a": 1}') == {"a": 1}


def test_strips_markdown_fences():
    raw = '```json\n{"a": 1, "b": [1, 2]}\n```'
    assert _strip_and_parse(raw) == {"a": 1, "b": [1, 2]}


def test_strips_bare_fences_without_language_tag():
    raw = '```\n{"ok": true}\n```'
    assert _strip_and_parse(raw) == {"ok": True}


def test_malformed_json_returns_none():
    assert _strip_and_parse("this is not json at all") is None
    assert _strip_and_parse('{"a": 1,}') is None  # trailing comma, invalid JSON
    assert _strip_and_parse("") is None
    assert _strip_and_parse(None) is None
