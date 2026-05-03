import pandas as pd
import streamlit as st

from services.news_service import fetch_company_news
from services.article_service import extract_articles


COUNTRY_OPTIONS = {
    "United States": "US",
    "United Kingdom": "GB",
    "Canada": "CA",
    "Australia": "AU",
    "Singapore": "SG",
}

SORT_OPTIONS = [
    "Google relevance",
    "Newest first",
]

MAX_GOOGLE_CANDIDATES = 100
FETCH_INCREMENT = 10
MIN_USABLE_TEXT_LENGTH = 1000


def format_datetime(value) -> str:
    if value is None:
        return "Unknown date"

    try:
        return value.strftime("%Y-%m-%d %H:%M")
    except AttributeError:
        return str(value)


def status_label(status: str) -> str:
    return {
        "success": "✅ Success",
        "empty_article": "❌ Empty / too short",
        "decode_failed": "❌ Decode failed",
        "extraction_failed": "❌ Extraction failed",
        "failed": "❌ Failed",
        "not_extracted": "Not extracted",
    }.get(status, status or "Unknown")


def is_usable_for_sentiment(article: dict) -> bool:
    status = article.get("text_extraction_status")
    full_text = article.get("full_text") or ""

    return status == "success" and len(full_text) >= MIN_USABLE_TEXT_LENGTH


def count_ready_articles(articles: list[dict]) -> int:
    return sum(bool(article.get("ready_for_sentiment")) for article in articles)


def count_selected_articles(articles: list[dict]) -> int:
    return sum(bool(article.get("use_for_sentiment")) for article in articles)


def deduplicate_news_items(news_items: list[dict]) -> list[dict]:
    seen_urls = set()
    unique_items = []

    for item in news_items:
        url = item.get("url")

        if not url or url in seen_urls:
            continue

        seen_urls.add(url)
        unique_items.append(item)

    return unique_items


def limit_to_target_ready_articles(
    articles: list[dict],
    target_ready_articles: int,
) -> list[dict]:
    limited_articles = []
    ready_count = 0

    for article in articles:
        is_ready = bool(article.get("ready_for_sentiment"))

        if is_ready and ready_count >= target_ready_articles:
            break

        limited_articles.append(article)

        if is_ready:
            ready_count += 1

        if ready_count >= target_ready_articles:
            break

    return limited_articles


def fetch_and_extract_until_target(
    query: str,
    target_ready_articles: int,
    news_region: str,
    language: str,
    period: str,
    sort_by: str,
) -> tuple[list[dict], int]:
    requested_candidates = min(
        max(target_ready_articles, FETCH_INCREMENT),
        MAX_GOOGLE_CANDIDATES,
    )

    extracted_articles: list[dict] = []
    processed_urls = set()

    while requested_candidates <= MAX_GOOGLE_CANDIDATES:
        news_items = fetch_company_news(
            query=query,
            news_region=news_region,
            language=language,
            period=period,
            max_results=requested_candidates,
            sort_by=sort_by,
        )

        news_items = deduplicate_news_items(news_items)

        new_items = [
            item
            for item in news_items
            if item.get("url") and item.get("url") not in processed_urls
        ]

        if not new_items:
            break

        for item in new_items:
            processed_urls.add(item.get("url"))

        newly_extracted_articles = extract_articles(new_items)
        extracted_articles.extend(newly_extracted_articles)

        ready_count = count_ready_articles(extracted_articles)

        if ready_count >= target_ready_articles:
            extracted_articles = limit_to_target_ready_articles(
                extracted_articles,
                target_ready_articles,
            )
            break

        if len(news_items) < requested_candidates:
            break

        requested_candidates += FETCH_INCREMENT

        if requested_candidates > MAX_GOOGLE_CANDIDATES:
            requested_candidates = MAX_GOOGLE_CANDIDATES

    return extracted_articles, requested_candidates


def build_result_dataframe(articles: list[dict]) -> pd.DataFrame:
    rows = []

    for index, article in enumerate(articles):
        full_text = article.get("full_text") or ""

        rows.append(
            {
                "index": index,
                "use_for_sentiment": bool(article.get("use_for_sentiment", False)),
                "ready_for_sentiment": bool(article.get("ready_for_sentiment", False)),
                "usable_for_sentiment": is_usable_for_sentiment(article),
                "title": article.get("title"),
                "source": article.get("source"),
                "published_at": format_datetime(article.get("published_at")),
                "query": article.get("query"),
                "news_region": article.get("news_region"),
                "google_news_url": article.get("google_news_url") or article.get("url"),
                "publisher_url": article.get("publisher_url"),
                "text_extraction_status": article.get("text_extraction_status"),
                "extraction_method": article.get("extraction_method"),
                "text_length": len(full_text),
                "extraction_error_reason": article.get("extraction_error_reason"),
            }
        )

    return pd.DataFrame(rows)


