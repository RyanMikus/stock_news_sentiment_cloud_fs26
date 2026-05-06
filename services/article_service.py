from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from typing import Optional
import re

from googlenewsdecoder import gnewsdecoder
from newspaper import Article, Config


MIN_USABLE_TEXT_LENGTH = 1000


BLOCKED_TEXT_PATTERNS = [
    "enable javascript",
    "please enable cookies",
    "accept cookies",
    "cookie policy",
    "privacy preferences",
    "subscribe to continue",
    "sign in to continue",
    "log in to continue",
    "access denied",
    "are you a robot",
    "captcha",
    "paywall",
    "this article is for subscribers",
    "create an account to continue",
]


KNOWN_STOCK_PROFILE_URL_PATTERNS = [
    "edition.cnn.com/markets/stocks/",
    "cnn.com/markets/stocks/",
    "finance.yahoo.com/quote/",
    "marketwatch.com/investing/stock/",
    "nasdaq.com/market-activity/stocks/",
    "google.com/finance/quote/",
]

# Module-level cache: avoids re-decoding the same Google News URL across reruns
_decode_cache: dict[str, tuple[Optional[str], Optional[str]]] = {}


@dataclass
class ArticleExtractionResult:
    google_news_url: str
    publisher_url: Optional[str]
    title: str
    full_text: Optional[str]
    text_extraction_status: str
    extraction_error_reason: Optional[str]
    extraction_method: str


def _clean_text(text: Optional[str]) -> str:
    if not text:
        return ""

    return re.sub(r"\s+", " ", text).strip()


def _looks_blocked(text: str) -> bool:
    lowered = text.lower()
    return any(pattern in lowered for pattern in BLOCKED_TEXT_PATTERNS)


def _is_known_stock_profile_url(url: str) -> bool:
    lowered_url = url.lower()
    return any(pattern in lowered_url for pattern in KNOWN_STOCK_PROFILE_URL_PATTERNS)


def _newspaper_config() -> Config:
    config = Config()
    config.browser_user_agent = (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0 Safari/537.36"
    )
    config.request_timeout = 10
    config.fetch_images = False
    return config


def _decode_google_news_url(google_news_url: str) -> tuple[Optional[str], Optional[str]]:
    if not google_news_url:
        return None, "Missing Google News URL"

    if google_news_url in _decode_cache:
        return _decode_cache[google_news_url]

    try:
        decoded = gnewsdecoder(google_news_url)

        if not isinstance(decoded, dict):
            result = None, "googlenewsdecoder returned an unexpected response type"
        elif decoded.get("status") is True and decoded.get("decoded_url"):
            result = decoded["decoded_url"], None
        else:
            result = None, decoded.get("message", "Google News URL could not be decoded")

    except Exception as error:
        result = None, f"googlenewsdecoder error: {type(error).__name__}: {error}"

    if result[0] is not None:
        _decode_cache[google_news_url] = result

    return result


def _extract_with_newspaper(
    publisher_url: str,
) -> tuple[Optional[str], str, Optional[str]]:
    if _is_known_stock_profile_url(publisher_url):
        return (
            None,
            "extraction_failed",
            "Decoded URL is a known stock profile or market data page",
        )

    try:
        article = Article(publisher_url, config=_newspaper_config())
        article.download()
        article.parse()

        text = _clean_text(article.text)[:100_000]

        if not text:
            return (
                None,
                "empty_article",
                "newspaper3k returned empty article text",
            )

        if _looks_blocked(text):
            return (
                None,
                "extraction_failed",
                "newspaper3k returned blocked, cookie, login, or paywall text",
            )

        if len(text) < MIN_USABLE_TEXT_LENGTH:
            return (
                None,
                "empty_article",
                f"Article text is too short for Step 4: {len(text)} characters. "
                f"Minimum is {MIN_USABLE_TEXT_LENGTH} characters.",
            )

        return text, "success", None

    except Exception as error:
        return (
            None,
            "extraction_failed",
            f"newspaper3k error: {type(error).__name__}: {error}",
        )


def _process_news_item(item: dict) -> dict:
    from services.datastore_service import get_article_by_url

    google_news_url = item.get("url") or ""
    title = item.get("title") or "Untitled article"

    publisher_url, decode_error = _decode_google_news_url(google_news_url)

    if not publisher_url:
        return {
            **item,
            "google_news_url": google_news_url,
            "publisher_url": None,
            "title": title,
            "full_text": None,
            "article_text": None,
            "text_extraction_status": "decode_failed",
            "extraction_error_reason": decode_error,
            "extraction_method": "googlenewsdecoder",
            "ready_for_sentiment": False,
            "use_for_sentiment": False,
        }

    cached = get_article_by_url(publisher_url)

    if cached:
        return {
            **item,
            **cached,
            "google_news_url": google_news_url,
            "publisher_url": publisher_url,
            "extraction_method": "datastore_cache",
            "ready_for_sentiment": True,
            "use_for_sentiment": True,
            "from_cache": True,
        }

    article_text, status, reason = _extract_with_newspaper(publisher_url)
    use = status == "success" and len(article_text or "") >= MIN_USABLE_TEXT_LENGTH

    return {
        **item,
        "google_news_url": google_news_url,
        "publisher_url": publisher_url,
        "title": title,
        "full_text": article_text,
        "article_text": article_text,
        "text_extraction_status": status,
        "extraction_error_reason": reason,
        "extraction_method": "newspaper3k",
        "ready_for_sentiment": use,
        "use_for_sentiment": use,
    }


def extract_articles(news_items: list[dict]) -> list[dict]:
    if not news_items:
        return []

    results: list[dict | None] = [None] * len(news_items)
    max_workers = min(len(news_items), 10)

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_index = {
            executor.submit(_process_news_item, item): i
            for i, item in enumerate(news_items)
        }

        for future in as_completed(future_to_index):
            i = future_to_index[future]
            try:
                results[i] = future.result()
            except Exception as error:
                item = news_items[i]
                results[i] = {
                    **item,
                    "google_news_url": item.get("url") or "",
                    "publisher_url": None,
                    "title": item.get("title") or "Untitled article",
                    "full_text": None,
                    "article_text": None,
                    "text_extraction_status": "extraction_failed",
                    "extraction_error_reason": f"Unexpected error: {error}",
                    "extraction_method": "newspaper3k",
                    "ready_for_sentiment": False,
                    "use_for_sentiment": False,
                }

    return [r for r in results if r is not None]
