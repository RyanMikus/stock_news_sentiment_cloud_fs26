import streamlit as st


def show_home():
    st.title("Stock News Sentiment Dashboard")
    st.write(
        "Analyze company-related financial news using sentiment analysis, "
        "entity extraction, stock data, and visual dashboards."
    )

    st.subheader("Recent Financial News")

    mock_news = [
        {
            "title": "NVIDIA shares rise after strong AI chip demand",
            "source": "Mock Financial News",
            "date": "2026-05-03",
            "ticker": "NVDA",
            "sentiment": "Positive",
        },
        {
            "title": "Tesla faces pressure as competition increases",
            "source": "Mock Market Daily",
            "date": "2026-05-03",
            "ticker": "TSLA",
            "sentiment": "Negative",
        },
        {
            "title": "Apple announces new product updates",
            "source": "Mock Tech Business",
            "date": "2026-05-03",
            "ticker": "AAPL",
            "sentiment": "Neutral",
        },
    ]

    for article in mock_news:
        with st.container(border=True):
            st.subheader(article["title"])
            st.write(f"Source: {article['source']}")
            st.write(f"Date: {article['date']}")
            st.write(f"Ticker: {article['ticker']}")
            st.write(f"Sentiment: {article['sentiment']}")