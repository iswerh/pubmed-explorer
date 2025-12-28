import streamlit as st

st.set_page_config(page_title="PubMed Explorer", layout="wide")

st.title("PubMed Explorer")
st.write("Natural-language PubMed search with author/date filters and optional AI summaries.")

query = st.text_input("Enter a research question:")
related = st.text_input("Optional related terms (comma-separated):")

st.button("Search")

st.caption("AI summary is optional and requires a local API key (not stored in this repo).")
