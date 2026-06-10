from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any

try:
    import config  # noqa: F401
except ImportError:
    pass

from google.cloud import language_v1


MAX_TEXT_BYTES = 95_000
MIN_WORD_COUNT = 20


def _get_language_client() -> language_v1.LanguageServiceClient:
    return language_v1.LanguageServiceClient()


def _truncate_text_for_api(text: str, max_bytes: int = MAX_TEXT_BYTES) -> str:
    encoded = text.encode("utf-8")
    if len(encoded) <= max_bytes:
        return text
    return encoded[:max_bytes].decode("utf-8", errors="ignore")


def classify_text(text: str) -> dict[str, Any]:
    clean_text = (text or "").strip()

    if len(clean_text.split()) < MIN_WORD_COUNT:
        return {
            "categories": [],
            "classification_status": "skipped",
            "classification_error_reason": "Text too short for classification.",
        }

    try:
        client = _get_language_client()
        document = language_v1.Document(
            content=_truncate_text_for_api(clean_text),
            type_=language_v1.Document.Type.PLAIN_TEXT,
        )
        response = client.classify_text(request={"document": document})
        categories = [
            {"name": cat.name, "confidence": round(float(cat.confidence), 3)}
            for cat in response.categories
        ]
        return {
            "categories": categories,
            "classification_status": "success",
            "classification_error_reason": None,
        }
    except Exception as error:
        return {
            "categories": [],
            "classification_status": "failed",
            "classification_error_reason": f"{type(error).__name__}: {error}",
        }


def classify_article(article: dict[str, Any]) -> dict[str, Any]:
    if article.get("classification_status") == "success":
        return article

    if not article.get("use_for_sentiment"):
        return {
            **article,
            "categories": [],
            "classification_status": "skipped",
            "classification_error_reason": "Article not selected for analysis.",
        }

    if article.get("text_extraction_status") != "success":
        return {
            **article,
            "categories": [],
            "classification_status": "skipped",
            "classification_error_reason": "Article text extraction did not succeed.",
        }

    result = classify_text(article.get("full_text") or "")
    return {**article, **result}


def classify_articles(articles: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not articles:
        return articles

    results: list[dict | None] = [None] * len(articles)

    with ThreadPoolExecutor(max_workers=min(len(articles), 10)) as executor:
        future_to_index = {
            executor.submit(classify_article, article): i
            for i, article in enumerate(articles)
        }
        for future in as_completed(future_to_index):
            i = future_to_index[future]
            try:
                results[i] = future.result()
            except Exception:
                results[i] = articles[i]

    return [r for r in results if r is not None]
