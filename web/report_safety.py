"""Code-enforced safety rules for the user-facing report.

The saved graph state retains the original analyst discussion for auditing. It
must not be presented as an actionable report when a critical data request
failed.
"""

from __future__ import annotations

from typing import Any


DATA_INCOMPLETE_SIGNAL = "DataIncomplete"
DECISION_INVALID_SIGNAL = "DecisionInvalid"
DATA_INCOMPLETE_NOTICE = (
    "本次关键数据没有取到，系统不提供买入、卖出、价格或投入比例建议。"
    "请稍后重新分析，等数据完整后再看结论。"
)
DECISION_INVALID_NOTICE = (
    "最终评级与操作内容未通过代码一致性检查，系统已停止展示投资结论。"
    "内部分析仍保留用于排查，请重新分析后再查看。"
)


def is_data_limited(final_state: dict[str, Any]) -> bool:
    """Whether code-level quality checks prohibit actionable presentation."""
    return (
        final_state.get("data_quality_status") == "低"
        or final_state.get("decision_validation_status")
        in {"blocked_data", "blocked_conflict"}
    )


def limitation_notice(final_state: dict[str, Any]) -> str:
    if final_state.get("decision_validation_status") == "blocked_conflict":
        return DECISION_INVALID_NOTICE
    return DATA_INCOMPLETE_NOTICE


def display_signal(final_state: dict[str, Any], signal: str) -> str:
    """Return the only signal allowed in the product UI and exports."""
    if final_state.get("data_quality_status") == "低":
        return DATA_INCOMPLETE_SIGNAL
    if final_state.get("decision_validation_status") == "blocked_conflict":
        return DECISION_INVALID_SIGNAL
    return signal


def signal_label(signal: str) -> str:
    """Map internal five-tier ratings to short, plain Chinese labels."""
    labels = {
        "BUY": "买入",
        "OVERWEIGHT": "偏向买入",
        "HOLD": "持有",
        "UNDERWEIGHT": "偏向卖出",
        "SELL": "卖出",
        "DATAINCOMPLETE": "关键数据缺失",
        "DECISIONINVALID": "结论校验失败",
    }
    return labels.get(str(signal).replace("_", "").upper(), "暂无法判断")
