"""Deterministic validation contract for the final user-facing decision."""

from __future__ import annotations

import re
from typing import Any

from tradingagents.agents.utils.rating import parse_rating


_RATING_LABELS = {
    "Buy": "买入",
    "Overweight": "偏向买入",
    "Hold": "持有",
    "Underweight": "偏向卖出",
    "Sell": "卖出",
}

_ACTION_GUIDANCE = {
    "Buy": "可以考虑分批买入，但仍要控制投入比例。",
    "Overweight": "整体偏积极，可考虑小幅增加持仓，不宜一次重仓。",
    "Hold": "暂时维持现有仓位；没有持仓的用户先观察。",
    "Underweight": "整体偏谨慎，可考虑降低部分持仓。",
    "Sell": "风险占优，可考虑退出或暂不参与。",
}

_RISK_LEVELS = {
    "Buy": "中等",
    "Overweight": "中等偏高",
    "Hold": "中等",
    "Underweight": "较高",
    "Sell": "高",
}

_RISK_GUIDANCE = {
    "Buy": "倾向买入不代表不会下跌，应分批参与并预留止损空间。",
    "Overweight": "仍有回撤风险，只适合小幅增加仓位。",
    "Hold": "多空证据较均衡，应继续观察关键变化。",
    "Underweight": "不利因素较多，应优先控制亏损和持仓比例。",
    "Sell": "风险因素占优，应优先避免继续扩大损失。",
}

_EXPLICIT_RATING_RE = re.compile(
    r"(?:rating|最终评级|综合评级)\s*[*]*\s*[:：-]\s*[*]*"
    r"(buy|overweight|hold|underweight|sell|买入|偏向买入|持有|偏向卖出|卖出)",
    re.IGNORECASE,
)

_EXPLICIT_ACTION_RE = re.compile(
    r"(?:action|decision|最终交易指令|最终交易建议|交易指令|决策|操作建议)"
    r"\s*[*]*\s*[:：-]\s*[*]*"
    r"(buy|sell|hold|买入|卖出|持有|加仓|减仓|退出|观望)",
    re.IGNORECASE,
)

_CN_TO_RATING = {
    "买入": "Buy",
    "偏向买入": "Overweight",
    "持有": "Hold",
    "偏向卖出": "Underweight",
    "卖出": "Sell",
}

_ACTION_DIRECTION = {
    "buy": "positive",
    "买入": "positive",
    "加仓": "positive",
    "hold": "neutral",
    "持有": "neutral",
    "观望": "neutral",
    "sell": "negative",
    "卖出": "negative",
    "减仓": "negative",
    "退出": "negative",
}

_RATING_DIRECTION = {
    "Buy": "positive",
    "Overweight": "positive",
    "Hold": "neutral",
    "Underweight": "negative",
    "Sell": "negative",
}


def _canonical_rating(value: str) -> str:
    cleaned = value.strip().strip("*")
    if cleaned in _CN_TO_RATING:
        return _CN_TO_RATING[cleaned]
    return cleaned.capitalize()


def validate_final_decision(state: dict[str, Any]) -> dict[str, Any]:
    """Validate data status, one final rating, and explicit action consistency."""
    text = str(state.get("final_trade_decision", ""))
    if state.get("data_quality_status") == "低":
        return {
            "decision_validation_status": "blocked_data",
            "validated_decision": {
                "rating": "",
                "rating_label": "关键数据缺失",
                "action_guidance": "关键数据没有取到，本次不能给出操作结论。",
                "can_show_action": False,
                "risk_notice": "关键数据缺失，无法可靠评估风险。",
                "data_quality_status": "低",
                "reason": "关键数据缺失",
            },
        }

    explicit_ratings = {
        _canonical_rating(match.group(1))
        for match in _EXPLICIT_RATING_RE.finditer(text)
    }
    parsed_rating = parse_rating(text, default="")
    if parsed_rating:
        explicit_ratings.add(parsed_rating)

    if len(explicit_ratings) != 1:
        return {
            "decision_validation_status": "blocked_conflict",
            "validated_decision": {
                "rating": "",
                "rating_label": "结论校验失败",
                "action_guidance": "最终评级缺失或出现多个互相冲突的评级。",
                "can_show_action": False,
                "risk_notice": "结论内部不一致，风险判断不可用。",
                "data_quality_status": state.get("data_quality_status", ""),
                "reason": "最终评级不唯一",
            },
        }

    rating = next(iter(explicit_ratings))
    if rating not in _RATING_LABELS:
        return {
            "decision_validation_status": "blocked_conflict",
            "validated_decision": {
                "rating": "",
                "rating_label": "结论校验失败",
                "action_guidance": "最终评级不在允许的五档范围内。",
                "can_show_action": False,
                "risk_notice": "结论内部不一致，风险判断不可用。",
                "data_quality_status": state.get("data_quality_status", ""),
                "reason": "最终评级无效",
            },
        }

    action_directions = {
        _ACTION_DIRECTION.get(match.group(1).strip().lower())
        for match in _EXPLICIT_ACTION_RE.finditer(text)
    }
    action_directions.discard(None)
    expected_direction = _RATING_DIRECTION[rating]
    if action_directions and action_directions != {expected_direction}:
        return {
            "decision_validation_status": "blocked_conflict",
            "validated_decision": {
                "rating": rating,
                "rating_label": "结论校验失败",
                "action_guidance": "最终评级与明确操作指令不一致，系统已停止展示结论。",
                "can_show_action": False,
                "risk_notice": "评级与操作指令矛盾，风险判断不可用。",
                "data_quality_status": state.get("data_quality_status", ""),
                "reason": "评级与操作指令冲突",
            },
        }

    quality = str(state.get("data_quality_status", ""))
    quality_notice = (
        "部分数据没有取到，不得使用缺失领域作为依据。"
        if quality == "中"
        else "本次范围内的数据已通过完整性检查。"
    )
    risk_notice = f"{_RISK_GUIDANCE[rating]}{quality_notice}"
    return {
        "decision_validation_status": "valid",
        "validated_decision": {
            "rating": rating,
            "rating_label": _RATING_LABELS[rating],
            "action_guidance": _ACTION_GUIDANCE[rating],
            "can_show_action": True,
            "risk_level": _RISK_LEVELS[rating],
            "risk_notice": risk_notice,
            "data_quality_status": quality,
            "reason": "代码校验通过",
        },
    }
