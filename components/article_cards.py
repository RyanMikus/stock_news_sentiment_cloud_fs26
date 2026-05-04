import re

import pandas as pd
import streamlit as st


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


def article_passed_extraction(article: dict) -> bool:
    return article.get("text_extraction_status") == "success"


def calculate_weighted_sentiment(article: dict) -> float | None:
    weighted_sentiment = article.get("weighted_sentiment")

    if weighted_sentiment is not None:
        return weighted_sentiment

    sentiment_score = article.get("sentiment_score")
    sentiment_magnitude = article.get("sentiment_magnitude")

    if sentiment_score is None or sentiment_magnitude is None:
        return None

    return sentiment_score * sentiment_magnitude


def prepare_article_analysis_selection(article: dict) -> None:
    """
    Since the checkbox was removed, successfully extracted articles are selected
    automatically for sentiment and entity analysis. Failed articles are not selected.
    """
    usable_for_sentiment = is_usable_for_sentiment(article)

    article["use_for_sentiment"] = usable_for_sentiment
    article["ready_for_sentiment"] = usable_for_sentiment


def build_stable_article_key(article: dict, index: int) -> str:
    """
    Builds a stable Streamlit key so Details expanders do not share open/closed
    state across Passed and Failed filtered views.
    """
    raw_key = (
        article.get("publisher_url")
        or article.get("google_news_url")
        or article.get("url")
        or article.get("title")
        or f"article_{index}"
    )

    safe_key = re.sub(r"[^a-zA-Z0-9_-]+", "_", str(raw_key)).strip("_")

    if not safe_key:
        safe_key = f"article_{index}"

    return safe_key[:180]


def render_sentence_level_sentiment(article: dict) -> None:
    st.subheader("Sentence-Level Sentiment")

    sentence_sentiments = article.get("sentence_sentiments") or []

    if article.get("sentiment_error_reason"):
        st.warning(article["sentiment_error_reason"])

    if not sentence_sentiments:
        st.info("No sentence-level sentiment available.")
        return

    sentence_rows = [
        {
            "sentence": sentence.get("text"),
            "score": sentence.get("score"),
            "magnitude": sentence.get("magnitude"),
        }
        for sentence in sentence_sentiments
    ]

    st.dataframe(
        pd.DataFrame(sentence_rows),
        use_container_width=True,
        hide_index=True,
    )


def render_entity_result(article: dict) -> None:
    entities = article.get("entities") or []

    st.subheader("Extracted Entities")

    if article.get("entity_error_reason"):
        st.warning(article["entity_error_reason"])

    if not entities:
        st.info("No entities extracted.")
        return

    entity_rows = [
        {
            "name": entity.get("name"),
            "type": entity.get("type"),
            "salience": entity.get("salience"),
            "wikipedia_url": entity.get("wikipedia_url"),
        }
        for entity in entities
    ]

    entity_rows = sorted(
        entity_rows,
        key=lambda row: row.get("salience") or 0,
        reverse=True,
    )

    st.dataframe(
        pd.DataFrame(entity_rows),
        use_container_width=True,
        hide_index=True,
    )


def render_extracted_text(article: dict) -> None:
    full_text = article.get("full_text") or ""

    st.subheader("Extracted Article Text")

    if not full_text:
        st.info("No extracted article text available.")
        return

    st.text(full_text)


def render_article_details(article: dict) -> None:
    render_sentence_level_sentiment(article)

    st.divider()

    render_entity_result(article)

    st.divider()

    render_extracted_text(article)


def render_article_card_metrics(article: dict) -> None:
    full_text = article.get("full_text") or ""

    sentiment_score = article.get("sentiment_score")
    sentiment_magnitude = article.get("sentiment_magnitude")
    weighted_sentiment = calculate_weighted_sentiment(article)

    metric_col_1, metric_col_2, metric_col_3, metric_col_4 = st.columns(4)

    with metric_col_1:
        st.metric(
            "Weighted sentiment",
            f"{weighted_sentiment:.3f}" if weighted_sentiment is not None else "N/A",
        )

    with metric_col_2:
        st.metric(
            "Score",
            f"{sentiment_score:.3f}" if sentiment_score is not None else "N/A",
        )

    with metric_col_3:
        st.metric(
            "Magnitude",
            f"{sentiment_magnitude:.3f}" if sentiment_magnitude is not None else "N/A",
        )

    with metric_col_4:
        st.metric("Text length", len(full_text))


