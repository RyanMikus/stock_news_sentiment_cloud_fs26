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
class SentenceSentiment:
    text: str
    score: float
    magnitude: float


@dataclass
class SentimentAnalysisResult:
    sentiment_score: float | None
    sentiment_magnitude: float | None
    weighted_sentiment: float | None
    sentiment_label: str
    sentence_sentiments: list[dict[str, Any]]
    sentiment_analysis_status: str
    sentiment_error_reason: str | None


def _get_language_client() -> language_v1.LanguageServiceClient:
    return language_v1.LanguageServiceClient()


def _truncate_text_for_api(text: str, max_bytes: int = MAX_TEXT_BYTES) -> str:
    """
    Keeps text safely below the Natural Language API request size limit.

    We truncate by bytes, not by characters, because API limits are byte-based.
    """
    encoded_text = text.encode("utf-8")

    if len(encoded_text) <= max_bytes:
        return text

    truncated = encoded_text[:max_bytes]
    return truncated.decode("utf-8", errors="ignore")


def calculate_weighted_sentiment(
    sentiment_score: float | None,
    sentiment_magnitude: float | None,
) -> float | None:
    """
    Combines sentiment direction and emotional strength.

    Formula:
    weighted_sentiment = sentiment_score * sentiment_magnitude

    Positive values mean positive sentiment with strength.
    Negative values mean negative sentiment with strength.
    Values near zero mean neutral, weak, or mixed directional sentiment.
    """
    if sentiment_score is None or sentiment_magnitude is None:
        return None

    return sentiment_score * sentiment_magnitude


def _sentiment_label(score: float | None) -> str:
    if score is None:
        return "unknown"

    if score > 0.1:
        return "positive"

    if score < -0.1:
        return "negative"

    return "neutral"


def analyze_sentiment(text: str) -> dict[str, Any]:
    """
    Analyze overall and sentence-level sentiment using Google Cloud Natural Language API.

    Returns a plain dictionary so it can be stored in Streamlit session state,
    displayed in a dataframe, and later saved to Datastore.
    """
    clean_text = (text or "").strip()

    if not clean_text:
        result = SentimentAnalysisResult(
            sentiment_score=None,
            sentiment_magnitude=None,
            weighted_sentiment=None,
            sentiment_label="unknown",
            sentence_sentiments=[],
            sentiment_analysis_status="skipped",
            sentiment_error_reason="No article text available for sentiment analysis.",
        )
        return asdict(result)

    try:
        client = _get_language_client()

        document = language_v1.Document(
            content=_truncate_text_for_api(clean_text),
            type_=language_v1.Document.Type.PLAIN_TEXT,
        )

        response = client.analyze_sentiment(request={"document": document})
        document_sentiment = response.document_sentiment

        sentence_sentiments = []

        for sentence in response.sentences:
            sentence_sentiments.append(
                asdict(
                    SentenceSentiment(
                        text=sentence.text.content,
                        score=float(sentence.sentiment.score),
                        magnitude=float(sentence.sentiment.magnitude),
                    )
                )
            )

        score = float(document_sentiment.score)
        magnitude = float(document_sentiment.magnitude)
        weighted_sentiment = calculate_weighted_sentiment(score, magnitude)

        result = SentimentAnalysisResult(
            sentiment_score=score,
            sentiment_magnitude=magnitude,
            weighted_sentiment=weighted_sentiment,
            sentiment_label=_sentiment_label(score),
            sentence_sentiments=sentence_sentiments,
            sentiment_analysis_status="success",
            sentiment_error_reason=None,
        )

        return asdict(result)

    except Exception as error:
        result = SentimentAnalysisResult(
            sentiment_score=None,
            sentiment_magnitude=None,
            weighted_sentiment=None,
            sentiment_label="unknown",
            sentence_sentiments=[],
            sentiment_analysis_status="failed",
            sentiment_error_reason=f"{type(error).__name__}: {error}",
        )
        return asdict(result)


def analyze_article_sentiment(article: dict[str, Any]) -> dict[str, Any]:
    """
    Enrich one article dictionary with sentiment results.

    Only articles selected for sentiment and successfully extracted should be analyzed.
    """
    if (
        article.get("sentiment_analysis_status") == "success"
        and article.get("sentiment_score") is not None
    ):
        return article

    full_text = article.get("full_text") or article.get("article_text") or ""

    if not article.get("use_for_sentiment"):
        return {
            **article,
            "sentiment_score": None,
            "sentiment_magnitude": None,
            "weighted_sentiment": None,
            "sentiment_label": "unknown",
            "sentence_sentiments": [],
            "sentiment_analysis_status": "skipped",
            "sentiment_error_reason": "Article was not selected for sentiment analysis.",
        }

    if article.get("text_extraction_status") != "success":
        return {
            **article,
            "sentiment_score": None,
            "sentiment_magnitude": None,
            "weighted_sentiment": None,
            "sentiment_label": "unknown",
            "sentence_sentiments": [],
            "sentiment_analysis_status": "skipped",
            "sentiment_error_reason": "Article text extraction did not succeed.",
        }

    title = (article.get("title") or "").strip()
    if title and title.lower() not in full_text[:500].lower():
        full_text = f"{title}\n\n{full_text}"

    sentiment_result = analyze_sentiment(full_text)

    return {
        **article,
        **sentiment_result,
    }


def analyze_articles_sentiment(articles: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not articles:
        return articles

    results: list[dict | None] = [None] * len(articles)

    with ThreadPoolExecutor(max_workers=min(len(articles), 10)) as executor:
        future_to_index = {
            executor.submit(analyze_article_sentiment, article): i
            for i, article in enumerate(articles)
        }

        for future in as_completed(future_to_index):
            i = future_to_index[future]
            try:
                results[i] = future.result()
            except Exception:
                results[i] = articles[i]

    return [r for r in results if r is not None]