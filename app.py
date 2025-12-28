import streamlit as st
from src.pubmed import search_pmids, fetch_summaries

st.set_page_config(page_title="PubMed Explorer", page_icon="🧬", layout="wide")

st.title("PubMed Explorer")
st.write("Natural-language PubMed search with author/date filters and optional AI summaries.")

query = st.text_input("Enter a research question:")
related = st.text_input("Optional related terms (comma-separated):")

col1, col2 = st.columns([1, 2])
with col1:
    retmax = st.number_input("Results", min_value=1, max_value=25, value=8, step=1)
with col2:
    st.caption("Tip: related terms are optional and help broaden search coverage.")

if st.button("Search"):
    term = query.strip()
    if related.strip():
        terms = [t.strip() for t in related.split(",") if t.strip()]
        if terms:
            term = f"({term}) OR " + " OR ".join([f"({t})" for t in terms])

    if not term.strip("() ").strip():
        st.warning("Enter a query.")
        st.stop()

    with st.spinner("Searching PubMed..."):
        pmids = search_pmids(term, retmax=int(retmax))

    if not pmids:
        st.info("No results found.")
        st.stop()

    with st.spinner("Fetching summaries..."):
        summaries = fetch_summaries(pmids)

    st.subheader("Top results")
    for pmid in pmids:
        s = summaries.get(pmid, {})
        title = (s.get("title") or "No title").strip()
        pubdate = s.get("pubdate") or "No date"
        link = f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/"
        st.markdown(f"**{title}**  \n{pubdate} • PMID: `{pmid}` • {link}")

st.caption("Security: API keys are not stored in this repo. AI features come later and are optional.")
