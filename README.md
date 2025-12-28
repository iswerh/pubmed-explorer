
IMPORTANT
-----------------------------------------------------------------------------
This project is tested on Python **3.12.x**.
Some dependencies are not yet compatible with Python 3.13+.
If you encounter import or runtime errors, ensure you are using Python 3.12.
-----------------------------------------------------------------------------

PubMed Explorer is a research tool that turns natural-language questions into
evidence-grounded answers using PubMed abstracts.

Users can type any query or question, and based off their question. PubMed Explorer will generate an answer based off 

## Demo

[![PubMed Explorer Demo](https://youtu.be/2l6A4qfkUJw)


## What this app does

1. Converts free-form questions into structured PubMed queries
2. Retrieves relevant papers using the PubMed API
3. Fetches titles, dates, and abstracts

(API KEY)
4. Optionally generates an evidence-based synthesis grounded only in abstracts
5. Explicitly signals uncertainty when the literature does not support a conclusion

## Evidence-Based AI (Optional but Recommended)

If an API key is configured, the app generates a structured response consisting of:

- **Direct Answer** – a concise synthesis
- **Key Evidence Bullets** – each claim cited with PMIDs
- **Limitations** – what cannot be concluded from the abstracts
- **Confidence Level** – heuristic indicator based on strength of evidence

If no API key is present, the app still works fully as a PubMed search and
abstract exploration tool.

### Enabling AI synthesis

AI synthesis is disabled by default and activates automatically when an API key is present in the environment.

To enable it locally, create a file named .env in the project root (this file is ignored by git):

GROQ_API_KEY=your_api_key_here

Alternatively, set the variable in your shell.

macOS / Linux:
export GROQ_API_KEY=your_api_key_here

Windows (PowerShell):
setx GROQ_API_KEY "your_api_key_here"

Restart the app after setting the variable.

## Running locally

### 1. Clone and install dependencies
```bash
git clone https://github.com/iswerh/pubmed-explorer.git
cd pubmed-explorer
pip install -r requirements.txt
Run the app
python -m streamlit run app.py
```

Disclaimer

This tool is intended for research exploration only. It does not provide medical, environmental, or regulatory advice.
