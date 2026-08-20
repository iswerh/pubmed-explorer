# PubMed Explorer

PubMed Explorer turns natural-language questions into evidence-grounded, citation-backed answers from PubMed abstracts. Ask a question in plain English — the app converts it into a structured PubMed query, retrieves and parses the most relevant abstracts, and (optionally) synthesizes a direct answer with every claim traced back to a source PMID.

## Demo
[![PubMed Explorer Demo](https://img.youtube.com/vi/2l6A4qfkUJw/0.jpg)](https://youtu.be/2l6A4qfkUJw)

## How it works

PubMed Explorer runs a multi-stage backend pipeline rather than a single API call:

1. **Query construction** – the natural-language question is converted into a structured PubMed search query
2. **Retrieval** – the app executes ~8 API calls per query against the NCBI Entrez API to pull the top 8 relevant abstracts, titles, and publication dates
3. **Synthesis (optional, requires API key)** – if a Groq API key is configured, LLaMA-3.3 generates a structured, citation-backed response grounded only in the retrieved abstracts
4. **Confidence scoring** – each response is scored against a framework across the 8 evidence sources per query, so the app can flag when the literature doesn't support a firm conclusion instead of overstating it

End-to-end response time is typically ~1–3 seconds, including retrieval and synthesis.

### Why this design
Biomedical literature synthesis has a specific failure mode: a fluent-sounding answer that isn't actually supported by the evidence. To guard against that, the app is built so the model can only cite what it retrieved (no open-ended generation), and confidence scoring is calculated from evidence strength rather than model certainty — the two are not the same thing, and conflating them is a common mistake in RAG-style tools applied to clinical domains.

## Evidence-Based AI Response (Optional but Recommended)

When a Groq API key is configured, the app returns:

- **Direct Answer** – a concise synthesis of the retrieved abstracts
- **Key Evidence Bullets** – each claim cited with its source PMID
- **Limitations** – what the abstracts do *not* support
- **Confidence Level** – derived from the strength and consistency of retrieved evidence

Without an API key, the app still works fully as a PubMed search and abstract exploration tool — AI synthesis is an optional layer on top, not a requirement.

### Enabling AI synthesis
AI synthesis is disabled by default and activates automatically when an API key is present in the environment.

To enable it locally, create a file named `.env` in the project root (this file is ignored by git):

GROQ_API_KEY=your_api_key_here

Alternatively, set the variable in your shell:

**macOS / Linux:**
```bash
export GROQ_API_KEY=your_api_key_here
```
**Windows (PowerShell):**
```powershell
setx GROQ_API_KEY "your_api_key_here"
```
Restart the app after setting the variable.

## Running locally

**Requirements:** Python 3.12.x — some dependencies are not yet compatible with Python 3.13+.

```bash
git clone https://github.com/iswerh/pubmed-explorer.git
cd pubmed-explorer
pip install -r requirements.txt
python -m streamlit run app.py
```

## Disclaimer
This tool is intended for research exploration only. It does not provide medical, environmental, or regulatory advice.
