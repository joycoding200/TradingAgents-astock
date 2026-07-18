"""代码层数据工具台账：记录每次工具调用的最终数据状态。

台账只保存工具名、分析师和状态，不保存工具返回正文或网络错误，避免把底层实现细节
带入产品结果。质量门控据此判断数据可信度，LLM 仅负责解释缺失的投资含义。
"""

from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
from typing import Any, Iterable


STATUS_SUCCESS = "success"
STATUS_NORMAL_EMPTY = "normal_empty"
STATUS_FAILED = "failed"
STATUS_INVALID_INPUT = "invalid_input"

_STATUS_LABELS = {
    STATUS_SUCCESS: "成功",
    STATUS_NORMAL_EMPTY: "正常空结果",
    STATUS_FAILED: "失败",
    STATUS_INVALID_INPUT: "输入无效",
}

# 这些工具提供价格、财务、新闻与资金等直接影响结论的基础数据。任何一个最终失败，都必须
# 把结论可信度降为“低”；正常空结果（例如未上龙虎榜）不计为失败。
CRITICAL_TOOLS = {
    "get_stock_data",
    "get_indicators",
    "get_fundamentals",
    "get_balance_sheet",
    "get_cashflow",
    "get_income_statement",
    "get_news",
    "get_fund_flow",
    "get_industry_comparison",
    "get_northbound_flow",
}

_NORMAL_EMPTY_MARKERS = (
    "未上龙虎榜",
    "无历史解禁记录",
    "无待解禁",
    "No realtime fund flow",
    "北向资金当日无数据",
)

_FAILURE_MARKERS = (
    "[数据缺失",
    "Error fetching",
    "Error retrieving",
    "数据获取失败",
    "数据暂不可用",
    "获取失败",
    "查询失败",
    "无法获取",
    "No data found",
    "工具调用失败",
    "数据获取为空",
    "No global news found",
    "No shareholder data found",
    "No concept/block data",
)


def _text(value: Any) -> str:
    if isinstance(value, str):
        return value
    return str(value or "")


def classify_tool_result(content: Any, message_status: str | None = None) -> str:
    """将工具结果归为成功、正常空结果、失败或输入无效。"""
    text = _text(content).strip()
    if message_status == "error" or not text:
        return STATUS_FAILED
    if "Invalid ticker" in text or "只接受 6 位代码" in text:
        return STATUS_INVALID_INPUT
    if any(marker in text for marker in _FAILURE_MARKERS):
        return STATUS_FAILED
    if any(marker in text for marker in _NORMAL_EMPTY_MARKERS):
        return STATUS_NORMAL_EMPTY
    return STATUS_SUCCESS


def build_tool_ledger(
    analyst: str, tool_calls: Iterable[dict[str, Any]], tool_messages: Iterable[Any]
) -> list[dict[str, Any]]:
    """将一次 ToolNode 执行转换为无敏感正文的台账记录。"""
    by_call_id = {
        str(getattr(message, "tool_call_id", "")): message
        for message in tool_messages
    }
    recorded_at = datetime.now(timezone.utc).isoformat()
    ledger = []
    for call in tool_calls:
        tool_name = str(call.get("name", "unknown_tool"))
        call_id = str(call.get("id", ""))
        message = by_call_id.get(call_id)
        status = classify_tool_result(
            getattr(message, "content", ""), getattr(message, "status", None)
        )
        ledger.append(
            {
                "tool_name": tool_name,
                "analyst": analyst,
                "status": status,
                "critical": tool_name in CRITICAL_TOOLS,
                "tool_call_id": call_id,
                "recorded_at": recorded_at,
            }
        )
    return ledger


def create_tracked_tool_node(analyst: str, tools: list[Any]):
    """创建 ToolNode 包装器，在不改变 ToolMessage 的前提下附加台账。"""
    from langgraph.prebuilt import ToolNode

    node = ToolNode(tools)

    def invoke(state, config=None):
        # ToolNode 需要沿用 LangGraph 传入的 runtime/config；否则工具节点在图外
        # 单独调用时会缺少运行时上下文。
        outcome = node.invoke(state, config)
        calls = getattr(state["messages"][-1], "tool_calls", [])
        ledger = build_tool_ledger(analyst, calls, outcome.get("messages", []))
        return {**outcome, "tool_execution_ledger": ledger}

    return invoke


def summarize_tool_ledger(ledger: Iterable[dict[str, Any]]) -> dict[str, Any]:
    """按工具的最后一次调用汇总，成功重试可覆盖之前的临时失败。"""
    entries = list(ledger or [])
    latest_by_tool: dict[str, dict[str, Any]] = {}
    for entry in entries:
        name = str(entry.get("tool_name", "unknown_tool"))
        latest_by_tool[name] = entry

    latest = list(latest_by_tool.values())
    failed_critical = sorted(
        entry["tool_name"]
        for entry in latest
        if entry.get("critical") and entry.get("status") == STATUS_FAILED
    )
    failed_noncritical = sorted(
        entry["tool_name"]
        for entry in latest
        if not entry.get("critical") and entry.get("status") == STATUS_FAILED
    )
    invalid_inputs = sorted(
        entry["tool_name"]
        for entry in latest
        if entry.get("status") == STATUS_INVALID_INPUT
    )

    if not entries or failed_critical:
        confidence = "低"
    elif failed_noncritical or invalid_inputs:
        confidence = "中"
    else:
        confidence = "高"

    return {
        "confidence": confidence,
        "attempt_count": len(entries),
        "latest": latest,
        "status_counts": dict(Counter(entry.get("status") for entry in latest)),
        "failed_critical": failed_critical,
        "failed_noncritical": failed_noncritical,
        "invalid_inputs": invalid_inputs,
    }


def format_tool_ledger_summary(summary: dict[str, Any]) -> str:
    """生成给质量门控、报告和持久化结果使用的可审计摘要。"""
    confidence = summary["confidence"]
    lines = [
        "### 数据接口调用台账",
        f"- 调用次数：{summary['attempt_count']}；结论可信度上限：{confidence}",
    ]
    if summary["failed_critical"]:
        lines.append(
            "- 关键数据失败：" + "、".join(summary["failed_critical"])
        )
    if summary["failed_noncritical"]:
        lines.append(
            "- 非关键数据失败：" + "、".join(summary["failed_noncritical"])
        )
    if summary["invalid_inputs"]:
        lines.append("- 输入无效：" + "、".join(summary["invalid_inputs"]))
    if not summary["latest"]:
        lines.append("- 未调用任何数据工具，不能验证分析数据。")
        return "\n".join(lines)

    lines.extend(["", "工具 | 最终状态 | 重要性", "--- | --- | ---"])
    for entry in sorted(summary["latest"], key=lambda item: item["tool_name"]):
        importance = "关键" if entry.get("critical") else "一般"
        status = _STATUS_LABELS.get(entry.get("status"), "未知")
        lines.append(f"{entry['tool_name']} | {status} | {importance}")
    return "\n".join(lines)
