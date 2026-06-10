import streamlit as st

from components.article_cards import render_articles_tab
from components.overview import render_overview_tab
from views.stock_detail import render_stocks_from_articles
from services.news_service import fetch_company_news
from services.article_service import extract_articles
from services.sentiment_service import analyze_articles_sentiment
from services.entity_service import extract_articles_entities


COUNTRY_OPTIONS = {
    "United States": "US",
    "United Kingdom": "GB",
    "Canada": "CA",
    "Australia": "AU",
    "Singapore": "SG",
    "Switzerland": "CH",
}

SORT_OPTIONS = [
    "Google relevance",
    "Newest first",
]

MAX_GOOGLE_CANDIDATES = 100
FETCH_INCREMENT = 10
MIN_USABLE_TEXT_LENGTH = 1000


def is_usable_for_sentiment(article: dict) -> bool:
    status = article.get("text_extraction_status")
    full_text = article.get("full_text") or ""

    return status == "success" and len(full_text) >= MIN_USABLE_TEXT_LENGTH


def count_ready_articles(articles: list[dict]) -> int:
    return sum(bool(article.get("ready_for_sentiment")) for article in articles)


def prepare_article_analysis_selection(article: dict) -> None:
    usable_for_sentiment = is_usable_for_sentiment(article)

    article["use_for_sentiment"] = usable_for_sentiment
    article["ready_for_sentiment"] = usable_for_sentiment


def prepare_articles_for_analysis(articles: list[dict]) -> list[dict]:
    for article in articles:
        prepare_article_analysis_selection(article)

    return articles


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
    ready_articles = [
        article
        for article in articles
        if article.get("ready_for_sentiment")
    ]

    failed_articles = [
        article
        for article in articles
        if not article.get("ready_for_sentiment")
    ]

    return ready_articles[:target_ready_articles] + failed_articles


def build_search_query_variants(query: str) -> list[str]:
    clean_query = query.strip()

    ticker_aliases = {
        "APPL": ["AAPL", "Apple"],
        "AAPL": ["Apple"],
        "NVDA": ["NVIDIA"],
        "TSLA": ["Tesla"],
        "MSFT": ["Microsoft"],
        "GOOGL": ["Google", "Alphabet"],
        "GOOG": ["Google", "Alphabet"],
        "AMZN": ["Amazon"],
        "META": ["Meta"],
    }

    variants = [clean_query]
    upper_query = clean_query.upper()

    for alias in ticker_aliases.get(upper_query, []):
        if alias not in variants:
            variants.append(alias)

    return variants


