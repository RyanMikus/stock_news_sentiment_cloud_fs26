from datetime import datetime, timezone

import streamlit as st

from components.article_cards import render_articles_tab
from components.overview import render_overview_tab
from views.stock_detail import render_stocks_from_articles
from services.datastore_service import query_articles


def _render_results(articles: list[dict]) -> None:
    overview_tab, articles_tab, stocks_tab = st.tabs(["Overview", "Articles", "Charts"])

    with overview_tab:
        render_overview_tab(articles)

    with articles_tab:
        render_articles_tab(articles, show_delete=True)

    with stocks_tab:
        render_stocks_from_articles(articles)


def _render_query_section() -> None:
    with st.form("database_query_form"):
        company = st.text_input(
            "Company, ticker, or keyword",
            placeholder="e.g. NVIDIA, Apple, Federal Reserve",
        )

        col1, col2, col3 = st.columns([1, 1, 2])

        with col1:
            start_input = st.date_input("Published from", value=None)
        with col2:
            end_input = st.date_input("Published to", value=None)
        with col3:
            min_sentiment, max_sentiment = st.slider(
                "Sentiment score range",
                min_value=-1.0,
                max_value=1.0,
                value=(-1.0, 1.0),
                step=0.05,
            )

        start_date = None
        end_date = None

        if start_input:
            start_date = datetime(
                start_input.year, start_input.month, start_input.day,
                tzinfo=timezone.utc,
            )
        if end_input:
            end_date = datetime(
                end_input.year, end_input.month, end_input.day,
                23, 59, 59,
                tzinfo=timezone.utc,
            )

        run_query = st.form_submit_button(
            "Run Query",
            type="primary",
            use_container_width=True,
        )

    if not run_query and "stored_query_results" not in st.session_state:
        return

    if run_query:
        with st.spinner("Querying Database..."):
            try:
                results = query_articles(
                    company=company.strip() if company else None,
                    min_sentiment=min_sentiment,
                    max_sentiment=max_sentiment,
                    start_date=start_date,
                    end_date=end_date,
                )
                st.session_state.stored_query_results = results
                for key in list(st.session_state.keys()):
                    if key.startswith("gemini_"):
                        del st.session_state[key]
            except Exception as error:
                st.error(f"Query failed: {type(error).__name__}: {error}")
                return

    results = st.session_state.get("stored_query_results", [])

    if not results:
        st.info("No articles found for the current filters.")
        return

    st.caption(f"Found **{len(results)}** article(s).")

    _render_results(results)


def show_search_database() -> None:
    st.title("Search Database")
    _render_query_section()
