import os
from typing import Dict, List, Tuple

try:
    from groq import Groq
except Exception:
    Groq = None


def _truncate(text: str, max_chars: int) -> str:
    text = (text or "").strip()
    if len(text) <= max_chars:
        return text
    return text[: max_chars - 3].rstrip() + "..."


def build_context(pmids: List[str], summaries: Dict[str, dict], abstracts: Dict[str, str],
                  max_papers: int = 8, max_abs_chars: int = 1800) -> Tuple[str, List[str]]:
    """
    Build a compact context bundle: each paper is tagged with PMID and title/date.
    Returns (context_text, used_pmids)
    """
    used = pmids[:max_papers]
    blocks = []
    for pmid in used:
        s = summaries.get(pmid, {})
        title = (s.get("title") or "No title").strip()
        pubdate = s.get("pubdate") or "No date"
        abs_text = abstracts.get(pmid, "No abstract available.")
        abs_text = _truncate(abs_text, max_abs_chars)

        blocks.append(
            f"[PMID {pmid}]\n"
            f"Title: {title}\n"
            f"Date: {pubdate}\n"
            f"Abstract: {abs_text}\n"
        )

    return "\n---\n".join(blocks), used


def answer_question_with_abstracts(
    question: str,
    pmids: List[str],
    summaries: Dict[str, dict],
    abstracts: Dict[str, str],
    model: str | None = None,
) -> str:
    """
    Uses Groq (if available + key present) to answer the user's question using ONLY the provided abstracts.
    Returns a markdown answer with PMID citations.
    Safe fallback: returns an explanation if AI isn't configured.
    """
    api_key = os.getenv("GROQ_API_KEY", "").strip()
    if not api_key or Groq is None:
        return (
            "AI answer is disabled.\n\n"
            "To enable it locally:\n"
            "1) Install: `pip install groq`\n"
            "2) Set `GROQ_API_KEY` in your environment (or `.env` ignored by git)\n"
            "3) Restart the app.\n"
        )

    context, used_pmids = build_context(pmids, summaries, abstracts, max_papers=8, max_abs_chars=1800)

    sys = (
        "You are a research assistant. You must answer using ONLY the provided PubMed abstracts.\n"
        "Rules:\n"
        "- If the abstracts do not support a claim, say 'Not enough evidence in the provided abstracts.'\n"
        "- Cite PMIDs inline for every factual claim, like: (PMID 12345678).\n"
        "- Do not invent study details not present in the abstracts.\n"
        "- Prefer cautious language when evidence is mixed.\n"
        "- Output markdown.\n"
    )

    prompt = (
        f"User question:\n{question}\n\n"
        "PubMed abstracts (context):\n"
        f"{context}\n\n"
        "Write:\n"
        "1) A direct answer (3–8 sentences)\n"
        "2) Key evidence bullets (each bullet must include one or more PMID citations)\n"
        "3) Limitations / what you still can't conclude from these abstracts\n"
    )

    client = Groq(api_key=api_key)
    try:
        resp = client.chat.completions.create(
            model=model or os.getenv("GROQ_ANSWER_MODEL", "llama-3.1-70b-versatile"),
            messages=[
                {"role": "system", "content": sys},
                {"role": "user", "content": prompt},
            ],
            temperature=0.2,
            max_tokens=700,
        )
        return resp.choices[0].message.content or "No response."
    except Exception as e:
        return f"AI answer failed: `{type(e).__name__}: {e}`"
