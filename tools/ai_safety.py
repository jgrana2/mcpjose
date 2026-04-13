"""Defensive AI safety helpers for prompt risk assessment and safe rewrites."""

from __future__ import annotations

import re
from typing import Any, Dict, List


_RISK_PATTERNS = {
    "coercion": [
        r"\b(or else|otherwise|do it now|immediately|right now)\b",
        r"\bif you don't\b",
        r"\bmust comply\b",
        r"\bno choice\b",
    ],
    "jailbreak": [
        r"\bignore (all|previous|prior) instructions\b",
        r"\bdo anything now\b",
        r"\byou are not bound\b",
        r"\bpretend to be\b",
    ],
    "exfiltration": [
        r"\bapi key\b",
        r"\bpassword\b",
        r"\bsecret\b",
        r"\btoken\b",
        r"\bcredentials\b",
    ],
    "harmful_request": [
        r"\bhack\b",
        r"\bbreak into\b",
        r"\bsteal\b",
        r"\bmalware\b",
        r"\bphish\b",
    ],
}


def assess_prompt_risk(prompt: str) -> Dict[str, Any]:
    """Assess a prompt for manipulative or unsafe patterns."""
    text = prompt or ""
    lowered = text.lower()
    hits: Dict[str, List[str]] = {}
    score = 0

    for category, patterns in _RISK_PATTERNS.items():
        category_hits: List[str] = []
        for pattern in patterns:
            if re.search(pattern, lowered):
                category_hits.append(pattern)
        if category_hits:
            hits[category] = category_hits
            score += len(category_hits)

    level = "low"
    if score >= 5:
        level = "high"
    elif score >= 2:
        level = "medium"

    recommendations = [
        "State the goal directly.",
        "Remove threats, pressure, or instruction conflicts.",
        "Ask for the safest useful alternative if the task is risky.",
    ]
    if "harmful_request" in hits or "exfiltration" in hits:
        recommendations.append("Reframe the request toward defense, detection, or policy.")

    return {
        "risk_level": level,
        "risk_score": score,
        "categories": list(hits.keys()),
        "matched_patterns": hits,
        "recommendations": recommendations,
    }


_SAFE_REWRITE_GUIDANCE = {
    "hacking": "Ask for defensive security guidance, authorized testing, or detection ideas.",
    "coercive": "Use a clear urgency statement without threats or pressure.",
    "prompt_injection": "Ask for safeguards, filters, or evaluation cases instead of exploit steps.",
}


def rewrite_to_safe_alternative(request: str) -> Dict[str, str]:
    """Convert a risky request into a safer alternative."""
    text = (request or "").strip()
    lowered = text.lower()

    if any(word in lowered for word in ["hack", "break into", "steal", "phish", "malware"]):
        suggestion = (
            "Help me design a defensive security test or explain how to harden a system against misuse."
        )
    elif any(word in lowered for word in ["ignore instructions", "jailbreak", "override"]):
        suggestion = "Help me evaluate prompt injection resistance and safe refusal behavior."
    else:
        suggestion = "Rewrite this as a clear, safe, and constructive request."

    return {
        "original_request": text,
        "safe_alternative": suggestion,
        "guidance": _SAFE_REWRITE_GUIDANCE,
    }
