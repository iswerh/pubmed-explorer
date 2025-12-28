# PubMed Explorer

A Streamlit app that helps you search PubMed using natural language, automatically extracts filters (author names + date ranges), retrieves abstracts from NCBI, and can optionally generate an AI-assisted summary.

## Demo
(Coming soon) — I’ll link an unlisted video demo here.

## Features
- Natural-language PubMed search
- Automatic author + date-range detection
- Abstract retrieval via NCBI Entrez
- Optional AI summary (requires local API key)

## Run locally
```bash
python -m venv .venv
# Windows:
.venv\Scripts\activate
pip install -r requirements.txt
python -m spacy download en_core_web_sm
streamlit run app.py
## Security
API keys are never stored in this repository.  
To enable AI summaries locally, use a `.env` file (see `.env.example`).
