import streamlit as st
from pages.home import show_home
from pages.search import show_search
from pages.stock_detail import show_stock_detail
from pages.stored_data import show_stored_data


st.set_page_config(
    page_title="Stock News Sentiment Dashboard",
    page_icon="📈",
    layout="wide",
)

st.sidebar.title("Navigation")

page = st.sidebar.radio(
    "Go to",
    [
        "Home",
        "Search",
        "Stock Detail",
        "Stored Data",
    ],
)

if page == "Home":
    show_home()
elif page == "Search":
    show_search()
elif page == "Stock Detail":
    show_stock_detail()
elif page == "Stored Data":
    show_stored_data()