def fetch_and_extract_until_target(
    query: str,
    target_ready_articles: int,
    news_region: str,
    language: str,
    period: str,
    sort_by: str,
) -> tuple[list[dict], int]:
    query_variants = build_search_query_variants(query)

    extracted_articles: list[dict] = []
    processed_urls = set()
    max_requested_candidates = 0

    for search_query in query_variants:
        requested_candidates = min(
            max(target_ready_articles, FETCH_INCREMENT),
            MAX_GOOGLE_CANDIDATES,
        )

        while requested_candidates <= MAX_GOOGLE_CANDIDATES:
            max_requested_candidates = max(
                max_requested_candidates,
                requested_candidates,
            )

            news_items = fetch_company_news(
                query=search_query,
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
            newly_extracted_articles = prepare_articles_for_analysis(
                newly_extracted_articles
            )
            extracted_articles.extend(newly_extracted_articles)

            ready_count = count_ready_articles(extracted_articles)

            if ready_count >= target_ready_articles:
                extracted_articles = limit_to_target_ready_articles(
                    articles=extracted_articles,
                    target_ready_articles=target_ready_articles,
                )
                return extracted_articles, max_requested_candidates

            if requested_candidates >= MAX_GOOGLE_CANDIDATES:
                break

            requested_candidates = min(
                requested_candidates + FETCH_INCREMENT,
                MAX_GOOGLE_CANDIDATES,
            )

    extracted_articles = limit_to_target_ready_articles(
        articles=extracted_articles,
        target_ready_articles=target_ready_articles,
    )

    return extracted_articles, max_requested_candidates


def analyze_extracted_articles(articles: list[dict]) -> list[dict]:
    prepared_articles = prepare_articles_for_analysis(articles)

    analyzed_articles = analyze_articles_sentiment(prepared_articles)
    analyzed_articles = extract_articles_entities(analyzed_articles)

    return analyzed_articles


def initialize_search_session_state() -> None:
    if "extracted_articles" not in st.session_state:
        st.session_state.extracted_articles = []

    if "requested_google_candidates" not in st.session_state:
        st.session_state.requested_google_candidates = 0

    if "target_ready_articles" not in st.session_state:
        st.session_state.target_ready_articles = 10


def _render_search_form() -> None:
    with st.form("search_web_form"):
        query = st.text_input(
            "Company, ticker, or keyword",
            value=st.session_state.get("sidebar_query", ""),
            placeholder="e.g. NVIDIA, Apple, Federal Reserve",
        )

        col1, col2, col3, col4 = st.columns(4)

        with col1:
            country_label = st.selectbox(
                "Country edition",
                options=list(COUNTRY_OPTIONS.keys()),
                index=0,
            )

        with col2:
            period = st.selectbox(
                "Period",
                options=["1d", "7d", "30d"],
                index=1,
            )

        with col3:
            sort_by = st.selectbox(
                "Sort by",
                options=SORT_OPTIONS,
                index=0,
            )

        with col4:
            target_ready_articles = st.slider(
                "Target articles",
                min_value=1,
                max_value=25,
                value=min(st.session_state.get("target_ready_articles", 10), 25),
            )

        search_submitted = st.form_submit_button(
            "Search & Analyze",
            type="primary",
            use_container_width=True,
        )

    if search_submitted:
        clean_query = query.strip()

        if not clean_query:
            st.error("Please enter a search query.")
            return

        country_code = COUNTRY_OPTIONS[country_label]

        try:
            with st.spinner("Searching and analyzing..."):
                extracted_articles, requested_candidates = fetch_and_extract_until_target(
                    query=clean_query,
                    target_ready_articles=target_ready_articles,
                    news_region=country_code,
                    language="en",
                    period=period,
                    sort_by=sort_by,
                )

                final_articles = analyze_extracted_articles(extracted_articles)

                st.session_state.extracted_articles = final_articles
                st.session_state.requested_google_candidates = requested_candidates
                st.session_state.target_ready_articles = target_ready_articles
                st.session_state.sidebar_query = clean_query
                for key in list(st.session_state.keys()):
                    if key.startswith("gemini_"):
                        del st.session_state[key]
                st.session_state.last_search_config = {
                    "query": clean_query,
                    "country_label": country_label,
                    "country_code": country_code,
                    "period": period,
                    "sort_by": sort_by,
                    "target_ready_articles": target_ready_articles,
                    "requested_google_candidates": requested_candidates,
                }

            if not final_articles:
                st.warning("Search completed, but no articles were found.")

        except Exception as error:
            st.error(f"Search or analysis failed: {type(error).__name__}: {error}")


def show_search_web() -> None:
    initialize_search_session_state()

    st.title("Search Web")

    _render_search_form()

    articles = st.session_state.get("extracted_articles", [])

    if not articles:
        return

    last_search_config = st.session_state.get("last_search_config")
    if last_search_config:
        st.caption(
            f"Search: **{last_search_config.get('query')}** · "
            f"{last_search_config.get('country_label')} · "
            f"{last_search_config.get('period')} · "
            f"{last_search_config.get('sort_by')}"
        )

    target_ready_articles = st.session_state.get("target_ready_articles", 0)
    ready_count = count_ready_articles(articles)

    if ready_count < target_ready_articles:
        requested_candidates = st.session_state.get("requested_google_candidates", 0)
        st.warning(
            f"Could only extract {ready_count} usable article(s) out of "
            f"{target_ready_articles} requested "
            f"(tried up to {requested_candidates} Google News candidates). "
            f"This usually happens when publishers block extraction or return short text."
        )

    overview_tab, articles_tab, stocks_tab = st.tabs(["Overview", "Articles", "Charts"])

    with overview_tab:
        render_overview_tab(articles)

    with articles_tab:
        render_articles_tab(articles, show_save=True)

    with stocks_tab:
        render_stocks_from_articles(articles)
