"""Regression tests for user-facing report safety and final signal selection."""

from web.history import extract_signal
from web.pdf_export import generate_markdown
from web.report_safety import DATA_INCOMPLETE_NOTICE


def test_history_uses_final_rating_not_earlier_research_opinion():
    state = {
        "investment_plan": "**Rating**: Hold",
        "trader_investment_decision": "**Rating**: Hold",
        "final_trade_decision": "**Rating**: Sell",
    }

    assert extract_signal(state) == "Sell"


def test_history_preserves_five_tier_final_rating_and_low_quality_override():
    state = {"final_trade_decision": "**Rating**: Underweight"}
    assert extract_signal(state) == "Underweight"

    state["data_quality_status"] = "低"
    assert extract_signal(state) == "DataIncomplete"


def test_history_uses_validated_rating_and_blocks_conflicting_decision():
    valid = {
        "decision_validation_status": "valid",
        "validated_decision": {"rating": "Underweight"},
        "final_trade_decision": "**Rating**: Buy",
    }
    conflict = {
        "decision_validation_status": "blocked_conflict",
        "final_trade_decision": "**Rating**: Hold\n决策：卖出",
    }

    assert extract_signal(valid) == "Underweight"
    assert extract_signal(conflict) == "DecisionInvalid"


def test_low_quality_markdown_hides_actionable_internal_reports(monkeypatch):
    monkeypatch.setattr("web.pdf_export.stock_display_label", lambda ticker, state: ticker)
    monkeypatch.setattr("web.pdf_export.normalize_stock_mentions", lambda text, ticker, state: text)
    state = {
        "data_quality_status": "低",
        "market_report": "建议立刻买入，目标价 100 元。",
        "final_trade_decision": "**Rating**: Sell\n立即卖出，止损价 80 元。",
        "data_quality_summary": "关键数据失败：资金流向",
    }

    markdown = generate_markdown(state, "600879", "2026-07-18", "Sell")

    assert "交易信号**：**关键数据缺失" in markdown
    assert DATA_INCOMPLETE_NOTICE in markdown
    assert "立即卖出" not in markdown
    assert "目标价 100" not in markdown


def test_decision_conflict_markdown_hides_actionable_internal_reports(monkeypatch):
    monkeypatch.setattr("web.pdf_export.stock_display_label", lambda ticker, state: ticker)
    monkeypatch.setattr("web.pdf_export.normalize_stock_mentions", lambda text, ticker, state: text)
    state = {
        "data_quality_status": "高",
        "decision_validation_status": "blocked_conflict",
        "market_report": "建议立即买入。",
        "final_trade_decision": "**Rating**: Hold\n最终交易指令 决策：卖出",
    }

    markdown = generate_markdown(state, "600879", "2026-07-18", "Sell")

    assert "交易信号**：**结论校验失败" in markdown
    assert "停止展示投资结论" in markdown
    assert "建议立即买入" not in markdown
    assert "决策：卖出" not in markdown


def test_markdown_leads_with_code_validated_action_and_marks_model_text_as_evidence(
    monkeypatch,
):
    monkeypatch.setattr("web.pdf_export.stock_display_label", lambda ticker, state: ticker)
    monkeypatch.setattr(
        "web.pdf_export.normalize_stock_mentions", lambda text, ticker, state: text
    )
    state = {
        "analysis_mode": "full",
        "data_quality_status": "高",
        "data_completeness_status": "complete",
        "decision_validation_status": "valid",
        "validated_decision": {
            "rating": "Hold",
            "rating_label": "持有",
            "action_guidance": "暂时维持现有仓位。",
            "risk_level": "中等",
            "risk_notice": "多空证据较均衡。",
        },
        "final_trade_decision": "**Rating**: Hold\n模型详细分析。",
    }

    markdown = generate_markdown(state, "600519", "2026-07-17", "Hold")

    assert "## 代码校验后的结论" in markdown
    assert "操作倾向：暂时维持现有仓位" in markdown
    assert "风险程度：中等" in markdown
    assert "## 模型结论依据（不作为操作指令）" in markdown


def test_normal_markdown_uses_chinese_five_tier_signal(monkeypatch):
    monkeypatch.setattr("web.pdf_export.stock_display_label", lambda ticker, state: ticker)
    markdown = generate_markdown({}, "600879", "2026-07-18", "Underweight")
    assert "交易信号**：**偏向卖出" in markdown


def test_medium_quality_keeps_conclusion_and_exports_scope_limits(monkeypatch):
    monkeypatch.setattr("web.pdf_export.stock_display_label", lambda ticker, state: ticker)
    monkeypatch.setattr("web.pdf_export.normalize_stock_mentions", lambda text, ticker, state: text)
    state = {
        "data_quality_status": "中",
        "data_quality_constraints": "不能判断主力资金流入或流出。",
        "final_trade_decision": "**Rating**: Hold\n结合现有数据暂时持有。",
    }

    markdown = generate_markdown(state, "600879", "2026-07-17", "Hold")

    assert "交易信号**：**持有" in markdown
    assert "结合现有数据暂时持有" in markdown
    assert "不能判断主力资金流入或流出" in markdown
