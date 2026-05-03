import streamlit as st


def show_search():
    st.title("Company / Stock Search")

    query = st.text_input(
        "Search for a company, ticker, or keyword",
        placeholder="Example: NVIDIA, NVDA, Apple, AAPL",
    )

    max_articles = st.slider("Number of articles", 1, 10, 5)

    if st.button("Search"):
        if not query.strip():
            st.warning("Please enter a search term.")
            return

        st.success(f"Mock search started for: {query}")
        st.write(f"Maximum articles: {max_articles}")

        st.info(
            "Next step: connect this search form to gnews. "
            "For now, this page only checks that the UI works."
        )