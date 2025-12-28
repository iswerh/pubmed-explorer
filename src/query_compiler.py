import re
from datetime import datetime
from typing import Dict, Tuple, Optional, List

# Matches common "question framing" prefixes that usually end right before the topic.
# We only strip ONE prefix from the START, never mid-sentence.
_FILLER_PREFIX = re.compile(
    r"""
    ^\s*
    (?:                                       # one leading conversational frame
        # WH-question frames (incl. contractions)
        (?:what(?:'s| is)?|how|why|when|where|which)\b
        (?:[^?.,;:"]{0,80})?
        \b(?:about|on|of|regarding|concerning)\b

      | # Modal/polite frames
        (?:can|could|would|will|may|might)\s+you\b
        (?:[^?.,;:"]{0,80})?
        \b(?:about|on|of|regarding|concerning)\b

      | # Imperative frames
        (?:tell|explain|describe|summarize|outline|show|find|give)\b
        (?:[^?.,;:"]{0,80})?
        \b(?:about|on|of|regarding|concerning)\b

      | # Curiosity/hedging
        i\s*(?:am|'m)\s*(?:curious|wondering|interested)\b
        (?:[^?.,;:"]{0,80})?
        \b(?:about|on|of|regarding|concerning)\b
    )
    \s+
    """,
    re.IGNORECASE | re.VERBOSE,
)

_MIN_REMAINING_CHARS = 6


def _strip_filler(text: str) -> str:
    t = text.strip()

    # Quoted start usually means explicit topic → never strip
    if t.startswith('"'):
        return t

    m = _FILLER_PREFIX.match(t)
    if not m:
        return t

    remainder = t[m.end():].strip()

    # Safety rails
    if not remainder:
        return t

    if len(remainder) < _MIN_REMAINING_CHARS:
        return t

    # If remainder still starts with auxiliary/filler, revert (no cascading)
    if re.match(r"^(what|how|why|when|where|which|can|could|would|will)\b", remainder, re.I):
        return t

    return remainder


def _extract_since_year(text: str) -> Tuple[Optional[datetime], Optional[datetime]]:
    m = re.search(r"\bsince\s+(\d{4})\b", text.lower())
    if not m:
        return None, None
    y = int(m.group(1))
    return datetime(y, 1, 1), datetime.now()

def _extract_year_range(text: str) -> Tuple[Optional[datetime], Optional[datetime]]:
    m = re.search(r"\bfrom\s+(\d{4})\s+(to|-)\s+(\d{4})\b", text.lower())
    if not m:
        return None, None
    y1, y2 = int(m.group(1)), int(m.group(3))
    return datetime(y1, 1, 1), datetime(y2, 12, 31)

def _tokenize_terms(text: str) -> List[str]:
    """
    A lightweight tokenizer that keeps quoted phrases and removes obvious junk.
    This is intentionally simple to avoid overfitting/false constraints.
    """
    # Keep quoted phrases
    phrases = re.findall(r'"([^"]+)"', text)
    tmp = re.sub(r'"[^"]+"', " ", text)

    # Split remaining on punctuation
    words = re.split(r"[\s,;:/()]+", tmp)
    words = [w.strip() for w in words if w.strip()]

    # Remove very short/filler tokens
    stop = {
        "the","a","an","and","or","of","to","in","on","for","with",
        "about","show","find","papers","studies","study","research",
        "recent","latest","new","does","do","we","what","is","are",
        "tell","me","can","you"
    }
    cleaned = []
    for w in words:
        wl = w.lower()
        if wl in stop:
            continue
        if len(wl) <= 2:
            continue
        cleaned.append(w)

    # Add quoted phrases back (as phrases)
    out = [f'"{p}"' for p in phrases] + cleaned
    return out

def _fmt_pdat(d: datetime) -> str:
    return d.strftime("%Y/%m/%d")

def compile_pubmed_query(user_text: str) -> Tuple[str, Dict]:
    """
    Returns:
      pubmed_term: PubMed query string
      debug: extracted parts for optional display
    """
    original = user_text.strip()
    core = _strip_filler(original)

    start_date, end_date = _extract_year_range(core)
    if not start_date:
        start_date, end_date = _extract_since_year(core)

    # Remove date phrases from topic text to reduce noise
    topic_text = re.sub(r"\bsince\s+\d{4}\b", " ", core, flags=re.IGNORECASE)
    topic_text = re.sub(r"\bfrom\s+\d{4}\s+(to|-)\s+\d{4}\b", " ", topic_text, flags=re.IGNORECASE)

    terms = _tokenize_terms(topic_text)
    # Build topic query: AND between terms; quoted phrases get Title/Abstract tag too
    if terms:
        ta_terms = []
        for t in terms:
            # Preserve phrases, but still apply [Title/Abstract]
            if t.startswith('"') and t.endswith('"'):
                ta_terms.append(f'{t}[Title/Abstract]')
            else:
                ta_terms.append(f'{t}[Title/Abstract]')
        topic_query = " AND ".join(ta_terms)
        pubmed_term = f"({topic_query})"
    else:
        pubmed_term = original  # fallback: don't block user

    # Date filter only if explicitly present
    if start_date and end_date:
        pubmed_term += f' AND ("{_fmt_pdat(start_date)}"[PDAT] : "{_fmt_pdat(end_date)}"[PDAT])'

    debug = {
        "original": original,
        "core_after_filler_strip": core,
        "terms_used": terms,
        "start_date": start_date.isoformat() if start_date else None,
        "end_date": end_date.isoformat() if end_date else None,
        "pubmed_term": pubmed_term,
    }
    return pubmed_term, debug
