import os
import re
from datetime import datetime
from typing import Dict, Tuple, Optional, List
from src.ai_query_expansion import expand_terms_groq
import spacy
from spacy.lang.en.stop_words import STOP_WORDS


_NLP = None

def _get_nlp():
    global _NLP
    if _NLP is None:
        _NLP = spacy.load("en_core_web_sm")
    return _NLP

# Matches common "question framing" prefixes that usually end right before the topic.
# We only strip ONE prefix from the START, never mid-sentence.
_FILLER_PREFIX = re.compile(
    r"""
    ^\s*
    (?:                                       # one of:
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

      | # Curiosity/hedging frames
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

    # Don’t strip if the user starts with a quoted phrase; that’s usually the topic.
    if t.startswith('"'):
        return t

    m = _FILLER_PREFIX.match(t)
    if not m:
        return t

    remainder = t[m.end():].strip()

    # Safety rails:
    if not remainder:
        return t
    if len(remainder) < _MIN_REMAINING_CHARS:
        return t
    # Avoid cascading / weird “can you tell me what is …”
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
    Extract high-signal concept phrases using spaCy noun chunks.
    """
    text = (text or "").strip()
    if not text:
        return []

    # Preserve quoted phrases
    quoted = re.findall(r'"([^"]+)"', text)
    text_wo_quotes = re.sub(r'"[^"]+"', " ", text)

    nlp = _get_nlp()
    doc = nlp(text_wo_quotes)

    QUESTION_OPERATORS = {
        "how", "what", "why", "when", "where", "which",
        "does", "do", "did", "can", "could", "would", "will",
        "affect", "affects", "impact", "influence", "cause",
        "role", "effect", "effects", "association"
    }

    phrases = []

    for chunk in doc.noun_chunks:
        phrase = chunk.text.strip()
        phrase = re.sub(r"^(the|a|an)\s+", "", phrase, flags=re.I)

        if not phrase:
            continue

        tokens = [t.text.lower() for t in chunk if t.is_alpha]
        if not tokens:
            continue

        if tokens[0] in QUESTION_OPERATORS:
            continue

        if all(t in STOP_WORDS for t in tokens):
            continue

        phrases.append(phrase)

    # Merge quoted phrases first
    phrases = quoted + phrases

    # De-duplicate
    seen = set()
    out = []
    for p in phrases:
        key = p.lower()
        if key in seen:
            continue
        seen.add(key)
        out.append(p)

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

    # Explicit date constraints ONLY (conservative)
    start_date, end_date = _extract_year_range(core)
    if not start_date:
        start_date, end_date = _extract_since_year(core)

    # Remove explicit date phrases from topic text to reduce noise
    topic_text = re.sub(r"\bsince\s+\d{4}\b", " ", core, flags=re.IGNORECASE)
    topic_text = re.sub(r"\bfrom\s+\d{4}\s+(to|-)\s+\d{4}\b", " ", topic_text, flags=re.IGNORECASE)

    terms = _tokenize_terms(topic_text)

    # Optional AI expansion: only adds OR terms, never touches filters
    use_ai = os.getenv("USE_AI_EXPANSION", "1").strip() != "0"
    ai_terms: List[str] = []
    if use_ai and terms:
        ai_terms = expand_terms_groq(original, terms, max_new=6)

    # Build topic query: AND between base terms; AI adds OR terms
    if terms:
        base = [f'"{t}"[Title/Abstract]' if " " in t else f"{t}[Title/Abstract]" for t in terms]

        # AI terms are plain phrases; quote multi-word phrases
        extra: List[str] = []
        for t in ai_terms:
            if " " in t:
                extra.append(f'"{t}"[Title/Abstract]')
            else:
                extra.append(f"{t}[Title/Abstract]")

        if extra:
            # Keep base intent (AND) but allow AI to broaden via OR bucket
            # (base AND...) OR (ai OR...)
            topic_query = "(" + " AND ".join(base) + ") OR (" + " OR ".join(extra) + ")"
            pubmed_term = f"({topic_query})"
        else:
            pubmed_term = f"({ ' AND '.join(base) })"
    else:
        # Fallback: if tokenization fails, don't block the user
        pubmed_term = original

    # Apply date filter only if explicitly present
    if start_date and end_date:
        pubmed_term += f' AND ("{_fmt_pdat(start_date)}"[PDAT] : "{_fmt_pdat(end_date)}"[PDAT])'

    debug = {
        "original": original,
        "core_after_filler_strip": core,
        "terms_used": terms,
        "start_date": start_date.isoformat() if start_date else None,
        "end_date": end_date.isoformat() if end_date else None,
        "ai_expansion_enabled": use_ai,
        "ai_added_terms": ai_terms,
        "pubmed_term": pubmed_term,
    }
    return pubmed_term, debug
