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
    """
    Decode a Google News RSS URL into the real publisher URL.
    """
    if not google_news_url:
        return None, "Missing Google News URL"

    try:
        decoded = gnewsdecoder(google_news_url)

        if not isinstance(decoded, dict):
            return None, "googlenewsdecoder returned an unexpected response type"

        if decoded.get("status") is True and decoded.get("decoded_url"):
            return decoded["decoded_url"], None

        return None, decoded.get("message", "Google News URL could not be decoded")

    except Exception as error:
        return None, f"googlenewsdecoder error: {type(error).__name__}: {error}"


def _extract_with_newspaper(
    publisher_url: str,
) -> tuple[Optional[str], str, Optional[str]]:
    """
    Returns:
    - extracted text or None
    - status: success, empty_article, extraction_failed
    - error/warning reason
    """

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

        text = _clean_text(article.text)

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


def extract_article_text(news_item: dict) -> ArticleExtractionResult:
    """
    Phase 3 article extraction flow.

    1. Take Google News URL from gnews result.
    2. Decode it with googlenewsdecoder.
    3. Extract article text with newspaper3k.
    4. Mark articles with at least 1000 extracted characters as success.
    5. Mark empty, short, blocked, unusable, and known stock profile pages as not ready.
    """

    google_news_url = news_item.get("url") or ""
    title = news_item.get("title") or "Untitled article"

    publisher_url, decode_error = _decode_google_news_url(google_news_url)

    if not publisher_url:
        return ArticleExtractionResult(
            google_news_url=google_news_url,
            publisher_url=None,
            title=title,
            full_text=None,
            text_extraction_status="decode_failed",
            extraction_error_reason=decode_error,
            extraction_method="googlenewsdecoder",
        )

    article_text, status, reason = _extract_with_newspaper(publisher_url)

    if not article_text:
        return ArticleExtractionResult(
            google_news_url=google_news_url,
            publisher_url=publisher_url,
            title=title,
            full_text=None,
            text_extraction_status=status,
            extraction_error_reason=reason,
            extraction_method="newspaper3k",
        )

    return ArticleExtractionResult(
        google_news_url=google_news_url,
        publisher_url=publisher_url,
        title=title,
        full_text=article_text,
        text_extraction_status=status,
        extraction_error_reason=reason,
        extraction_method="newspaper3k",
    )


def extract_articles(news_items: list[dict]) -> list[dict]:
    """
    Enrich gnews result dictionaries with decoded publisher URLs and extracted text.

    Rules:
    - success: ready for sentiment if full_text has at least 1000 characters
    - empty_article: not ready for sentiment
    - extraction_failed: not ready for sentiment
    - decode_failed: not ready for sentiment
    """

    extracted_articles = []

    for item in news_items:
        result = extract_article_text(item)
        text_length = len(result.full_text or "")

        default_use_for_sentiment = (
            result.text_extraction_status == "success"
            and text_length >= MIN_USABLE_TEXT_LENGTH
        )

        enriched_item = {
            **item,
            "google_news_url": result.google_news_url,
            "publisher_url": result.publisher_url,
            "full_text": result.full_text,
            "article_text": result.full_text,
            "text_extraction_status": result.text_extraction_status,
            "extraction_error_reason": result.extraction_error_reason,
            "extraction_method": result.extraction_method,
            "ready_for_sentiment": default_use_for_sentiment,
            "use_for_sentiment": default_use_for_sentiment,
        }

        extracted_articles.append(enriched_item)

    return extracted_articles