"""Shared 5-tier rating vocabulary and a deterministic heuristic parser.

The same five-tier scale (Buy, Overweight, Hold, Underweight, Sell) is used by:
- The Research Manager (investment plan recommendation)
- The Portfolio Manager (final position decision)
- The signal processor (rating extracted for downstream consumers)
- The memory log (rating tag stored alongside each decision entry)

Centralising it here avoids drift between those call sites.
"""

from __future__ import annotations

import re
from typing import Tuple


# Canonical, ordered 5-tier scale (most bullish to most bearish).
RATINGS_5_TIER: Tuple[str, ...] = (
    "Buy", "Overweight", "Hold", "Underweight", "Sell",
)

_RATING_SET = {r.lower() for r in RATINGS_5_TIER}

# Chinese → English rating mapping (matching the Chinese output_language).
_CHINESE_TO_RATING = {
    "买入": "Buy", "买": "Buy",
    "增持": "Overweight", "超配": "Overweight",
    "持有": "Hold", "观望": "Hold",
    "减持": "Underweight", "低配": "Underweight",
    "卖出": "Sell", "卖": "Sell",
}

# Matches "Rating: X" / "评级：X" / "最终建议：X" — tolerates markdown bold.
_RATING_LABEL_RE = re.compile(
    r"(?:rating|评级|最终建议).*?[:\-][\s*]*(\w+)", re.IGNORECASE
)


def parse_rating(text: str, default: str = "Hold") -> str:
    """Heuristically extract a 5-tier rating from prose text.

    Three-pass strategy:
    1. Look for an explicit rating label (English "Rating:" or Chinese "评级：").
    2. Look for Chinese rating terms (买入/增持/持有/减持/卖出) in text.
    3. Fall back to English 5-tier rating words anywhere in the text.

    Returns a Title-cased English rating string, or ``default`` if none found.
    """
    for line in text.splitlines():
        m = _RATING_LABEL_RE.search(line)
        if m:
            candidate = m.group(1).lower()
            if candidate in _RATING_SET:
                return candidate.capitalize()
            for cn, en in _CHINESE_TO_RATING.items():
                if cn == candidate or cn.startswith(candidate):
                    return en

    for line in text.splitlines():
        for cn, en in _CHINESE_TO_RATING.items():
            if cn in line:
                return en

    for line in text.splitlines():
        for word in line.lower().split():
            clean = word.strip("*:.,")
            if clean in _RATING_SET:
                return clean.capitalize()

    return default
