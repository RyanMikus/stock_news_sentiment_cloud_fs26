from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict, dataclass
from typing import Any

try:
    import config  # noqa: F401
except ImportError:
    # Allows deployment environments where credentials are provided by App Engine
    # or by already-set environment variables.
    pass

from google.cloud import language_v1


MAX_TEXT_BYTES = 95_000


@dataclass
class ExtractedEntity:
    name: str
    type: str
    salience: float
    wikipedia_url: str | None
    metadata: dict[str, str]
    mentions: list[dict[str, Any]]


@dataclass
class EntityExtractionResult:
    entities: list[dict[str, Any]]
    entity_extraction_status: str
    entity_error_reason: str | None


def _get_language_client() -> language_v1.LanguageServiceClient:
    return language_v1.LanguageServiceClient()


def _truncate_text_for_api(text: str, max_bytes: int = MAX_TEXT_BYTES) -> str:
    encoded_text = text.encode("utf-8")

    if len(encoded_text) <= max_bytes:
        return text

    truncated = encoded_text[:max_bytes]
    return truncated.decode("utf-8", errors="ignore")


def _entity_type_name(entity_type: Any) -> str:
    try:
        return language_v1.Entity.Type(entity_type).name
    except Exception:
        return str(entity_type)


def _mention_type_name(mention_type: Any) -> str:
    try:
        return language_v1.EntityMention.Type(mention_type).name
    except Exception:
        return str(mention_type)


def _extract_entity_metadata(entity: language_v1.Entity) -> dict[str, str]:
    return dict(entity.metadata or {})


def _extract_entity_mentions(entity: language_v1.Entity) -> list[dict[str, Any]]:
    mentions = []

    for mention in entity.mentions:
        mentions.append(
            {
                "text": mention.text.content,
                "type": _mention_type_name(mention.type_),
            }
        )

    return mentions


def extract_entities(text: str) -> dict[str, Any]:
    """
    Extract named entities using Google Cloud Natural Language API.

    Returns plain dictionaries so the result can be displayed in Streamlit,
    exported as CSV/JSON later, and stored in Datastore in Phase 5.
    """
    clean_text = (text or "").strip()

    if not clean_text:
        result = EntityExtractionResult(
            entities=[],
            entity_extraction_status="skipped",
            entity_error_reason="No article text available for entity extraction.",
        )
        return asdict(result)

    try:
        client = _get_language_client()

        document = language_v1.Document(
            content=_truncate_text_for_api(clean_text),
            type_=language_v1.Document.Type.PLAIN_TEXT,
        )

        response = client.analyze_entities(request={"document": document})

        entities = []

        for entity in response.entities:
            metadata = _extract_entity_metadata(entity)

            entities.append(
                asdict(
                    ExtractedEntity(
                        name=entity.name,
                        type=_entity_type_name(entity.type_),
                        salience=float(entity.salience),
                        wikipedia_url=metadata.get("wikipedia_url"),
                        metadata=metadata,
                        mentions=_extract_entity_mentions(entity),
                    )
                )
            )

        result = EntityExtractionResult(
            entities=entities,
            entity_extraction_status="success",
            entity_error_reason=None,
        )

        return asdict(result)

    except Exception as error:
        result = EntityExtractionResult(
            entities=[],
            entity_extraction_status="failed",
            entity_error_reason=f"{type(error).__name__}: {error}",
        )
        return asdict(result)


def extract_article_entities(article: dict[str, Any]) -> dict[str, Any]:
    """
    Enrich one article dictionary with extracted entities.

    Only articles selected for sentiment/entity analysis and successfully extracted
    should be sent to the Natural Language API.
    """
    if article.get("entity_extraction_status") == "success":
        return article

    full_text = article.get("full_text") or article.get("article_text") or ""

    if not article.get("use_for_sentiment"):
        return {
            **article,
            "entities": [],
            "entity_extraction_status": "skipped",
            "entity_error_reason": "Article was not selected for entity extraction.",
        }

    if article.get("text_extraction_status") != "success":
        return {
            **article,
            "entities": [],
            "entity_extraction_status": "skipped",
            "entity_error_reason": "Article text extraction did not succeed.",
        }

    title = (article.get("title") or "").strip()
    if title and title.lower() not in full_text[:500].lower():
        full_text = f"{title}\n\n{full_text}"

    entity_result = extract_entities(full_text)

    return {
        **article,
        **entity_result,
    }


def extract_articles_entities(articles: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not articles:
        return articles

    results: list[dict | None] = [None] * len(articles)

    with ThreadPoolExecutor(max_workers=min(len(articles), 10)) as executor:
        future_to_index = {
            executor.submit(extract_article_entities, article): i
            for i, article in enumerate(articles)
        }

        for future in as_completed(future_to_index):
            i = future_to_index[future]
            try:
                results[i] = future.result()
            except Exception:
                results[i] = articles[i]

    return [r for r in results if r is not None]