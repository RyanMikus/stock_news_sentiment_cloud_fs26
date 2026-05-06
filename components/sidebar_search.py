import streamlit as st


_NAV_PAGES = ["Home", "Search Web", "Search Database"]

_HIDE_STREAMLIT_NAV_CSS = """
<style>
[data-testid="stSidebarNav"] { display: none; }
</style>
"""


def initialize_app_navigation_state() -> None:
    if "active_page" not in st.session_state:
        st.session_state.active_page = "Home"


def render_sidebar_search() -> None:
    initialize_app_navigation_state()

    st.markdown(_HIDE_STREAMLIT_NAV_CSS, unsafe_allow_html=True)

    current = st.session_state.get("active_page", "Home")

    st.sidebar.markdown("### Stock News Sentiment")
    st.sidebar.divider()

    for page in _NAV_PAGES:
        if st.sidebar.button(
            page,
            use_container_width=True,
            type="primary" if current == page else "secondary",
        ):
            st.session_state.active_page = page
            st.rerun()