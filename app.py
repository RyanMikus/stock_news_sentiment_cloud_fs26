import streamlit as st

from components.sidebar_search import render_sidebar_search
from pages.home import show_home
from pages.search_dashboard import show_search_dashboard


st.set_page_config(
    page_title="Stock News Sentiment Dashboard",
    page_icon="📈",
    layout="wide",
)


def main() -> None:
    render_sidebar_search()

    active_page = st.session_state.get("active_page", "Home")

    if active_page == "Search Dashboard":
        show_search_dashboard()
    else:
        show_home()


if __name__ == "__main__":
    main()