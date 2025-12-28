import os
import re
from typing import List

try:
    from groq import Groq
except Exception:
    Groq = None  # allows repo to run even if groq package isn't installed


# Keep expansions safe + simple: no field tags, no boolean operators, no brackets.
_BAD_CHARS = re.compile(r"[\[\]\(\):]")
_BAD_TOKENS = re.compile(r"\b(AND|OR|NOT)\b", re.IGNORECASE)


def _clean_candidate(s: str) -> str:
    s = s.strip().strip('"').strip("'").strip()
    s = re.sub(r"\s+", " ", s)

    # reject anything that looks like query syntax
    if not s or len(s) < 3:
        return ""
    if _BAD_CHARS.search(s):
        return ""
    if _BAD_TOKENS.search(s):
        return ""
    if s.startswith("-"):
        return ""

    # limit length to keep it sane
    if len(s) > 60:
        return ""

    return s


def expand_terms_groq(user_text: str, seed_terms: List[str], max_new: int = 6) -> List[str]:
    """
    Returns a list of additional plain-language terms/phrases to OR into the search.
    Safe fallback: returns [] on any error or if no API key.
    """
    api_key = os.getenv("GROQ_API_KEY", "").strip()
    if not api_key or Groq is None:
        return []

    client = Groq(api_key=api_key)

    # Keep prompt narrow: we want synonyms / related phrases only.
    seed_preview = ", ".join(seed_terms[:10])
    prompt = (
        "You help expand PubMed search keywords.\n"
        "Task: Given a user's question and some seed terms, propose up to "
        f"{max_new} additional SEARCH TERMS or SHORT PHRASES.\n"
        "Rules:\n"
        "- Output ONLY a newline-separated list of terms (no bullets, no numbering).\n"
        "- No boolean operators (AND/OR/NOT), no brackets, no field tags.\n"
        "- Terms should be plain words/phrases suitable for Title/Abstract search.\n\n"
        f"User question: {user_text}\n"
        f"Seed terms: {seed_preview}\n"
        "Additional terms:\n"
    )

    try:
        resp = client.chat.completions.create(
            model=os.getenv("GROQ_MODEL", "llama-3.1-8b-instant"),
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
            max_tokens=200,
        )
        text = resp.choices[0].message.content or ""
    except Exception:
        return []

    # Parse newline-separated outputs
    raw_lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    cleaned = []
    seen = set(t.lower() for t in seed_terms)

    for ln in raw_lines:
        cand = _clean_candidate(ln)
        if not cand:
            continue
        if cand.lower() in seen:
            continue
        seen.add(cand.lower())
        cleaned.append(cand)
        if len(cleaned) >= max_new:
            break

    return cleaned
