import streamlit as st


def show_stored_data():
    st.title("Stored Data")

    st.write(
        "This page will later query Firestore in Datastore mode "
        "and display already analyzed articles."
    )

    st.info("Datastore is not connected yet. That comes later.")