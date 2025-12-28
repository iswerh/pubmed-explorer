import os
import streamlit as st

from src.pubmed import search_pmids, fetch_summaries, fetch_abstracts
from src.query_compiler import compile_pubmed_query
from src.reply import answer_question_with_abstracts

st.set_page_config(page_title="PubMed Explorer", page_icon="🧬", layout="wide")

st.title("PubMed Explorer")
st.write(
    "Type anything — the app compiles your text into a PubMed query, "
    "retrieves relevant papers, and can synthesize an answer grounded in abstracts."
)

query = st.text_input("Enter a research question:")
related = st.text_input("Optional related terms (comma-separated):")

col1, col2, col3 = st.columns([1, 2, 2])
with col1:
    retmax = st.number_input("Results", min_value=1, max_value=25, value=8, step=1)
with col2:
    st.caption("Tip: related terms are optional and help broaden search coverage.")
with col3:
    use_ai = st.toggle("AI-expand search terms (optional)", value=True)

if st.button("Search"):
    if not query.strip():
        st.warning("Enter a query.")
        st.stop()

    # Control AI expansion per run (compiler reads this env var)
    os.environ["USE_AI_EXPANSION"] = "1" if use_ai else "0"

    # Compile free-form query -> PubMed-safe query
    term, debug = compile_pubmed_query(query)

    # Optional: manual OR expansion via related terms
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
            st.code(
                debug.get("pubmed_term_with_related", debug.get("pubmed_term", term)),
                language="text",
            )
            st.write("Extracted terms:", debug.get("terms_used", []))
            if debug.get("ai_added_terms"):
                st.write("AI-added terms:", debug["ai_added_terms"])
            if debug.get("start_date"):
                st.write("Date range:", debug["start_date"], "→", debug.get("end_date"))
            if debug.get("core_after_filler_strip"):
                st.write("After filler stripping:", debug["core_after_filler_strip"])
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

    # ---- Step 21.2: AI Answer Section ----
    st.divider()
    st.subheader("AI answer (from these abstracts)")

    if st.button("Generate answer"):
        with st.spinner("Synthesizing answer from abstracts..."):
            answer_md = answer_question_with_abstracts(
                question=query,
                pmids=pmids,
                summaries=summaries,
                abstracts=abstracts,
            )
        st.markdown(answer_md)
        st.caption("Verify claims by opening the cited PMIDs above.")

    # Optional auditability
    with st.expander("Show search details (advanced)"):
        st.code(
            debug.get("pubmed_term_with_related", debug.get("pubmed_term", term)),
            language="text",
        )
        st.write("Extracted terms:", debug.get("terms_used", []))
        st.write("AI expansion enabled:", bool(debug.get("ai_expansion_enabled", False)))
        if debug.get("ai_added_terms"):
            st.write("AI-added terms:", debug["ai_added_terms"])
        if debug.get("start_date"):
            st.write("Date range:", debug["start_date"], "→", debug.get("end_date"))
        if debug.get("core_after_filler_strip"):
            st.write("After filler stripping:", debug["core_after_filler_strip"])

st.caption(
    "Security: API keys are not stored in this repo. "
    "AI features are optional and fall back safely when disabled."
)
