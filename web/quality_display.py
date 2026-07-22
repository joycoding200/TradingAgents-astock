"""User-facing analysis scope, data completeness, and trust labels."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


_DATA_STATUS_FROM_QUALITY = {
    "高": "complete",
    "中": "partial",
    "低": "critical_missing",
}

_DATA_LABELS = {
    "complete": "数据齐全",
    "partial": "部分数据获取成功",
    "critical_missing": "关键数据缺失",
    "unknown": "数据状态未评级",
}

_CONFIDENCE_LABELS = {
    5: "高可信",
    4: "较高可信",
    3: "可参考",
    2: "谨慎参考",
    1: "无法形成可靠结论",
    0: "未评级",
}


@dataclass(frozen=True)
class ReportTrustDisplay:
    completion_label: str
    scope_label: str
    data_status: str
    data_label: str
    score: int
    stars: str
    confidence_label: str


def _scope_label(state: dict[str, Any]) -> tuple[str, bool]:
    mode = state.get("analysis_mode", "full")
    selected = state.get("selected_analysts")
    if mode == "fast":
        return "三项速览", False
    if isinstance(selected, list) and selected and len(selected) != 7:
        return f"{len(selected)}项分析", False
    return "七项分析", True


def _derived_score(data_status: str, full_scope: bool) -> int:
    if data_status == "complete":
        return 5 if full_scope else 4
    if data_status == "partial":
        return 3 if full_scope else 2
    if data_status == "critical_missing":
        return 1
    return 0


def report_trust_display(state: dict[str, Any]) -> ReportTrustDisplay:
    """Return consistent, backward-compatible product labels for a result."""
    raw_data_status = str(state.get("data_completeness_status", ""))
    data_status = (
        raw_data_status
        if raw_data_status in {"complete", "partial", "critical_missing"}
        else _DATA_STATUS_FROM_QUALITY.get(state.get("data_quality_status"), "unknown")
    )
    scope_label, full_scope = _scope_label(state)

    raw_score = state.get("report_confidence_score")
    if isinstance(raw_score, int) and 0 <= raw_score <= 5:
        score = raw_score
    else:
        score = _derived_score(data_status, full_scope)
    # Old records do not contain a persisted score. Recompute from their existing
    # quality and mode so a fast analysis can never silently receive five stars.
    if "report_confidence_score" not in state:
        score = _derived_score(data_status, full_scope)

    completion = state.get("analysis_completion_status", "completed")
    completion_label = "已完成" if completion == "completed" else "未完成"
    confidence_label = _CONFIDENCE_LABELS[score]
    if state.get("decision_validation_status") == "blocked_conflict":
        score = 1
        confidence_label = "结论校验失败"
    stars = "★" * score + "☆" * (5 - score)
    return ReportTrustDisplay(
        completion_label=completion_label,
        scope_label=scope_label,
        data_status=data_status,
        data_label=_DATA_LABELS[data_status],
        score=score,
        stars=stars,
        confidence_label=confidence_label,
    )
