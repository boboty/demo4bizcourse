from __future__ import annotations


VALIDATION_RULE = {
    "correct": [
        "先正常评估 A：汇损＋退税",
        "A 因业务规则被排除后，才允许回退到 B：只有退税",
    ],
    "misunderstood": [
        "同时发现 A 和 B 时，直接优先选择 B",
    ],
    "paths": {
        "A": "汇损＋退税",
        "B": "只有退税",
    },
}

TEST_RESULTS = [
    ("Implementation", "PASS"),
    ("Unit Tests", "PASS"),
    ("Integration Tests", "PASS"),
    ("Regression Tests", "PASS"),
]


def validation_fixture() -> dict[str, object]:
    return {
        "rule": VALIDATION_RULE,
        "tests": list(TEST_RESULTS),
        "final_status": "验收未通过",
        "reason": "实现和测试使用了同一个错误理解。",
    }

