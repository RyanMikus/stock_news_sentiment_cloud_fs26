import streamlit as st


def show_stock_detail():
    st.title("Stock Detail Page")

    ticker = st.text_input("Ticker symbol", value="NVDA")

    st.subheader(f"Details for {ticker.upper()}")

    st.write("This page will later show:")
    st.write("- stock price chart")
    st.write("- quantitative stock metrics")
    st.write("- recent related news")
    st.write("- sentiment results")
    st.write("- related stock suggestions")