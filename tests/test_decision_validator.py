"""Final decision contract blocks data gaps and rating/action conflicts."""

from tradingagents.agents.decision_validator import validate_final_decision


def test_valid_rating_builds_code_owned_action_guidance():
    result = validate_final_decision({
        "data_quality_status": "高",
        "final_trade_decision": "**Rating**: Hold\n\n**Investment Thesis**: 等待更多信号。",
    })

    assert result["decision_validation_status"] == "valid"
    assert result["validated_decision"]["rating"] == "Hold"
    assert result["validated_decision"]["rating_label"] == "持有"
    assert "维持现有仓位" in result["validated_decision"]["action_guidance"]
    assert result["validated_decision"]["risk_level"] == "中等"
    assert "多空证据较均衡" in result["validated_decision"]["risk_notice"]


def test_rating_and_explicit_action_conflict_is_blocked():
    result = validate_final_decision({
        "data_quality_status": "高",
        "final_trade_decision": "**Rating**: Hold\n\n最终交易指令 决策：卖出",
    })

    assert result["decision_validation_status"] == "blocked_conflict"
    assert result["validated_decision"]["can_show_action"] is False
    assert result["validated_decision"]["reason"] == "评级与操作指令冲突"


def test_missing_or_multiple_rating_is_blocked():
    missing = validate_final_decision({
        "data_quality_status": "高",
        "final_trade_decision": "暂时观望。",
    })
    multiple = validate_final_decision({
        "data_quality_status": "高",
        "final_trade_decision": "Rating: Buy\n最终评级：卖出",
    })

    assert missing["decision_validation_status"] == "blocked_conflict"
    assert multiple["decision_validation_status"] == "blocked_conflict"


def test_low_data_quality_blocks_decision_before_rating_check():
    result = validate_final_decision({
        "data_quality_status": "低",
        "final_trade_decision": "**Rating**: Buy",
    })

    assert result["decision_validation_status"] == "blocked_data"
    assert result["validated_decision"]["rating"] == ""
