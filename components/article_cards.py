import io
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
    usable_for_sentiment = is_usable_for_sentiment(article)

    article["use_for_sentiment"] = usable_for_sentiment
    article["ready_for_sentiment"] = usable_for_sentiment


def build_stable_article_key(article: dict, index: int) -> str:
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
        column_config={
            "sentence": st.column_config.TextColumn("Sentence"),
            "score": st.column_config.NumberColumn("Score", format="%.3f"),
            "magnitude": st.column_config.NumberColumn("Magnitude", format="%.3f"),
        },
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
        column_config={
            "name": st.column_config.TextColumn("Name"),
            "type": st.column_config.TextColumn("Type"),
            "salience": st.column_config.NumberColumn("Salience", format="%.3f"),
            "wikipedia_url": st.column_config.LinkColumn("Wikipedia"),
        },
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


def _escape_markdown(text: str) -> str:
    return re.sub(r"([\\`*_{}[\]()#+\-!$|])", r"\\\1", text)


def render_article_card(
    article: dict,
    index: int,
    show_save_checkbox: bool = False,
    show_delete_checkbox: bool = False,
) -> None:
    prepare_article_analysis_selection(article)

    title = article.get("title") or "Untitled article"
    source = article.get("source") or "Unknown source"
    published_at = format_datetime(article.get("published_at"))
    article_key = build_stable_article_key(article, index)

    with st.container(border=True, key=f"article_card_{article_key}"):
        if show_save_checkbox:
            title_col, chk_col = st.columns([11, 1])
            with title_col:
                st.subheader(f"{index + 1}. {_escape_markdown(title)}")
            with chk_col:
                st.checkbox(
                    "Save",
                    value=True,
                    key=f"save_chk_{article_key}",
                    label_visibility="collapsed",
                )
        elif show_delete_checkbox:
            title_col, chk_col = st.columns([11, 1])
            with title_col:
                st.subheader(f"{index + 1}. {_escape_markdown(title)}")
            with chk_col:
                st.checkbox(
                    "Delete",
                    value=False,
                    key=f"delete_chk_{article_key}",
                    label_visibility="collapsed",
                )
        else:
            st.subheader(f"{index + 1}. {_escape_markdown(title)}")

        st.caption(f"{_escape_markdown(source)} · {published_at}")

        render_article_card_metrics(article)
        render_original_article_button(article)

        with st.expander("Details"):
            render_article_details(article)


def _build_article_export_dataframe(articles: list[dict]) -> pd.DataFrame:
    rows = []

    for article in articles:
        entities = article.get("entities") or []
        entity_names_preview = ", ".join(
            e["name"] for e in entities[:10] if e.get("name")
        )

        rows.append(
            {
                "title": article.get("title"),
                "source": article.get("source"),
                "published_at": article.get("published_at"),
                "query": article.get("query"),
                "sentiment_score": article.get("sentiment_score"),
                "sentiment_magnitude": article.get("sentiment_magnitude"),
                "weighted_sentiment": article.get("weighted_sentiment"),
                "sentiment_label": article.get("sentiment_label"),
                "entity_names": entity_names_preview,
                "url": article.get("url"),
            }
        )

    return pd.DataFrame(rows)


def _render_article_export_buttons(articles: list[dict]) -> None:
    df = _build_article_export_dataframe(articles)

    col1, col2, col3 = st.columns(3)

    with col1:
        st.download_button(
            "Download CSV",
            data=df.to_csv(index=False).encode("utf-8"),
            file_name="articles.csv",
            mime="text/csv",
            use_container_width=True,
        )

    with col2:
        st.download_button(
            "Download JSON",
            data=df.to_json(orient="records", date_format="iso", indent=2),
            file_name="articles.json",
            mime="application/json",
            use_container_width=True,
        )

    with col3:
        excel_df = df.copy()
        for col in excel_df.select_dtypes(include="datetimetz").columns:
            excel_df[col] = excel_df[col].dt.tz_convert(None)

        excel_buffer = io.BytesIO()
        excel_df.to_excel(excel_buffer, index=False)
        excel_buffer.seek(0)

        st.download_button(
            "Download Excel",
            data=excel_buffer.getvalue(),
            file_name="articles.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
        )


def _render_save_section(
    all_articles: list[dict],
    saveable_articles: list[dict],
) -> None:
    from services.datastore_service import save_articles

    selected_count = sum(
        1 for a in saveable_articles
        if st.session_state.get(
            f"save_chk_{build_stable_article_key(a, all_articles.index(a))}",
            True,
        )
    )

    if st.button(
        f"Save {selected_count} selected to Database",
        type="primary",
        use_container_width=True,
        disabled=selected_count == 0,
    ):
        to_save = [
            a for a in saveable_articles
            if st.session_state.get(
                f"save_chk_{build_stable_article_key(a, all_articles.index(a))}",
                True,
            )
        ]
        save_articles(to_save)


def _render_delete_section(
    all_articles: list[dict],
    deletable_articles: list[dict],
) -> None:
    from services.datastore_service import delete_articles

    selected_ids = [
        a["datastore_id"]
        for a in deletable_articles
        if st.session_state.get(
            f"delete_chk_{build_stable_article_key(a, all_articles.index(a))}",
            False,
        )
        and a.get("datastore_id")
    ]

    if st.button(
        f"Delete {len(selected_ids)} selected from Database",
        use_container_width=True,
        disabled=len(selected_ids) == 0,
    ):
        delete_articles(selected_ids)
        st.toast(f"Deleted {len(selected_ids)} article(s) from database.")
        if "stored_query_results" in st.session_state:
            st.session_state.stored_query_results = [
                a for a in st.session_state.stored_query_results
                if a.get("datastore_id") not in selected_ids
            ]
        st.rerun()


def render_articles_tab(articles: list[dict], show_save: bool = False, show_delete: bool = False) -> None:
    if not articles:
        st.info("No articles available.")
        return

    for article in articles:
        prepare_article_analysis_selection(article)

    passed_articles = [a for a in articles if article_passed_extraction(a)]
    failed_articles = [a for a in articles if not article_passed_extraction(a)]

    col1, col2, col3 = st.columns(3)
    col1.metric("Total articles", len(articles))
    col2.metric("Passed extraction", len(passed_articles))
    col3.metric("Failed extraction", len(failed_articles))

    _render_article_export_buttons(articles)

    if show_save:
        saveable = [
            a for a in passed_articles
            if a.get("sentiment_analysis_status") == "success"
        ]
        _render_save_section(articles, saveable)

    if show_delete:
        _render_delete_section(articles, passed_articles)

    st.divider()

    if not passed_articles:
        st.info("No articles passed extraction.")
    else:
        for article in passed_articles:
            is_saveable = (
                show_save
                and article.get("sentiment_analysis_status") == "success"
            )
            is_deletable = show_delete
            render_article_card(
                article,
                articles.index(article),
                show_save_checkbox=is_saveable,
                show_delete_checkbox=is_deletable,
            )

    if failed_articles:
        st.divider()
        with st.expander(f"View {len(failed_articles)} failed article(s)"):
            for article in failed_articles:
                render_article_card(article, articles.index(article))
