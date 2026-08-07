from __future__ import annotations

from copy import deepcopy
from typing import Any


COMPANY = {
    "name": "华启制造有限公司",
    "business": "制造企业",
    "month": "2026年7月",
}

CORE_TRANSACTION = {
    "direction": "收款",
    "amount": "¥58,600.00",
    "payer": "华远商贸有限公司",
    "summary": "货款",
    "date": "2026-07-28",
    "attachment": "无",
    "initial_status": "未找到唯一匹配",
}

UNMATCHED_RECEIVABLES = [
    {"number": "XS-0721-018", "date": "2026-07-21", "amount": "¥32,000"},
    {"number": "XS-0723-006", "date": "2026-07-23", "amount": "¥27,500"},
    {"number": "XS-0725-011", "date": "2026-07-25", "amount": "¥58,600"},
    {"number": "XS-0726-003", "date": "2026-07-26", "amount": "¥14,800"},
]

HISTORICAL_PAYMENTS = [
    {"date": "2026-06-12", "amount": "¥58,600", "result": "核销 XS-0610-009", "evidence": "付款通知"},
    {"date": "2026-06-27", "amount": "¥58,600", "result": "核销 XS-0624-017", "evidence": "业务人员确认"},
    {"date": "2026-07-08", "amount": "¥60,000", "result": "分配至两笔应收", "evidence": "客户对账单"},
]

KNOWLEDGE_SOURCES = [
    {"name": "企业科目表", "detail": "销售回款进入应收账款核销流程"},
    {"name": "客户档案", "detail": "华远商贸有限公司，核心客户"},
    {"name": "内部收款处理规则", "detail": "金额一致不能单独作为核销依据"},
    {"name": "历史凭证", "detail": "相同金额曾对应不同业务"},
    {"name": "未核销应收", "detail": "存在一笔同金额候选 XS-0725-011"},
]

BATCH_ROWS = [
    {"id": "BW-001", "payer": "华远商贸有限公司", "amount": "¥58,600", "status": "待调查", "result": "未找到唯一匹配"},
    {"id": "BW-002", "payer": "华东零部件有限公司", "amount": "¥24,800", "status": "已生成草稿", "result": "销售回款"},
    {"id": "BW-003", "payer": "华启设备服务有限公司", "amount": "¥18,200", "status": "已生成草稿", "result": "服务费"},
    {"id": "BW-004", "payer": "远航物流有限公司", "amount": "¥9,600", "status": "已生成草稿", "result": "物流服务"},
    {"id": "BW-005", "payer": "华南包装有限公司", "amount": "¥12,400", "status": "已生成草稿", "result": "采购退款"},
    {"id": "BW-006", "payer": "新锐电子有限公司", "amount": "¥36,000", "status": "已生成草稿", "result": "销售回款"},
    {"id": "BW-007", "payer": "启明工业有限公司", "amount": "¥15,800", "status": "已生成草稿", "result": "销售回款"},
    {"id": "BW-008", "payer": "盛达贸易有限公司", "amount": "¥8,900", "status": "已生成草稿", "result": "服务费"},
    {"id": "BW-009", "payer": "安泰材料有限公司", "amount": "¥44,000", "status": "已生成草稿", "result": "销售回款"},
    {"id": "BW-010", "payer": "华北工贸有限公司", "amount": "¥21,500", "status": "已生成草稿", "result": "销售回款"},
]

BATCH_SUMMARY = {
    "batch_id": "BW-202607-04",
    "total": 40,
    "drafted": 37,
    "investigating": 3,
    "posted": 0,
}

PERMISSIONS = {
    "allowed": [
        "查询客户档案",
        "查询应收",
        "查询历史凭证和回款",
        "检查附件",
        "生成建议",
        "生成凭证草稿",
        "创建待确认任务",
    ],
    "forbidden": [
        "证据不足时自行分配回款",
        "自动核销存在歧义的应收",
        "修改原始单据",
        "自动过账",
        "代替会计作最终业务判断",
    ],
}


def finance_fixture() -> dict[str, Any]:
    """返回一份可供测试和文档检查使用的完整固定数据快照。"""

    return deepcopy(
        {
            "company": COMPANY,
            "transaction": CORE_TRANSACTION,
            "unmatched_receivables": UNMATCHED_RECEIVABLES,
            "historical_payments": HISTORICAL_PAYMENTS,
            "knowledge_sources": KNOWLEDGE_SOURCES,
            "batch_rows": BATCH_ROWS,
            "batch_summary": BATCH_SUMMARY,
            "permissions": PERMISSIONS,
        }
    )