def render_status_summary(extracted_articles: list[dict]) -> None:
    total_count = len(extracted_articles)

    succeeded_count = sum(
        article.get("text_extraction_status") == "success"
        for article in extracted_articles
    )

    empty_count = sum(
        article.get("text_extraction_status") == "empty_article"
        for article in extracted_articles
    )

    failed_count = sum(
        article.get("text_extraction_status")
        in ["empty_article", "extraction_failed", "decode_failed", "failed"]
        for article in extracted_articles
    )

    ready_count = count_ready_articles(extracted_articles)
    selected_count = count_selected_articles(extracted_articles)

    col1, col2, col3, col4, col5 = st.columns(5)

    col1.metric("Articles processed", total_count)
    col2.metric("Succeeded", succeeded_count)
    col3.metric("Empty / too short", empty_count)
    col4.metric("Failed", failed_count)
    col5.metric("Ready for Step 4", ready_count)

    status_counts = (
        pd.Series(
            [
                article.get("text_extraction_status", "unknown")
                for article in extracted_articles
            ]
        )
        .value_counts()
        .rename_axis("status")
        .reset_index(name="count")
    )

    if not status_counts.empty:
        st.subheader("Extraction Status Overview")
        st.bar_chart(status_counts, x="status", y="count")

    st.caption(
        f"{selected_count} article(s) are currently selected for Step 4 sentiment analysis. "
        f"Articles with fewer than {MIN_USABLE_TEXT_LENGTH} extracted characters are never ready for Step 4."
    )


def render_article_card(article: dict, index: int) -> None:
    title = article.get("title") or "Untitled article"
    description = article.get("description") or ""
    source = article.get("source") or "Unknown source"
    published_at = format_datetime(article.get("published_at"))

    google_news_url = article.get("google_news_url") or article.get("url")
    publisher_url = article.get("publisher_url")
    status = article.get("text_extraction_status") or "not_extracted"
    reason = article.get("extraction_error_reason")
    full_text = article.get("full_text") or ""
    usable_for_sentiment = is_usable_for_sentiment(article)

    with st.container(border=True):
        top_left, top_right = st.columns([4, 1])

        with top_left:
            st.subheader(f"{index + 1}. {title}")
            st.caption(f"{source} · {published_at}")

        with top_right:
            st.write(status_label(status))

        if description:
            st.write(description)

        metric_col_1, metric_col_2, metric_col_3 = st.columns(3)

        with metric_col_1:
            st.metric("Text length", len(full_text))

        with metric_col_2:
            st.metric("Ready for Step 4", "Yes" if usable_for_sentiment else "No")

        with metric_col_3:
            st.metric(
                "Selected for Step 4",
                "Yes" if article.get("use_for_sentiment") else "No",
            )

        if usable_for_sentiment:
            article["use_for_sentiment"] = st.checkbox(
                "Use this article for sentiment analysis later",
                value=bool(article.get("use_for_sentiment", True)),
                key=f"use_for_sentiment_{index}",
            )
        else:
            article["use_for_sentiment"] = False
            article["ready_for_sentiment"] = False

        link_col_1, link_col_2 = st.columns(2)

        with link_col_1:
            if google_news_url:
                st.link_button("Open Google News URL", google_news_url)

        with link_col_2:
            if publisher_url:
                st.link_button("Open Publisher URL", publisher_url)

        if reason:
            st.warning(reason)

        if full_text:
            with st.expander("Show extracted article text"):
                st.write(full_text[:3000])

                if len(full_text) > 3000:
                    st.caption("Preview limited to first 3000 characters.")


def initialize_search_session_state() -> None:
    if "extracted_articles" not in st.session_state:
        st.session_state.extracted_articles = []

    if "requested_google_candidates" not in st.session_state:
        st.session_state.requested_google_candidates = 0

    if "target_ready_articles" not in st.session_state:
        st.session_state.target_ready_articles = 10


