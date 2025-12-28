import os
import re
import streamlit as st

from src.pubmed import search_pmids, fetch_summaries, fetch_abstracts
from src.query_compiler import compile_pubmed_query
from src.reply import answer_question_with_abstracts

def detect_confidence_level_1(answer_md: str) -> tuple[str, str]:
    """
    Level 1: heuristic + explainable confidence.
    Uses only the model output wording (no extra API calls).
    Returns (label, reason).
    """
    t = (answer_md or "").lower()

    low_cues = [
        "not enough evidence",
        "insufficient evidence",
        "do not directly address",
        "does not directly address",
        "cannot conclude",
        "not possible to conclude",
        "do not allow us to conclude",
        "limited direct evidence",
    ]

    moderate_cues = [
        "suggests",
        "may",
        "might",
        "could",
        "indirect",
        "mixed",
        "limited",
    ]

    low_hits = sum(p in t for p in low_cues)
    moderate_hits = sum(p in t for p in moderate_cues)

    if low_hits >= 1:
        return (
            "Low",
            "The retrieved abstracts do not directly support a strong conclusion for this question.",
        )

    if moderate_hits >= 2:
        return (
            "Moderate",
            "Some evidence is relevant, but the conclusion relies on indirect or limited findings.",
        )

    return (
        "High",
        "Multiple statements appear directly supported by the retrieved abstracts.",
    )

st.set_page_config(page_title="PubMed Explorer", page_icon="🧬", layout="wide")

st.title("🧬 PubMed Explorer")
st.write(
    "Type anything — the app compiles your text into a PubMed query, retrieves "
    "relevant papers, and can synthesize an answer grounded in abstracts."
)

# -----------------------------
# Adaptive retmax (auto-tuning)
# -----------------------------
def recommend_retmax(query: str) -> int:
    q = (query or "").strip().lower()
    if not q:
        return 15

    words = re.findall(r"[a-z0-9]+", q)
    n = len(words)

    broad_starters = {"how", "what", "why", "when", "where", "which", "does", "do", "can"}
    starts_broad = words and words[0] in broad_starters

    has_quotes = '"' in q
    has_year = bool(re.search(r"\b(19|20)\d{2}\b", q))

    score = 0
    if starts_broad:
        score += 1
    if n <= 6:
        score += 2
    elif n <= 10:
        score += 1
    if has_quotes or has_year:
        score -= 1

    if score >= 3:
        return 25
    if score == 2:
        return 20
    if score == 1:
        return 15
    return 12


# -----------------------------
# Session state init
# -----------------------------
if "last_search" not in st.session_state:
    st.session_state.last_search = {
        "query": "",
        "retmax": 15,
        "use_ai_expand": True,
        "term": "",
        "debug": {},
        "pmids": [],
        "summaries": {},
        "abstracts": {},
        "answer_md": None,
        "answer_error": None,
        "answer_generated_for": None,
    }

# -----------------------------
# Inputs
# -----------------------------
query = st.text_input("Enter a research question:")

recommended_retmax = recommend_retmax(query)

col1, col2, col3 = st.columns([1, 2, 2])
with col1:
    retmax = st.number_input(
        "Results",
        min_value=1,
        max_value=25,
        value=int(st.session_state.get("retmax", recommended_retmax)),
        step=1,
        help=f"Recommended for this query: {recommended_retmax}",
    )
    st.session_state["retmax"] = int(retmax)

with col2:
    st.caption("Result count is automatically tuned based on query breadth.")

with col3:
    use_ai_expand = st.toggle("AI-expand search terms (optional)", value=True)

# Advanced controls (hidden by default)
related = ""
with st.expander("Advanced options"):
    related = st.text_input(
        "Optional related terms (comma-separated)",
        help="Adds OR terms to broaden recall if results are too narrow.",
    )

# Use a form so "Search" behaves predictably
with st.form("search_form", clear_on_submit=False):
    submitted = st.form_submit_button("Search")

# -----------------------------
# Search pipeline
# -----------------------------
if submitted:
    if not query.strip():
        st.warning("Enter a query.")
        st.stop()

    os.environ["USE_AI_EXPANSION"] = "1" if use_ai_expand else "0"

    term, debug = compile_pubmed_query(query)

    if related.strip():
        extra = [t.strip() for t in related.split(",") if t.strip()]
        if extra:
            term = f"({term}) OR " + " OR ".join(f"({t})" for t in extra)
            debug["related_terms"] = extra
            debug["pubmed_term_with_related"] = term

    with st.spinner("Searching PubMed..."):
        pmids = search_pmids(term, retmax=int(retmax))

    if not pmids:
        st.info("No results found.")
        st.stop()

    with st.spinner("Fetching summaries..."):
        summaries = fetch_summaries(pmids)

    with st.spinner("Fetching abstracts..."):
        abstracts = fetch_abstracts(pmids)

    st.session_state.last_search = {
        "query": query,
        "retmax": int(retmax),
        "use_ai_expand": bool(use_ai_expand),
        "term": term,
        "debug": debug,
        "pmids": pmids,
        "summaries": summaries,
        "abstracts": abstracts,
        "answer_md": None,
        "answer_error": None,
        "answer_generated_for": None,
    }

# -----------------------------
# Render results
# -----------------------------
ls = st.session_state.last_search
pmids = ls["pmids"]
summaries = ls["summaries"]
abstracts = ls["abstracts"]
term = ls["term"]
debug = ls["debug"]

ai_available = bool(os.getenv("GROQ_API_KEY", "").strip())

def _render_sources(pmids_list):
    st.subheader("Sources")
    for pmid in pmids_list:
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

if pmids:
    if ai_available:
        st.subheader("Evidence-Based Synthesis")
        st.caption(
            "This synthesis is generated **only** from the retrieved PubMed abstracts. "
            "If the literature does not directly answer the question, the system will say so."
        )

        pmids_fingerprint = ",".join(pmids)
        gen_key = (ls["query"], term, pmids_fingerprint)

        if ls["answer_generated_for"] != gen_key:
            with st.spinner("Synthesizing answer from abstracts..."):
                try:
                    answer_md = answer_question_with_abstracts(
                        question=ls["query"],
                        pmids=pmids,
                        summaries=summaries,
                        abstracts=abstracts,
                    )
                    ls["answer_md"] = answer_md
                    ls["answer_error"] = None
                except Exception as e:
                    ls["answer_md"] = None
                    ls["answer_error"] = f"{type(e).__name__}: {e}"
                ls["answer_generated_for"] = gen_key
                st.session_state.last_search = ls

        if ls["answer_error"]:
            st.error("AI answer generation failed.")
            st.code(ls["answer_error"], language="text")
        elif ls["answer_md"]:
            level, reason = detect_confidence_level_1(ls["answer_md"])
            st.markdown(f"**Confidence:** {level}")
            st.caption(reason)

            st.markdown(ls["answer_md"])
            st.caption("All statements above are derived exclusively from the cited PubMed abstracts.")
            
        with st.expander(f"Show sources ({len(pmids)} papers)"):
            _render_sources(pmids)

    else:
        st.info(
            "To enable evidence-based synthesis, set an API key locally. "
            "You can still review all retrieved abstracts below."
        )
        _render_sources(pmids)

# -----------------------------
# Transparency / Debug
# -----------------------------
if term or debug:
    with st.expander("Show search details (advanced)"):
        st.code(debug.get("pubmed_term_with_related", debug.get("pubmed_term", term)))
        st.write("Extracted terms:", debug.get("terms_used", []))

st.caption(
    "Security: API keys are never stored in this repo. "
    "AI features are optional and sources are always available."
)
