import requests
import os
from Bio import Entrez

EUTILS = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"


def search_pmids(term: str, retmax: int = 8) -> list[str]:
    """Return a list of PubMed IDs matching `term`."""
    url = f"{EUTILS}/esearch.fcgi"
    params = {"db": "pubmed", "term": term, "retmode": "json", "retmax": retmax}
    r = requests.get(url, params=params, timeout=30)
    r.raise_for_status()
    return r.json().get("esearchresult", {}).get("idlist", [])


def fetch_summaries(pmids: list[str]) -> dict[str, dict]:
    """Return a dict pmid -> summary fields (title, pubdate, etc.)."""
    if not pmids:
        return {}
    url = f"{EUTILS}/esummary.fcgi"
    params = {"db": "pubmed", "id": ",".join(pmids), "retmode": "json"}
    r = requests.get(url, params=params, timeout=30)
    r.raise_for_status()
    result = r.json().get("result", {})
    out: dict[str, dict] = {}
    for pmid in pmids:
        out[pmid] = result.get(pmid, {})
    return out


def fetch_abstracts(pmids: list[str]) -> dict[str, str]:
    """
    Fetch abstracts via Entrez efetch.
    Uses ENTREZ_EMAIL env var if provided (recommended by NCBI).
    """
    if not pmids:
        return {}

    Entrez.email = os.getenv("ENTREZ_EMAIL", "your_email@example.com")

    handle = Entrez.efetch(db="pubmed", id=",".join(pmids), retmode="xml")
    records = Entrez.read(handle)
    handle.close()

    out: dict[str, str] = {}
    for art in records.get("PubmedArticle", []):
        pmid = str(art["MedlineCitation"]["PMID"])
        article = art["MedlineCitation"]["Article"]
        abs_list = article.get("Abstract", {}).get("AbstractText", [])
        abstract = " ".join([str(t) for t in abs_list]) if abs_list else "No abstract available."
        out[pmid] = abstract

    return out
