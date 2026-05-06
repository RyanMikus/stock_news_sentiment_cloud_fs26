import json
from datetime import datetime, timezone
from typing import Any

try:
    import config  # noqa: F401
except ImportError:
    pass

from google.cloud import datastore


ARTICLE_KIND = "Article"

_EXCLUDE_FROM_INDEXES = (
    "full_text",
    "entities_json",
    "sentence_sentiments_json",
    "extraction_error_reason",
    "sentiment_error_reason",
    "entity_error_reason",
    "publisher_url",
    "google_news_url",
)


def _get_client() -> datastore.Client:
    return datastore.Client()


def _article_to_ds_entity(
    client: datastore.Client,
    article: dict[str, Any],
) -> datastore.Entity:
    entities_list = article.get("entities") or []
    sentence_sentiments = article.get("sentence_sentiments") or []

    entity_names = list({e["name"] for e in entities_list if e.get("name")})
    entity_types = list({e["type"] for e in entities_list if e.get("type")})

    publisher_url = article.get("publisher_url") or ""
    google_news_url = article.get("google_news_url") or article.get("url") or ""
    url = publisher_url or google_news_url

    ds_entity = datastore.Entity(
        client.key(ARTICLE_KIND),
        exclude_from_indexes=_EXCLUDE_FROM_INDEXES,
    )

    ds_entity.update(
        {
            "url": url,
            "publisher_url": publisher_url,
            "google_news_url": google_news_url,
            "title": article.get("title") or "",
            "source": article.get("source") or "",
            "query": article.get("query") or "",
            "news_region": article.get("news_region") or "",
            "published_at": article.get("published_at"),
            "full_text": article.get("full_text") or "",
            "text_extraction_status": article.get("text_extraction_status") or "",
            "extraction_method": article.get("extraction_method") or "",
            "extraction_error_reason": article.get("extraction_error_reason") or "",
            "sentiment_score": article.get("sentiment_score"),
            "sentiment_magnitude": article.get("sentiment_magnitude"),
            "weighted_sentiment": article.get("weighted_sentiment"),
            "sentiment_label": article.get("sentiment_label") or "unknown",
            "sentiment_analysis_status": article.get("sentiment_analysis_status") or "",
            "sentiment_error_reason": article.get("sentiment_error_reason") or "",
            "entity_extraction_status": article.get("entity_extraction_status") or "",
            "entity_error_reason": article.get("entity_error_reason") or "",
            "entity_names": entity_names,
            "entity_types": entity_types,
            "entities_json": json.dumps(entities_list),
            "sentence_sentiments_json": json.dumps(sentence_sentiments),
            "saved_at": datetime.now(timezone.utc),
        }
    )

    return ds_entity


def _ds_entity_to_article(ds_entity: datastore.Entity) -> dict[str, Any]:
    try:
        entities = json.loads(ds_entity.get("entities_json") or "[]")
    except (json.JSONDecodeError, TypeError):
        entities = []

    try:
        sentence_sentiments = json.loads(
            ds_entity.get("sentence_sentiments_json") or "[]"
        )
    except (json.JSONDecodeError, TypeError):
        sentence_sentiments = []

    return {
        "datastore_id": ds_entity.key.id,
        "url": ds_entity.get("url") or "",
        "publisher_url": ds_entity.get("publisher_url") or "",
        "google_news_url": ds_entity.get("google_news_url") or "",
        "title": ds_entity.get("title") or "",
        "source": ds_entity.get("source") or "",
        "query": ds_entity.get("query") or "",
        "news_region": ds_entity.get("news_region") or "",
        "published_at": ds_entity.get("published_at"),
        "full_text": ds_entity.get("full_text") or "",
        "text_extraction_status": ds_entity.get("text_extraction_status") or "",
        "extraction_method": ds_entity.get("extraction_method") or "",
        "extraction_error_reason": ds_entity.get("extraction_error_reason") or "",
        "sentiment_score": ds_entity.get("sentiment_score"),
        "sentiment_magnitude": ds_entity.get("sentiment_magnitude"),
        "weighted_sentiment": ds_entity.get("weighted_sentiment"),
        "sentiment_label": ds_entity.get("sentiment_label") or "unknown",
        "sentiment_analysis_status": ds_entity.get("sentiment_analysis_status") or "",
        "sentiment_error_reason": ds_entity.get("sentiment_error_reason") or "",
        "entity_extraction_status": ds_entity.get("entity_extraction_status") or "",
        "entity_error_reason": ds_entity.get("entity_error_reason") or "",
        "entity_names": list(ds_entity.get("entity_names") or []),
        "entity_types": list(ds_entity.get("entity_types") or []),
        "entities": entities,
        "sentence_sentiments": sentence_sentiments,
        "saved_at": ds_entity.get("saved_at"),
    }


