import pandas as pd
import streamlit as st

from components.article_cards import render_articles_tab
from components.overview import render_overview_tab
from pages.stock_detail import show_stock_detail
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


def format_datetime(value) -> str:
    if value is None:
        return "Unknown date"

    try:
        return value.strftime("%Y-%m-%d %H:%M")
    except AttributeError:
        return str(value)


def is_usable_for_sentiment(article: dict) -> bool:
    status = article.get("text_extraction_status")
    full_text = article.get("full_text") or ""

    return status == "success" and len(full_text) >= MIN_USABLE_TEXT_LENGTH


def calculate_weighted_sentiment(article: dict) -> float | None:
    weighted_sentiment = article.get("weighted_sentiment")

    if weighted_sentiment is not None:
        return weighted_sentiment

    sentiment_score = article.get("sentiment_score")
    sentiment_magnitude = article.get("sentiment_magnitude")

    if sentiment_score is None or sentiment_magnitude is None:
        return None

    return sentiment_score * sentiment_magnitude


def count_ready_articles(articles: list[dict]) -> int:
    return sum(bool(article.get("ready_for_sentiment")) for article in articles)


def count_selected_articles(articles: list[dict]) -> int:
    return sum(bool(article.get("use_for_sentiment")) for article in articles)


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
    """
    Runs sentiment and entity analysis directly after search/extraction.

    Articles with failed extraction remain in the result list, but the Natural Language
    API calls are skipped for them by the service layer.
    """
    prepared_articles = prepare_articles_for_analysis(articles)

    analyzed_articles = analyze_articles_sentiment(prepared_articles)
    analyzed_articles = extract_articles_entities(analyzed_articles)

    return analyzed_articles


def build_result_dataframe(articles: list[dict]) -> pd.DataFrame:
    rows = []

    for index, article in enumerate(articles):
        full_text = article.get("full_text") or ""
        entities = article.get("entities") or []
        weighted_sentiment = calculate_weighted_sentiment(article)

        entity_names = ", ".join(
            entity.get("name", "")
            for entity in entities[:20]
            if entity.get("name")
        )

        entity_types = ", ".join(
            sorted(
                {
                    entity.get("type", "")
                    for entity in entities
                    if entity.get("type")
                }
            )
        )

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
                "sentiment_score": article.get("sentiment_score"),
                "sentiment_magnitude": article.get("sentiment_magnitude"),
                "weighted_sentiment": weighted_sentiment,
                "sentiment_label": article.get("sentiment_label"),
                "sentiment_analysis_status": article.get("sentiment_analysis_status"),
                "sentiment_error_reason": article.get("sentiment_error_reason"),
                "entity_extraction_status": article.get("entity_extraction_status"),
                "entity_count": len(entities),
                "entity_names_preview": entity_names,
                "entity_types": entity_types,
                "entity_error_reason": article.get("entity_error_reason"),
            }
        )

    return pd.DataFrame(rows)


def initialize_search_session_state() -> None:
    if "extracted_articles" not in st.session_state:
        st.session_state.extracted_articles = []

    if "requested_google_candidates" not in st.session_state:
        st.session_state.requested_google_candidates = 0

    if "target_ready_articles" not in st.session_state:
        st.session_state.target_ready_articles = 10

    if "active_search_tab" not in st.session_state:
        st.session_state.active_search_tab = "Overview"


def set_active_tab(tab_name: str) -> None:
    st.session_state.active_search_tab = tab_name


def render_page_buttons() -> str:
    page_options = [
        "Overview",
        "Articles",
        "Stocks",
        "Stored Data",
    ]

    current_tab = st.session_state.get("active_search_tab", "Overview")

    if current_tab not in page_options:
        current_tab = "Overview"

    st.session_state.active_search_tab = current_tab

    st.markdown(
        """
        <style>
        /*
         * overflow:clip on the block container prevents it from creating a new
         * scroll context (unlike overflow:hidden), so position:sticky on the
         * tab bar can anchor to stMain — Streamlit's actual scroll container.
         */
        div[data-testid="stAppViewBlockContainer"] {
            overflow: clip !important;
        }

        div[data-testid="stHorizontalBlock"]:has(div.st-key-tab_btn_Overview) {
            position: sticky !important;
            top: 0 !important;
            z-index: 999999 !important;
            background-color: var(--background-color) !important;
            padding-top: 0.5rem !important;
            padding-bottom: 0.5rem !important;
            border-bottom: 1px solid rgba(128, 128, 128, 0.2) !important;
            margin-bottom: 0.25rem !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    columns = st.columns(len(page_options))

    for column, tab_name in zip(columns, page_options):
        key = f"tab_btn_{tab_name.replace(' ', '_')}"
        with column:
            st.button(
                tab_name,
                key=key,
                type="primary" if tab_name == current_tab else "secondary",
                use_container_width=True,
                on_click=set_active_tab,
                args=(tab_name,),
            )

    return current_tab


def render_dashboard_context(articles: list[dict]) -> None:
    last_search_config = st.session_state.get("last_search_config")

    if last_search_config:
        st.caption(
            f"Current search: **{last_search_config.get('query')}** · "
            f"{last_search_config.get('country_label')} · "
            f"{last_search_config.get('period')} · "
            f"{last_search_config.get('sort_by')}"
        )

    if not articles:
        st.info("No search results yet. Use the search configuration in the sidebar.")
        return

    target_ready_articles = st.session_state.get("target_ready_articles", 0)
    ready_count = count_ready_articles(articles)

    if ready_count < target_ready_articles:
        requested_candidates = st.session_state.get("requested_google_candidates", 0)

        st.warning(
            f"The app could only extract {ready_count} usable article(s), "
            f"although {target_ready_articles} were requested. "
            f"It already tried up to {requested_candidates} Google News candidates. "
            f"This usually happens when publishers block extraction, return short text, "
            f"or Google News has no more unique results for the query."
        )

    st.divider()


def render_stored_data_tab(articles: list[dict]) -> None:
    st.subheader("Stored Data")

    if not articles:
        st.info("No data available yet.")
        return

    st.info(
        "Datastore storage/querying is still planned. For now, this tab shows the current "
        "search result dataset and lets you export it."
    )

    result_df = build_result_dataframe(articles)

    st.dataframe(
        result_df,
        use_container_width=True,
        hide_index=True,
    )

    csv_data = result_df.to_csv(index=False).encode("utf-8")

    st.download_button(
        "Download current results as CSV",
        data=csv_data,
        file_name="article_search_results.csv",
        mime="text/csv",
        use_container_width=True,
    )


def render_stocks_tab() -> None:
    st.subheader("Stocks")

    st.info(
        "This tab will later connect searched articles to stock data, charts, "
        "quantitative metrics, and related stock suggestions."
    )

    show_stock_detail()


def show_search_dashboard() -> None:
    initialize_search_session_state()

    articles = st.session_state.get("extracted_articles", [])

    selected_tab = render_page_buttons()

    if selected_tab not in ["Overview", "Articles"]:
        render_dashboard_context(articles)

    if selected_tab == "Overview":
        render_overview_tab(articles)
    elif selected_tab == "Articles":
        render_articles_tab(articles)
    elif selected_tab == "Stocks":
        render_stocks_tab()
    elif selected_tab == "Stored Data":
        render_stored_data_tab(articles)