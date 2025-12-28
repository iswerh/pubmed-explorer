import streamlit as st
from src.pubmed import search_pmids, fetch_summaries, fetch_abstracts
from src.query_compiler import compile_pubmed_query

st.set_page_config(page_title="PubMed Explorer", page_icon="🧬", layout="wide")

st.title("🧬 PubMed Explorer")
st.write("Type anything — the app compiles your text into a PubMed query and retrieves relevant papers.")

query = st.text_input("Enter a research question:")
related = st.text_input("Optional related terms (comma-separated):")

col1, col2 = st.columns([1, 2])
with col1:
    retmax = st.number_input("Results", min_value=1, max_value=25, value=8, step=1)
with col2:
    st.caption("Tip: related terms are optional and help broaden search coverage.")

if st.button("Search"):
    if not query.strip():
        st.warning("Enter a query.")
        st.stop()

    # Compile user's free-form text into a PubMed-safe query (filler stripping + date extraction, etc.)
    term, debug = compile_pubmed_query(query)

    # Optional: broaden search with additional related terms
    if related.strip():
        extra = [t.strip() for t in related.split(",") if t.strip()]
        if extra:
            term = f"({term}) OR " + " OR ".join([f"({t})" for t in extra])
            debug["related_terms"] = extra
            debug["pubmed_term_with_related"] = term

    if not term.strip("() ").strip():
        st.warning("Enter a query.")
        st.stop()

    with st.spinner("Searching PubMed..."):
        pmids = search_pmids(term, retmax=int(retmax))

    if not pmids:
        st.info("No results found.")
        with st.expander("Show search details (advanced)"):
            st.code(debug.get("pubmed_term_with_related", debug.get("pubmed_term", term)), language="text")
            if debug.get("terms_used") is not None:
                st.write("Extracted terms:", debug["terms_used"])
            if debug.get("start_date"):
                st.write("Date range:", debug["start_date"], "→", debug.get("end_date"))
        st.stop()

    with st.spinner("Fetching summaries..."):
        summaries = fetch_summaries(pmids)

    with st.spinner("Fetching abstracts..."):
        abstracts = fetch_abstracts(pmids)

    st.subheader("Top results")
    for pmid in pmids:
        s = summaries.get(pmid, {})
        title = (s.get("title") or "No title").strip()
        pubdate = s.get("pubdate") or "No date"
        link = f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/"
        abstract = abstracts.get(pmid, "No abstract available.")

        with st.expander(title):
            st.markdown(f"**Date:** {pubdate}")
            st.markdown(f"**PMID:** `{pmid}`")
            st.markdown(f"**Link:** {link}")
            st.write(abstract)

    # Optional auditability: hide compiled query unless user opens the expander
    with st.expander("Show search details (advanced)"):
        st.code(debug.get("pubmed_term_with_related", debug.get("pubmed_term", term)), language="text")
        if debug.get("terms_used") is not None:
            st.write("Extracted terms:", debug["terms_used"])
        if debug.get("start_date"):
            st.write("Date range:", debug["start_date"], "→", debug.get("end_date"))
        if debug.get("core_after_filler_strip"):
            st.write("After filler stripping:", debug["core_after_filler_strip"])

st.caption("Security: API keys are not stored in this repo. AI features are optional and come later.")
