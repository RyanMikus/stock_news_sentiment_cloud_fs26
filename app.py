import pandas as pd
import streamlit as st

from services.news_service import fetch_company_news


st.set_page_config(
    page_title="Stock News Sentiment Dashboard",
    page_icon="📈",
    layout="wide",
)


NEWS_REGION_OPTIONS = {
    "US - United States": "US",
    "GB - United Kingdom": "GB",
    "CH - Switzerland": "CH",
    "CA - Canada": "CA",
    "AU - Australia": "AU",
    "SG - Singapore": "SG",
    "IN - India": "IN",
}


def render_article_card(article: dict) -> None:
    published_at = article.get("published_at")
    published_text = published_at.strftime("%Y-%m-%d %H:%M") if published_at else "Unknown date"

    with st.container(border=True):
        st.subheader(article.get("title", "Untitled article"))

        st.caption(
            f"Source: {article.get('source') or 'Unknown'} | "
            f"Published: {published_text} | "
            f"News region: {article.get('news_region') or 'Unknown'}"
        )

        description = article.get("description")
        if description:
            st.write(description)

        url = article.get("url")
        if url:
            st.link_button("Open article", url)


def render_search_page() -> None:
    st.title("Company News Search")
    st.write(
        "Search for recent company-related news using a company name, "
        "ticker, or keyword."
    )

    col1, col2 = st.columns([3, 1])

    with col1:
        query = st.text_input(
            "Company, ticker, or keyword",
            value="NVDA",
            placeholder="Example: Apple, AAPL, NVIDIA, NVDA, Tesla, TSLA",
        )

    with col2:
        max_results = st.number_input(
            "Articles",
            min_value=1,
            max_value=50,
            value=10,
            step=1,
        )

    col3, col4, col5 = st.columns([1, 1, 1])

    with col3:
        period = st.selectbox(
            "Period",
            options=["1d", "7d", "30d"],
            index=1,
        )

    with col4:
        selected_region_label = st.selectbox(
            "Google News region",
            options=list(NEWS_REGION_OPTIONS.keys()),
            index=0,
        )
        news_region = NEWS_REGION_OPTIONS[selected_region_label]

    with col5:
        sort_by = st.selectbox(
            "Sort by",
            options=["Google relevance", "Newest first"],
            index=0,
        )

    search_clicked = st.button("Search news", type="primary")

    if search_clicked:
        try:
            with st.spinner("Fetching news..."):
                articles = fetch_company_news(
                    query=query,
                    max_results=max_results,
                    period=period,
                    news_region=news_region,
                    sort_by=sort_by,
                )

            if not articles:
                st.warning("No news articles found. Try another company, ticker, or keyword.")
                return

            st.success(f"Found {len(articles)} articles.")

            df = pd.DataFrame(articles)

            st.dataframe(
                df[["title", "source", "published_at", "news_region", "url"]],
                use_container_width=True,
                hide_index=True,
            )

            st.divider()

            for article in articles:
                render_article_card(article)

        except Exception as error:
            st.error("News fetching failed.")
            st.exception(error)


def main() -> None:
    st.sidebar.title("Navigation")

    page = st.sidebar.radio(
        "Go to",
        ["Search"],
    )

    if page == "Search":
        render_search_page()


if __name__ == "__main__":
    main()