def _url_already_exists(client: datastore.Client, url: str) -> bool:
    if not url:
        return False

    query = client.query(kind=ARTICLE_KIND)
    query.add_filter("url", "=", url)
    query.keys_only()

    return any(True for _ in query.fetch(limit=1))


def save_article(article: dict[str, Any]) -> str:
    """
    Save one analyzed article to Datastore.

    Returns "saved", "skipped" (URL already exists), or "error: <reason>".
    Uses publisher_url as the canonical URL for deduplication.
    """
    url = (
        article.get("publisher_url")
        or article.get("google_news_url")
        or article.get("url")
        or ""
    )

    try:
        client = _get_client()

        if _url_already_exists(client, url):
            return "skipped"

        ds_entity = _article_to_ds_entity(client, article)
        client.put(ds_entity)
        return "saved"

    except Exception as error:
        return f"error: {type(error).__name__}: {error}"


def _get_existing_urls(client: datastore.Client, urls: list[str]) -> set[str]:
    existing: set[str] = set()

    for i in range(0, len(urls), 30):
        chunk = [u for u in urls[i:i + 30] if u]
        if not chunk:
            continue
        try:
            query = client.query(kind=ARTICLE_KIND)
            query.add_filter("url", "IN", chunk)
            query.projection = ["url"]
            for entity in query.fetch():
                url = entity.get("url")
                if url:
                    existing.add(url)
        except Exception:
            for url in chunk:
                if _url_already_exists(client, url):
                    existing.add(url)

    return existing


def save_articles(articles: list[dict[str, Any]]) -> dict[str, int]:
    counts = {"saved": 0, "skipped": 0, "error": 0}

    if not articles:
        return counts

    try:
        client = _get_client()

        urls = [
            a.get("publisher_url") or a.get("google_news_url") or a.get("url") or ""
            for a in articles
        ]

        existing_urls = _get_existing_urls(client, [u for u in urls if u])

        to_put = []
        for article, url in zip(articles, urls):
            if not url or url in existing_urls:
                counts["skipped"] += 1
                continue
            try:
                to_put.append(_article_to_ds_entity(client, article))
            except Exception:
                counts["error"] += 1

        if to_put:
            client.put_multi(to_put)
            counts["saved"] = len(to_put)

    except Exception:
        counts = {"saved": 0, "skipped": 0, "error": 0}
        for article in articles:
            result = save_article(article)
            if result == "saved":
                counts["saved"] += 1
            elif result == "skipped":
                counts["skipped"] += 1
            else:
                counts["error"] += 1

    return counts


def query_articles(
    company: str | None = None,
    min_sentiment: float | None = None,
    max_sentiment: float | None = None,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
    limit: int = 500,
) -> list[dict[str, Any]]:
    """
    Fetch stored articles from Datastore with optional filters.

    One server-side filter is applied (min_sentiment if provided, otherwise order
    by saved_at). All remaining filters are applied in Python to avoid composite
    index requirements.
    """
    client = _get_client()
    query = client.query(kind=ARTICLE_KIND)

    if min_sentiment is not None:
        query.add_filter("sentiment_score", ">=", float(min_sentiment))
        query.order = ["sentiment_score"]
    else:
        query.order = ["-saved_at"]

    raw_results = list(query.fetch(limit=limit))
    articles = [_ds_entity_to_article(entity) for entity in raw_results]

    if max_sentiment is not None:
        articles = [
            a for a in articles
            if a.get("sentiment_score") is None
            or a["sentiment_score"] <= float(max_sentiment)
        ]

    if company:
        needle = company.strip().lower()
        articles = [
            a for a in articles
            if any(needle in name.lower() for name in (a.get("entity_names") or []))
        ]

    if start_date:
        articles = [
            a for a in articles
            if a.get("published_at") is not None
            and _as_utc(a["published_at"]) >= _as_utc(start_date)
        ]

    if end_date:
        articles = [
            a for a in articles
            if a.get("published_at") is not None
            and _as_utc(a["published_at"]) <= _as_utc(end_date)
        ]

    if min_sentiment is not None:
        articles.sort(key=lambda a: a.get("saved_at") or datetime.min, reverse=True)

    return articles


def get_article_by_url(url: str) -> dict[str, Any] | None:
    """
    Returns a stored article dict if the URL exists in Datastore, None otherwise.

    Silently returns None on any error so a Datastore failure never blocks
    the normal search and extraction flow.
    """
    if not url:
        return None

    try:
        client = _get_client()
        query = client.query(kind=ARTICLE_KIND)
        query.add_filter("url", "=", url)
        results = list(query.fetch(limit=1))

        if results:
            return _ds_entity_to_article(results[0])

        return None

    except Exception:
        return None


def _as_utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt
