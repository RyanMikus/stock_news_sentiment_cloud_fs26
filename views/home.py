import streamlit as st

from components.article_cards import render_article_card
from views.search_dashboard import analyze_extracted_articles
from services.article_service import extract_articles

from services.news_service import fetch_company_news


HOME_CANDIDATE_PREFETCH = 40
HOME_INITIAL_READY = 10
HOME_LOAD_MORE_READY = 5


def _prefetch_home_candidates() -> list[dict]:
    from views.search_dashboard import deduplicate_news_items
    items = fetch_company_news(
        query="financial news",
        max_results=HOME_CANDIDATE_PREFETCH,
        period="1d",
        language="en",
        news_region="US",
    )
    return deduplicate_news_items(items)


def _process_candidates_to_ready(
    candidates: list[dict],
    target_ready: int,
) -> tuple[list[dict], list[dict]]:
    from views.search_dashboard import prepare_articles_for_analysis

    ready: list[dict] = []
    i = 0

    while len(ready) < target_ready and i < len(candidates):
        needed = target_ready - len(ready)
        batch_end = min(i + max(needed * 2, 5), len(candidates))
        batch = candidates[i:batch_end]
        i = batch_end

        extracted = extract_articles(batch)
        prepared = prepare_articles_for_analysis(extracted)
        analyzed = analyze_extracted_articles(prepared)

        ready_in_batch = [
            a for a in analyzed
            if a.get("text_extraction_status") == "success"
        ][: target_ready - len(ready)]

        ready.extend(ready_in_batch)

    return ready, candidates[i:]


def _initialize_home_state() -> None:
    if "home_loaded" not in st.session_state:
        st.session_state.home_loaded = False
        st.session_state.home_articles = []
        st.session_state.home_pending = []
        st.session_state.home_load_more = False


def show_home() -> None:
    _initialize_home_state()

    st.title("Financial News")

    # Process "load more" before display so new articles appear in this render
    if st.session_state.home_load_more:
        st.session_state.home_load_more = False
        with st.spinner("Loading more articles..."):
            new_ready, remaining = _process_candidates_to_ready(
                st.session_state.home_pending,
                HOME_LOAD_MORE_READY,
            )
            st.session_state.home_articles.extend(new_ready)
            st.session_state.home_pending = remaining

    if not st.session_state.home_loaded:
        with st.spinner("Fetching today's financial news..."):
            candidates = _prefetch_home_candidates()
            st.session_state.home_pending = candidates

        with st.spinner("Analyzing..."):
            ready, remaining = _process_candidates_to_ready(
                candidates,
                HOME_INITIAL_READY,
            )
            st.session_state.home_articles = ready
            st.session_state.home_pending = remaining
            st.session_state.home_loaded = True

    passed = [
        a for a in st.session_state.home_articles
        if a.get("text_extraction_status") == "success"
    ]

    if not passed:
        st.info("No financial news articles could be loaded today.")
        if st.button("Reload"):
            st.session_state.home_loaded = False
            st.session_state.home_articles = []
            st.session_state.home_pending = []
            st.rerun()
        return

    for i, article in enumerate(passed):
        render_article_card(article, i)

    st.divider()

    col1, col2, col3 = st.columns([1, 2, 1])

    with col2:
        if st.session_state.home_pending:
            if st.button("Load 5 more", use_container_width=True):
                st.session_state.home_load_more = True
                st.rerun()
        else:
            st.caption(f"All {len(passed)} available articles shown.")

        if st.button("Refresh news", use_container_width=True, type="secondary"):
            st.session_state.home_loaded = False
            st.session_state.home_articles = []
            st.session_state.home_pending = []
            st.rerun()
