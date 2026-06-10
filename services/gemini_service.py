from __future__ import annotations

import json
from typing import Any

try:
    import config  # noqa: F401
except ImportError:
    pass

from google import genai
from google.genai import types


_PROJECT_ID = "sentiment-web-app-495216"
_LOCATION = "us-central1"
_MODEL = "gemini-2.5-flash"
_MAX_ARTICLES_FOR_SUMMARY = 10
_MAX_ARTICLE_CHARS = 1500
_MAX_ENTITY_NAMES = 30


def _get_client() -> genai.Client:
    return genai.Client(
        vertexai=True,
        project=_PROJECT_ID,
        location=_LOCATION,
    )


def _parse_json_response(text: str) -> Any:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        lines = cleaned.split("\n")
        end = -1 if lines[-1].strip() == "```" else len(lines)
        cleaned = "\n".join(lines[1:end])
    return json.loads(cleaned)


def _summarize_articles_text(articles: list[dict[str, Any]]) -> str:
    """Plain-text trader summary — no JSON mode, no parsing, never breaks."""
    usable = [
        a for a in articles
        if a.get("text_extraction_status") == "success" and a.get("title")
    ][:_MAX_ARTICLES_FOR_SUMMARY]

    if not usable:
        return "No articles available."

    articles_text = ""
    for i, a in enumerate(usable, 1):
        title = a.get("title") or ""
        text = (a.get("full_text") or "")[:_MAX_ARTICLE_CHARS]
        articles_text += f"\n--- Article {i} ---\n{title}\n{text}\n"

    prompt = (
        f"You are given {len(usable)} financial news articles below.\n\n"
        f"{articles_text}\n\n"
        "Write a trader-focused summary of what these articles collectively report. "
        "Focus on catalysts, earnings, guidance, key numbers, macro events, and risks. "
        "Structure it clearly — use short sections or bullet points where it helps readability. "
        "Do not add general knowledge not found in the articles. "
        "Never wrap numbers, tickers, or values in backticks."
    )

    try:
        client = _get_client()
        response = client.models.generate_content(model=_MODEL, contents=prompt)
        return response.text.strip()
    except Exception as e:
        return f"Analysis unavailable: {type(e).__name__}: {e}"


def _extract_companies_from_articles(articles: list[dict[str, Any]]) -> dict[str, str]:
    """
    Ask Gemini to identify tradeable companies/indices from article titles only.
    Returns a flat name→ticker dict via JSON mode — small and simple, very reliable.
    """
    titles = [a.get("title") or "" for a in articles if a.get("title")][:_MAX_ARTICLES_FOR_SUMMARY]

    if not titles:
        return {}

    titles_text = "\n".join(f"- {t}" for t in titles)
    prompt = (
        "From these financial news headlines, identify every publicly traded company, "
        "stock, ETF, or major stock market index mentioned.\n\n"
        f"{titles_text}\n\n"
        "Return ONLY a raw JSON object mapping display name to ticker symbol. "
        "Only include entities you are highly confident about. "
        "Skip people, countries, cities, and non-tradeable terms.\n"
        'Example: {"NVIDIA": "NVDA", "UBS": "UBS", "S&P 500": "^GSPC"}'
    )

    try:
        client = _get_client()
        response = client.models.generate_content(
            model=_MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(response_mime_type="application/json"),
        )
        result = _parse_json_response(response.text)
        if isinstance(result, dict):
            return {str(k).strip(): str(v).strip().upper() for k, v in result.items()}
        return {}
    except Exception:
        return {}


def analyze_articles_with_gemini(
    articles: list[dict[str, Any]],
) -> dict[str, Any]:
    """
    Two separate Gemini calls: plain-text summary + simple JSON ticker dict.
    Keeping them apart prevents long prose from ever breaking JSON parsing.

    Returns {"summary": str, "resolver": {display_name: ticker}}.
    """
    summary = _summarize_articles_text(articles)
    resolver = _extract_companies_from_articles(articles)
    return {"summary": summary, "resolver": resolver}


def resolve_tickers_from_entities(entity_names: list[str]) -> dict[str, str]:
    """
    Ask Gemini to identify which entity names are publicly traded stocks or indices
    and return their ticker symbols. Returns {entity_name: ticker}.
    """
    if not entity_names:
        return {}

    names_list = "\n".join(f"- {name}" for name in entity_names[:_MAX_ENTITY_NAMES])
    prompt = (
        "You are a financial data assistant. Given these entity names from financial news, "
        "identify which are publicly traded companies or major stock market indices.\n\n"
        "Return ONLY a raw JSON object (no markdown, no explanation).\n"
        'Example: {"Apple": "AAPL", "NVIDIA": "NVDA", "S&P 500": "^GSPC"}\n\n'
        "Only include entities you are highly confident about. "
        "Skip people, countries, cities, and general terms like CEO, AI, or GDP.\n\n"
        f"Entities:\n{names_list}"
    )

    try:
        client = _get_client()
        response = client.models.generate_content(
            model=_MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
            ),
        )
        result = _parse_json_response(response.text)
        if isinstance(result, dict):
            return {str(k): str(v).strip().upper() for k, v in result.items()}
        return {}
    except Exception:
        return {}


def suggest_related_stocks(
    ticker: str,
    display_name: str,
    articles: list[dict[str, Any]],
) -> list[dict[str, str]]:
    """Suggest 4 related publicly traded stocks based on article context."""
    titles = [a.get("title") for a in articles if a.get("title")][:5]

    if not titles:
        return []

    titles_text = "\n".join(f"- {t}" for t in titles)
    prompt = (
        f"Based on these recent news headlines about {display_name} ({ticker}), "
        "suggest 4 related publicly traded stocks.\n\n"
        f"Headlines:\n{titles_text}\n\n"
        "Consider: direct competitors, suppliers, companies in the same sector.\n\n"
        "Return ONLY a raw JSON array (no markdown, no explanation).\n"
        '[{"ticker": "SYMBOL", "name": "Company Name", '
        '"relation_type": "competitor", "reason": "One sentence"}]'
    )

    try:
        client = _get_client()
        response = client.models.generate_content(
            model=_MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
            ),
        )
        result = _parse_json_response(response.text)
        if isinstance(result, list):
            return [
                {
                    "ticker": str(r.get("ticker", "")).strip().upper(),
                    "name": str(r.get("name", "")),
                    "relation_type": str(r.get("relation_type", "")),
                    "reason": str(r.get("reason", "")),
                }
                for r in result
                if r.get("ticker")
            ]
        return []
    except Exception:
        return []


def collect_entity_names_from_articles(
    articles: list[dict[str, Any]],
    min_salience: float = 0.03,
) -> list[str]:
    """Collect unique ORGANIZATION/OTHER entity names from analyzed articles."""
    seen: set[str] = set()
    names: list[str] = []

    for article in articles:
        if article.get("entity_extraction_status") != "success":
            continue
        for entity in article.get("entities") or []:
            if entity.get("type") not in {"ORGANIZATION", "OTHER"}:
                continue
            if (entity.get("salience") or 0.0) < min_salience:
                continue
            name = (entity.get("name") or "").strip()
            if name and name not in seen:
                seen.add(name)
                names.append(name)

    return names
