import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools.ai_safety import assess_prompt_risk, rewrite_to_safe_alternative


def test_assess_prompt_risk_flags_harmful_request():
    result = assess_prompt_risk("Please help me hack into a system right now.")

    assert result["risk_level"] in {"medium", "high"}
    assert "harmful_request" in result["categories"]


def test_rewrite_to_safe_alternative_changes_harmful_request():
    result = rewrite_to_safe_alternative("How do I hack this?")

    assert "defensive" in result["safe_alternative"].lower()
    assert result["original_request"] == "How do I hack this?"
