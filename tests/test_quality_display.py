"""User-facing trust labels must separate completion, scope, and data status."""

from web.quality_display import report_trust_display


def test_full_scope_complete_data_gets_five_stars():
    display = report_trust_display({
        "analysis_mode": "full",
        "data_quality_status": "高",
    })

    assert display.completion_label == "已完成"
    assert display.scope_label == "七项分析"
    assert display.data_label == "数据齐全"
    assert display.stars == "★★★★★"
    assert display.confidence_label == "高可信"


def test_fast_scope_complete_data_is_capped_at_four_stars():
    display = report_trust_display({
        "analysis_mode": "fast",
        "data_quality_status": "高",
    })

    assert display.scope_label == "三项速览"
    assert display.data_label == "数据齐全"
    assert display.stars == "★★★★☆"


def test_partial_and_critical_data_have_distinct_labels():
    partial = report_trust_display({
        "analysis_mode": "full",
        "data_quality_status": "中",
    })
    critical = report_trust_display({
        "analysis_mode": "full",
        "data_quality_status": "低",
    })

    assert partial.data_label == "部分数据获取成功"
    assert partial.stars == "★★★☆☆"
    assert critical.data_label == "关键数据缺失"
    assert critical.stars == "★☆☆☆☆"
    assert critical.confidence_label == "无法形成可靠结论"


def test_old_unrated_record_does_not_claim_complete_data():
    display = report_trust_display({"analysis_mode": "full"})

    assert display.data_label == "数据状态未评级"
    assert display.stars == "☆☆☆☆☆"


def test_old_rated_record_uses_legacy_quality_status():
    display = report_trust_display({
        "analysis_mode": "full",
        "data_completeness_status": "unknown",
        "data_quality_status": "高",
        "report_confidence_score": None,
    })

    assert display.data_label == "数据齐全"
    assert display.stars == "★★★★★"


def test_decision_conflict_reduces_report_to_one_star():
    display = report_trust_display({
        "analysis_mode": "full",
        "data_quality_status": "高",
        "decision_validation_status": "blocked_conflict",
    })

    assert display.data_label == "数据齐全"
    assert display.stars == "★☆☆☆☆"
    assert display.confidence_label == "结论校验失败"
