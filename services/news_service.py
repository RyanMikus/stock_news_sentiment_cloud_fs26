from dataclasses import asdict, dataclass
from datetime import datetime
from email.utils import parsedate_to_datetime
from typing import Any

from gnews import GNews


@dataclass
class NewsArticle:
    title: str
    description: str
    url: str
    published_at: datetime | None
    source: str
    query: str
    news_region: str


def _parse_published_at(value: Any) -> datetime | None:
    if not value:
        return None

    if isinstance(value, datetime):
        return value

    if isinstance(value, str):
        try:
            return parsedate_to_datetime(value)
        except (TypeError, ValueError):
            return None

    return None


def _extract_source(item: dict[str, Any]) -> str:
    publisher = item.get("publisher")

    if isinstance(publisher, dict):
        return publisher.get("title") or publisher.get("href") or ""

    if isinstance(publisher, str):
        return publisher

    return item.get("source") or ""


def fetch_company_news(
    query: str,
    max_results: int = 10,
    period: str = "7d",
    language: str = "en",
    news_region: str = "US",
    sort_by: str = "Google relevance",
) -> list[dict[str, Any]]:
    """
    Fetch recent Google News articles for a company name, ticker, or keyword.

    Supported search examples:
    - Apple
    - AAPL
    - NVIDIA
    - NVDA
    - Tesla
    - TSLA

    news_region is passed to gnews as the country parameter.
    It represents the Google News regional edition, not necessarily
    the publisher's physical country.

    Sorting:
    - "Google relevance": keeps the order returned by Google News / gnews
    - "Newest first": sorts locally by publication date
    """

    clean_query = query.strip()

    if not clean_query:
        raise ValueError("Search query must not be empty.")

    max_results = max(1, min(max_results, 50))

    google_news = GNews(
        language=language,
        country=news_region,
        period=period,
        max_results=max_results,
    )

    raw_results = google_news.get_news(clean_query) or []

    articles: list[dict[str, Any]] = []

    for item in raw_results:
        article = NewsArticle(
            title=item.get("title", "").strip(),
            description=item.get("description", "").strip(),
            url=item.get("url", "").strip(),
            published_at=_parse_published_at(item.get("published date")),
            source=_extract_source(item),
            query=clean_query,
            news_region=news_region,
        )

        if article.title and article.url:
            articles.append(asdict(article))

    if sort_by == "Newest first":
        articles.sort(
            key=lambda article: article["published_at"] or datetime.min,
            reverse=True,
        )

    return articles