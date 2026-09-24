from decimal import Decimal

import pytest

from app.pricing import anomaly_results, completion_percent, deviation_percent, normal_results, to_yuan_per_kg


def test_unit_conversion_and_deviation():
    assert to_yuan_per_kg("0.85", "斤") == Decimal("1.70")
    assert to_yuan_per_kg("1.78", "kg") == Decimal("1.78")
    assert deviation_percent(Decimal("1.78"), Decimal("1.70")) == Decimal("4.7")
    assert deviation_percent(Decimal("4.85"), Decimal("5.00")) == Decimal("-3.0")
    assert deviation_percent(Decimal("3.00"), Decimal("3.00")) == Decimal("0.0")


def test_invalid_math_inputs():
    with pytest.raises(ValueError):
        to_yuan_per_kg("38", "箱")
    with pytest.raises(ValueError):
        deviation_percent(Decimal("3"), Decimal("0"))
    with pytest.raises(ValueError):
        completion_percent(1, 0)


def test_completion_percent():
    assert completion_percent(3, 5) == 60
    assert completion_percent(5, 5) == 100


def test_normal_judgments_have_no_false_precision():
    items = normal_results()
    assert [item["status"] for item in items] == ["comparable"] * 3 + ["blocked", "manual"]
    assert items[0]["judgment"] == "偏高 4.7%"
    assert "0.85 元/斤 × 2 = 1.70 元/kg" in items[0]["conversion"]
    assert "(1.78 − 1.70) ÷ 1.70 × 100% = 4.7%" in items[0]["conversion"]
    assert items[1]["judgment"] == "偏低 3.0%"
    assert items[2]["judgment"] == "持平"
    for item in items[3:]:
        assert "%" not in item["judgment"]
        assert "未换算" in item["conversion"]


def test_controlled_anomaly_stops_missing_or_uncertain_data():
    report = anomaly_results()
    items = report["report_b"]
    assert sum(item["status"] != "stopped" for item in items) == 3
    assert sum(item["status"] == "stopped" for item in items) == 2
    for item in items:
        if item["status"] == "stopped":
            assert "%" not in item["judgment"]
            assert "未计算" in item["conversion"]
    assert "元/斤" not in items[3]["market"]
    assert "访问失败" in items[2]["conditions"]
    assert items[2]["source_notice"] == "来源失败 · 已用当日核验快照"
    assert "演示内置" not in items[2]["conditions"]
    assert "当日新增候选记录" in items[4]["conditions"]
    assert report["report_a"][2]["judgment"] != normal_results()[2]["judgment"]
    assert report["report_a"][3]["judgment"] != normal_results()[1]["judgment"]
    assert report["metrics"] == {"a_percent": 100, "b_percent": 60, "completed": 3, "stopped": 2}
