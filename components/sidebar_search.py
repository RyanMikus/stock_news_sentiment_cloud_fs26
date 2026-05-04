import streamlit as st

from pages.search_dashboard import (
    COUNTRY_OPTIONS,
    SORT_OPTIONS,
    analyze_extracted_articles,
    fetch_and_extract_until_target,
    initialize_search_session_state,
)


def initialize_app_navigation_state() -> None:
    if "active_page" not in st.session_state:
        st.session_state.active_page = "Home"

    if "active_search_tab" not in st.session_state:
        st.session_state.active_search_tab = "Overview"

    if "run_analysis_after_search" not in st.session_state:
        st.session_state.run_analysis_after_search = False


def render_sidebar_search() -> None:
    initialize_search_session_state()
    initialize_app_navigation_state()

    st.sidebar.title("Article Search")

    with st.sidebar.form("sidebar_article_search_form"):
        query = st.text_input(
            "Company, ticker, or keyword",
            value=st.session_state.get("sidebar_query", "NVDA"),
            help="Examples: Apple, AAPL, NVIDIA, NVDA, Tesla, TSLA",
        )

        country_label = st.selectbox(
            "Google News country edition",
            options=list(COUNTRY_OPTIONS.keys()),
            index=0,
        )

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
            "Target articles ready for analysis",
            min_value=1,
            max_value=25,
            value=min(st.session_state.get("target_ready_articles", 10), 25),
            help=(
                "The app requests more Google News candidates if needed, "
                "until this many articles are ready for sentiment analysis "
                "or no more candidates are available."
            ),
        )

        run_analysis = st.checkbox(
            "Run sentiment and entity analysis",
            value=st.session_state.run_analysis_after_search,
            help=(
                "Uses the Google Cloud Natural Language API. "
                "Disable this during development to avoid unnecessary API calls."
            ),
        )

        search_submitted = st.form_submit_button(
            "Search, extract, and analyze articles"
            if run_analysis
            else "Search and extract articles",
            type="primary",
            use_container_width=True,
        )

    if search_submitted:
        clean_query = query.strip()

        if not clean_query:
            st.sidebar.error("Please enter a search query.")
            return

        country_code = COUNTRY_OPTIONS[country_label]

        try:
            with st.sidebar.status(
                f"Searching for {target_ready_articles} usable article(s)...",
                expanded=True,
            ) as status:
                st.write("Fetching Google News candidates...")
                st.write("Decoding publisher URLs...")
                st.write("Extracting article text...")

                extracted_articles, requested_candidates = fetch_and_extract_until_target(
                    query=clean_query,
                    target_ready_articles=target_ready_articles,
                    news_region=country_code,
                    language="en",
                    period=period,
                    sort_by=sort_by,
                )

                if run_analysis and extracted_articles:
                    st.write("Analyzing sentiment and entities...")
                    final_articles = analyze_extracted_articles(extracted_articles)
                    completion_label = "Search, extraction, and analysis completed."
                else:
                    final_articles = extracted_articles
                    completion_label = "Search and extraction completed."

                st.session_state.extracted_articles = final_articles
                st.session_state.requested_google_candidates = requested_candidates
                st.session_state.target_ready_articles = target_ready_articles
                st.session_state.run_analysis_after_search = run_analysis

                st.session_state.sidebar_query = clean_query
                st.session_state.last_search_config = {
                    "query": clean_query,
                    "country_label": country_label,
                    "country_code": country_code,
                    "period": period,
                    "sort_by": sort_by,
                    "target_ready_articles": target_ready_articles,
                    "requested_google_candidates": requested_candidates,
                    "run_analysis": run_analysis,
                }

                st.session_state.active_page = "Search Dashboard"
                st.session_state.active_search_tab = "Overview"

                if final_articles:
                    status.update(
                        label=completion_label,
                        state="complete",
                        expanded=False,
                    )
                else:
                    status.update(
                        label="Search completed, but no articles were found.",
                        state="error",
                        expanded=True,
                    )

        except Exception as error:
            st.sidebar.error(
                f"Search, extraction, or analysis failed: "
                f"{type(error).__name__}: {error}"
            )
            return

    st.sidebar.divider()

    if st.sidebar.button("Home", use_container_width=True):
        st.session_state.active_page = "Home"

    if st.session_state.get("extracted_articles"):
        if st.sidebar.button("Search Results", use_container_width=True):
            st.session_state.active_page = "Search Dashboard"
            st.session_state.active_search_tab = "Overview"