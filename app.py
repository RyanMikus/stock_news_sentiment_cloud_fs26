import streamlit as st

from components.sidebar_search import render_sidebar_search
from views.home import show_home
from views.search_dashboard import show_search_web
from views.stored_data import show_search_database


st.set_page_config(
    page_title="Stock News Sentiment Dashboard",
    page_icon="📈",
    layout="wide",
)


def main() -> None:
    render_sidebar_search()

    active_page = st.session_state.get("active_page", "Home")

    if active_page == "Search Web":
        show_search_web()
    elif active_page == "Search Database":
        show_search_database()
    else:
        show_home()


if __name__ == "__main__":
    main()