def render_original_article_button(article: dict) -> None:
    publisher_url = article.get("publisher_url")
    google_news_url = article.get("google_news_url") or article.get("url")

    if publisher_url:
        st.link_button(
            "Open original article",
            publisher_url,
            use_container_width=True,
        )
        return

    if google_news_url:
        st.link_button(
            "Open Google News result",
            google_news_url,
            use_container_width=True,
        )
        return

    st.caption("No article link available.")


def render_article_card(article: dict, index: int) -> None:
    prepare_article_analysis_selection(article)

    title = article.get("title") or "Untitled article"
    source = article.get("source") or "Unknown source"
    published_at = format_datetime(article.get("published_at"))
    article_key = build_stable_article_key(article, index)

    with st.container(border=True, key=f"article_card_{article_key}"):
        st.subheader(f"{index + 1}. {title}")
        st.caption(f"{source} · {published_at}")

        render_article_card_metrics(article)
        render_original_article_button(article)

        with st.expander("Details"):
            render_article_details(article)


def set_article_status_filter(status_name: str) -> None:
    st.session_state.article_status_filter = status_name


def initialize_article_filter_state() -> None:
    if "article_status_filter" not in st.session_state:
        st.session_state.article_status_filter = "Passed"

    if st.session_state.article_status_filter not in ["Passed", "Failed"]:
        st.session_state.article_status_filter = "Passed"


def filter_articles_by_status(
    articles: list[dict],
    selected_status_filter: str,
) -> list[dict]:
    filtered_articles = []

    for article in articles:
        passed = article_passed_extraction(article)

        if selected_status_filter == "Passed" and passed:
            filtered_articles.append(article)

        if selected_status_filter == "Failed" and not passed:
            filtered_articles.append(article)

    return filtered_articles


def render_article_filter_buttons(
    passed_count: int,
    failed_count: int,
) -> str:
    initialize_article_filter_state()

    st.markdown(
        """
        <style>
        div[data-testid="stHorizontalBlock"]:has(div.st-key-article_filter_button_Passed) {
            gap: 0.5rem;
            margin-top: 0.25rem;
            margin-bottom: 0.5rem;
        }

        div[data-testid="stHorizontalBlock"]:has(div.st-key-article_filter_button_Passed) button {
            white-space: nowrap;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    filter_options = [
        ("Passed", passed_count),
        ("Failed", failed_count),
    ]

    selected_filter = st.session_state.article_status_filter

    columns = st.columns(len(filter_options))

    for column, (status_name, count) in zip(columns, filter_options):
        with column:
            is_active = status_name == selected_filter

            st.button(
                f"{status_name} ({count})",
                key=f"article_filter_button_{status_name}",
                use_container_width=True,
                type="primary" if is_active else "secondary",
                on_click=set_article_status_filter,
                args=(status_name,),
            )

    return st.session_state.article_status_filter


def render_articles_tab(articles: list[dict]) -> None:
    if not articles:
        st.info("No articles available. Run a search from the sidebar.")
        return

    for article in articles:
        prepare_article_analysis_selection(article)

    st.subheader("Articles")

    passed_count = sum(article_passed_extraction(article) for article in articles)
    failed_count = len(articles) - passed_count

    col1, col2, col3 = st.columns(3)
    col1.metric("Total articles", len(articles))
    col2.metric("Passed extraction", passed_count)
    col3.metric("Failed extraction", failed_count)

    selected_status_filter = render_article_filter_buttons(
        passed_count=passed_count,
        failed_count=failed_count,
    )

    filtered_articles = filter_articles_by_status(
        articles=articles,
        selected_status_filter=selected_status_filter,
    )

    st.caption(f"Showing {len(filtered_articles)} of {len(articles)} article(s).")

    st.divider()

    if not filtered_articles:
        st.info(f"No {selected_status_filter.lower()} articles available.")
        return

    for article in filtered_articles:
        original_index = articles.index(article)
        render_article_card(article, original_index)