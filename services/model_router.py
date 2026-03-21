from __future__ import annotations

from typing import Optional, Tuple

KEYWORDS_FORCE_4O = {"think", "deep", "analyze", "critique", "rigor", "theoretical"}


def estimate_tokens(text: str) -> int:
    return max(1, len(text) // 4)


def select_model(
    *,
    rubric_id: str,
    document_text: str,
    user_text: Optional[str] = None,
    grammar_only: bool = False,
) -> Tuple[str, str, int]:
    merged = f"{document_text}\n{user_text or ''}".lower()
    token_estimate = estimate_tokens(merged)

    if rubric_id == "phd_unified_meta_v3" and not grammar_only:
        return "gpt-4o", "doctoral rubric requires gpt-4o", token_estimate

    if any(word in merged for word in KEYWORDS_FORCE_4O):
        return "gpt-4o", "keyword-triggered escalation", token_estimate

    if token_estimate > 1800:
        return "gpt-4o", "length/token heuristic escalation", token_estimate

    return "gpt-4o-mini", "default short/simple routing", token_estimate
