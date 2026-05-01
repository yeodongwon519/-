from __future__ import annotations

import logging
import re
import unicodedata
from dataclasses import asdict
from pathlib import Path

from autoedit.models import Alignment, ScriptToken, Word

log = logging.getLogger(__name__)

_PUNCT_RE = re.compile(r"[\s\.\,\!\?\;\:\(\)\[\]\{\}\-\—\–\"'`~·…“”‘’]+")
_SENTENCE_SPLIT_RE = re.compile(r"(?<=[\.\!\?])\s+|\n+")


def normalize(s: str) -> str:
    """NFC normalize, lowercase, strip punctuation/whitespace."""
    s = unicodedata.normalize("NFC", s)
    s = s.lower()
    s = _PUNCT_RE.sub("", s)
    return s


def tokenize_script(script: str) -> list[ScriptToken]:
    """Split script into sentence-tagged whitespace tokens, normalized."""
    tokens: list[ScriptToken] = []
    sentences = [s for s in _SENTENCE_SPLIT_RE.split(script) if s.strip()]
    char_offset = 0
    for sentence_idx, sent in enumerate(sentences):
        for raw in sent.split():
            norm = normalize(raw)
            if not norm:
                char_offset += len(raw) + 1
                continue
            tokens.append(ScriptToken(
                text=norm,
                raw=raw,
                sentence_idx=sentence_idx,
                char_offset=char_offset,
            ))
            char_offset += len(raw) + 1
    return tokens


def align(words: list[Word], tokens: list[ScriptToken]) -> Alignment:
    """
    Word-level alignment via similarity-weighted LCS.

    Returns pairs (word_idx, token_idx | None). None means the word has no script
    counterpart (likely a retake/filler/insertion).
    """
    from rapidfuzz.distance import Levenshtein

    n, m = len(words), len(tokens)
    if n == 0 or m == 0:
        return Alignment(pairs=tuple((i, None) for i in range(n)), confidence=0.0)

    norm_words = [normalize(w.text) for w in words]
    norm_tokens = [t.text for t in tokens]

    def sim(wi: int, ti: int) -> float:
        a, b = norm_words[wi], norm_tokens[ti]
        if not a or not b:
            return 0.0
        if a == b:
            return 1.0
        d = Levenshtein.distance(a, b)
        return max(0.0, 1.0 - d / max(len(a), len(b)))

    MATCH_THRESHOLD = 0.6

    # Banded DP to keep memory O(n * band).
    BAND = max(50, min(m, 400))
    INF = float("-inf")
    # Use a dict-of-dicts to be safe; for typical sizes (m<=5000), full table is fine.
    dp = [[INF] * (m + 1) for _ in range(n + 1)]
    bt = [[(0, 0)] * (m + 1) for _ in range(n + 1)]
    for i in range(n + 1):
        dp[i][0] = 0.0
    for j in range(m + 1):
        dp[0][j] = 0.0

    for i in range(1, n + 1):
        # Anchor j-band around the diagonal projection.
        center = int(i * m / n)
        j_lo = max(1, center - BAND)
        j_hi = min(m, center + BAND)
        for j in range(j_lo, j_hi + 1):
            s = sim(i - 1, j - 1)
            best = dp[i - 1][j]
            best_choice = (i - 1, j)
            cand = dp[i][j - 1]
            if cand > best:
                best, best_choice = cand, (i, j - 1)
            if s >= MATCH_THRESHOLD:
                cand = dp[i - 1][j - 1] + s
                if cand > best:
                    best, best_choice = cand, (i - 1, j - 1)
            dp[i][j] = best
            bt[i][j] = best_choice

    # Backtrace from the best end cell on row n.
    j_end = max(range(m + 1), key=lambda j: dp[n][j])
    i, j = n, j_end
    pairs_rev: list[tuple[int, int | None]] = []
    matched = 0
    while i > 0:
        pi, pj = bt[i][j]
        if pi == i - 1 and pj == j - 1:
            pairs_rev.append((i - 1, j - 1))
            matched += 1
        elif pi == i - 1 and pj == j:
            pairs_rev.append((i - 1, None))
        # pj == j - 1 means a script token was skipped; nothing to record per word.
        i, j = pi, pj

    pairs_rev.reverse()
    seen = {p[0] for p in pairs_rev}
    for wi in range(n):
        if wi not in seen:
            pairs_rev.append((wi, None))
    pairs = tuple(sorted(pairs_rev, key=lambda p: p[0]))
    confidence = matched / max(1, n)
    log.info("Alignment: %d/%d words matched (%.1f%%)", matched, n, 100 * confidence)
    return Alignment(pairs=pairs, confidence=confidence)


def save_alignment(alignment: Alignment, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        import json
        json.dump(
            {"pairs": list(alignment.pairs), "confidence": alignment.confidence},
            f, ensure_ascii=False, indent=2,
        )


def load_alignment(path: Path) -> Alignment:
    import json
    with open(path, encoding="utf-8") as f:
        raw = json.load(f)
    pairs = tuple((int(a), (int(b) if b is not None else None)) for a, b in raw["pairs"])
    return Alignment(pairs=pairs, confidence=float(raw["confidence"]))


def save_tokens(tokens: list[ScriptToken], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        import json
        json.dump([asdict(t) for t in tokens], f, ensure_ascii=False, indent=2)


def load_tokens(path: Path) -> list[ScriptToken]:
    import json
    with open(path, encoding="utf-8") as f:
        return [ScriptToken(**t) for t in json.load(f)]
