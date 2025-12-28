import requests

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