def show_search():
    initialize_search_session_state()

    st.title("Company / Stock Search")

    st.write(
        "Search company news, decode Google News URLs, extract full article text, "
        "and prepare usable articles for sentiment and entity analysis."
    )

    with st.expander("What this extraction step does"):
        st.markdown(
            f"""
            1. Searches Google News using `gnews`.
            2. Requests more Google News candidates if too many articles fail extraction.
            3. Decodes Google News redirect URLs using `googlenewsdecoder`.
            4. Extracts article text using `newspaper3k`.
            5. Marks articles with at least `{MIN_USABLE_TEXT_LENGTH}` extracted characters as `success`.
            6. Treats only successful articles with at least `{MIN_USABLE_TEXT_LENGTH}` characters as ready for Step 4.
            7. Marks empty, blocked, failed, or too-short articles as not ready.
            8. Stops at exactly the requested number of Step 4-ready articles when possible.
            """
        )

    st.subheader("Search Settings")

    col1, col2 = st.columns(2)

    with col1:
        query = st.text_input(
            "Company, ticker, or keyword",
            value="NVDA",
            help="Examples: Apple, AAPL, NVIDIA, NVDA, Tesla, TSLA",
        )

        country_label = st.selectbox(
            "Google News country edition",
            options=list(COUNTRY_OPTIONS.keys()),
            index=0,
        )

    with col2:
        period = st.selectbox(
            "News period",
            options=["1d", "7d", "30d"],
            index=1,
        )

        sort_by = st.selectbox(
            "Sort results",
            options=SORT_OPTIONS,
            index=0,
        )

    target_ready_articles = st.slider(
        "Target articles ready for Step 4",
        min_value=1,
        max_value=50,
        value=10,
        help=(
            "The app will request more Google News candidates if needed, "
            "until exactly this many articles are ready for sentiment analysis "
            "or no more candidates are available."
        ),
    )

    search_button = st.button(
        "Search and extract articles",
        type="primary",
        use_container_width=True,
    )

    if search_button:
        clean_query = query.strip()

        if not clean_query:
            st.error("Please enter a search query.")
            return

        country_code = COUNTRY_OPTIONS[country_label]

        try:
            with st.spinner(
                f"Fetching and extracting until {target_ready_articles} article(s) are ready for Step 4..."
            ):
                extracted_articles, requested_candidates = fetch_and_extract_until_target(
                    query=clean_query,
                    target_ready_articles=target_ready_articles,
                    news_region=country_code,
                    language="en",
                    period=period,
                    sort_by=sort_by,
                )

                st.session_state.extracted_articles = extracted_articles
                st.session_state.requested_google_candidates = requested_candidates
                st.session_state.target_ready_articles = target_ready_articles

        except Exception as error:
            st.error(f"Search or extraction failed: {type(error).__name__}: {error}")
            return

        if not st.session_state.extracted_articles:
            st.warning("No news articles found. Try another keyword, country, or period.")
            return

    if not st.session_state.extracted_articles:
        st.info("Enter a company, ticker, or keyword and click **Search and extract articles**.")
        return

    extracted_articles = st.session_state.extracted_articles
    ready_count = count_ready_articles(extracted_articles)
    target_count = st.session_state.target_ready_articles
    requested_candidates = st.session_state.requested_google_candidates

    if ready_count == target_count:
        st.success(
            f"Target reached: exactly {ready_count} article(s) are ready for Step 4. "
            f"The app requested up to {requested_candidates} Google News candidate(s)."
        )
    else:
        st.warning(
            f"Only {ready_count} article(s) are ready for Step 4, "
            f"although the target was {target_count}. "
            f"The app requested up to {requested_candidates} Google News candidate(s). "
            "Google News may not have enough usable articles for this query and period."
        )

    render_status_summary(extracted_articles)

    st.divider()

    st.header("Article Results")

    for index, article in enumerate(extracted_articles):
        render_article_card(article, index)

    st.divider()

    st.header("Extraction Results Table")

    df = build_result_dataframe(extracted_articles)

    st.dataframe(
        df.drop(columns=["index"]),
        use_container_width=True,
        hide_index=True,
    )

    csv_data = df.drop(columns=["index"]).to_csv(index=False).encode("utf-8")

    st.download_button(
        label="Download extraction results as CSV",
        data=csv_data,
        file_name="article_extraction_results.csv",
        mime="text/csv",
        use_container_width=True,
    )

    selected_articles = [
        article
        for article in extracted_articles
        if article.get("use_for_sentiment")
    ]

    st.info(
        f"{len(selected_articles)} article(s) are selected for Step 4 "
        "sentiment and entity analysis."
    )