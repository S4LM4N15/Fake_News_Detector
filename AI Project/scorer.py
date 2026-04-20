"""
scorer.py — Multi-signal fake-news scoring engine.

Signals
-------
1. Trusted domain found          → +40 pts
2. Multiple sources (≥2)         → +20 pts
3. Recent publication (≤30 days) → +20 pts
4. Headline keyword match ≥60%   → +20 pts

Verdict
-------
80–100 → REAL
50–79  → LIKELY_REAL
<50    → FAKE
"""

import re
import difflib
from datetime import datetime, timedelta
from urllib.parse import urlparse
from dateutil import parser as dateparser

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

TRUSTED_DOMAINS = {
    "bbc.com", "bbc.co.uk",
    "reuters.com",
    "apnews.com",
    "nytimes.com",
    "theguardian.com",
    "prothomalo.com",
    "thedailystar.net",
    "aljazeera.com",
    "cnn.com",
    "nbcnews.com",
    "washingtonpost.com",
    "bloomberg.com",
    "npr.org",
    "time.com",
    "forbes.com",
    "economist.com",
    "ft.com",
    "abc.net.au",
    "cbsnews.com",
    "abcnews.go.com",
    "usatoday.com",
    "thehill.com",
    "politico.com",
    "axios.com",
    "sciencedaily.com",
    "nature.com",
    "scientificamerican.com",
}

RECENCY_DAYS = 30


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def calculate_score(query: str, results: list[dict]) -> dict:
    """
    Run all four signals and return a structured result dict.

    Returns
    -------
    {
        score: int (0–100),
        verdict: "REAL" | "LIKELY_REAL" | "FAKE",
        verdict_label: str,
        verdict_emoji: str,
        breakdown: { signal_name: { points, max, passed, detail } },
        matched_sources: [ {title, url, domain, is_trusted, date} ],
    }
    """
    breakdown = {}
    matched_sources = []

    # ── Signal 1: Trusted domain ──────────────────────────────────────────
    trusted_hits = []
    for r in results:
        domain = r.get("true_domain") or _get_domain(r.get("url", ""))
        is_trusted = _is_trusted(domain)
        entry = {
            "title": r.get("title", ""),
            "url": r.get("url", ""),
            "domain": domain,
            "is_trusted": is_trusted,
            "date": r.get("date"),
            "snippet": r.get("snippet", ""),
        }
        matched_sources.append(entry)
        if is_trusted:
            trusted_hits.append(entry)

    s1_passed = len(trusted_hits) > 0
    breakdown["trusted_domain"] = {
        "label": "Found on trusted domain",
        "points": 40 if s1_passed else 0,
        "max": 40,
        "passed": s1_passed,
        "detail": (
            f"Matched: {', '.join(h['domain'] for h in trusted_hits[:3])}"
            if s1_passed else "No trusted domains found"
        ),
    }

    # ── Signal 2: Multiple sources ────────────────────────────────────────
    unique_domains = {r.get("true_domain") or _get_domain(r.get("url", "")) for r in results if r.get("url")}
    s2_passed = len(unique_domains) >= 2
    breakdown["multiple_sources"] = {
        "label": "Multiple sources reporting",
        "points": 20 if s2_passed else 0,
        "max": 20,
        "passed": s2_passed,
        "detail": f"{len(unique_domains)} unique source(s) found",
    }

    # ── Signal 3: Recent publication ──────────────────────────────────────
    recent_count = 0
    cutoff = datetime.now() - timedelta(days=RECENCY_DAYS)
    for r in results:
        parsed_date = _parse_date(r.get("date"))
        if parsed_date and parsed_date >= cutoff:
            recent_count += 1

    s3_passed = recent_count > 0
    breakdown["recent_publication"] = {
        "label": f"Recent publication (≤{RECENCY_DAYS} days)",
        "points": 20 if s3_passed else 0,
        "max": 20,
        "passed": s3_passed,
        "detail": (
            f"{recent_count} article(s) within last {RECENCY_DAYS} days"
            if s3_passed else "No recent publication dates detected"
        ),
    }

    # ── Signal 4: Headline keyword match ─────────────────────────────────
    best_similarity = 0.0
    query_clean = _clean_text(query)
    for r in results:
        title_clean = _clean_text(r.get("title", ""))
        sim = difflib.SequenceMatcher(None, query_clean, title_clean).ratio()
        if sim > best_similarity:
            best_similarity = sim

    s4_passed = best_similarity >= 0.40
    breakdown["headline_match"] = {
        "label": "Headline matches claim",
        "points": 20 if s4_passed else 0,
        "max": 20,
        "passed": s4_passed,
        "detail": f"Best keyword similarity: {best_similarity:.0%}",
    }

    # ── Total score & verdict ─────────────────────────────────────────────
    score = sum(v["points"] for v in breakdown.values())
    verdict, verdict_label, verdict_emoji, verdict_color = _get_verdict(score)

    return {
        "score": score,
        "verdict": verdict,
        "verdict_label": verdict_label,
        "verdict_emoji": verdict_emoji,
        "verdict_color": verdict_color,
        "breakdown": breakdown,
        "matched_sources": matched_sources[:8],   # cap at 8 for UI
        "total_results_found": len(results),
    }


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_domain(url: str) -> str:
    try:
        host = urlparse(url).netloc.lower()
        return host.removeprefix("www.")
    except Exception:
        return ""


def _is_trusted(domain: str) -> bool:
    if not domain:
        return False
    for td in TRUSTED_DOMAINS:
        if domain == td or domain.endswith("." + td):
            return True
    return False


def _clean_text(text: str) -> str:
    text = text.lower()
    text = re.sub(r"[^\w\s]", " ", text)
    stopwords = {"a", "an", "the", "is", "in", "on", "at", "to", "of",
                 "and", "or", "for", "with", "by", "that", "this", "are"}
    tokens = [w for w in text.split() if w not in stopwords and len(w) > 1]
    return " ".join(tokens)


def _parse_date(date_str: str | None) -> datetime | None:
    if not date_str:
        return None
    try:
        dt = dateparser.parse(date_str, fuzzy=True)
        return dt.replace(tzinfo=None)
    except Exception:
        return None


def _get_verdict(score: int) -> tuple[str, str, str, str]:
    if score >= 80:
        return "REAL", "Real News", "✅", "#22c55e"
    elif score >= 50:
        return "LIKELY_REAL", "Likely Real", "⚠️", "#f59e0b"
    else:
        return "FAKE", "Unverified / Fake", "❌", "#ef4444"
