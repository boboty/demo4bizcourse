"""天津货代询价 — the first scenario.

Truthfulness boundary (AGENTS.md):

* The schedule material below is a constructed *teaching fixture*. It is marked
  `teaching_fixture` / `verified=False` everywhere it is rendered, and it must
  never be presented in class as a real carrier publication.
* The rate card is deliberately absent. A quote cannot be produced from the
  materials in this repo, so the chain is expected to stop at
  「报价待业务资料 / 人工确认」 rather than invent a number.
"""

from __future__ import annotations

from .base import Material, Scenario, ToolSpec

REQUEST_TEXT = "天津新港到釜山，下周三货好，两个20GP，帮我看看船期和价格。"

FIXTURE_CAVEAT = (
    "以下内容为课堂教学构造的示例结构，不是承运人发布的真实船期，"
    "不得作为业务事实使用。"
)

SAILING_SCHEDULE_PAYLOAD = {
    "available": True,
    "verified": False,
    "source": "teaching_fixture",
    "caveat": FIXTURE_CAVEAT,
    "queried": {"origin": "天津新港 (Xingang)", "destination": "釜山 (Busan)", "container": "20GP"},
    "entries": [
        {"carrier": "示例承运人甲", "voyage": "FAKE-0001E", "etd": "示例日期", "eta": "示例日期", "verified": False},
        {"carrier": "示例承运人乙", "voyage": "FAKE-0002E", "etd": "示例日期", "eta": "示例日期", "verified": False},
    ],
    "next_step": "真实船期需从承运人官网或订舱平台按航次取回后方可引用。",
}

RATE_CARD_PAYLOAD = {
    "available": False,
    "verified": False,
    "source": "teaching_fixture",
    "reason": "本地没有可核验的报价资料（无承运人报价单、无订舱平台有效期运价）。",
    "next_step": "运价须由业务人员从承运人报价单或订舱平台取得，并确认有效期与附加费。",
}

SPACE_CHECK_PAYLOAD = {
    "available": False,
    "verified": False,
    "source": "teaching_fixture",
    "reason": "舱位需向船公司/订舱口实时确认，本地资料无法给出可用舱位。",
    "next_step": "舱位确认属于人工确认点，不能由模型代替承诺。",
}

TIANJIN_FREIGHT = Scenario(
    key="tianjin-freight",
    name="天津货代询价",
    request_text=REQUEST_TEXT,
    task=(
        "根据客户询价识别已知与缺失条件，取回可核验的船期/报价事实，形成候选方案；"
        "事实不足时明确停在待业务资料或人工确认，不得编造船期、运价或舱位承诺。"
    ),
    known=(
        "起运港：天津新港",
        "目的港：釜山",
        "箱型箱量：20GP × 2",
        "货好时间：下周三（客户口径）",
    ),
    missing=(
        "可核验的有效船期",
        "有效报价资料（运价、附加费、有效期）",
        "舱位确认",
    ),
    human_gates=(
        "报价确认",
        "舱位承诺",
    ),
    next_actions=(
        "向承运人或订舱平台按航次取回真实船期",
        "取回承运人报价单，确认有效期与附加费",
        "向船公司/订舱口实时确认可用舱位",
        "由业务人员完成报价确认与舱位承诺",
    ),
    materials=(
        Material(
            key="sailing_schedule",
            title="船期资料来源说明",
            body=(
                f"{FIXTURE_CAVEAT}\n"
                "本场景可用的船期来源：承运人船期表（需按航次实时取回）、订舱平台航次查询。\n"
                "当前仓库内没有接入任一来源。"
            ),
        ),
        Material(
            key="rate_source",
            title="报价资料来源说明",
            body=(
                "本场景可用的报价来源：承运人报价单、订舱平台有效期运价。\n"
                "两者都未接入；因此任何具体运价数字都无来源，不得写入交付结果。"
            ),
        ),
        Material(
            key="customer_profile",
            title="客户与业务口径",
            body=(
                "客户为长期合作货代客户，询价口径为「船期 + 价格」。\n"
                "人工确认点：报价确认、舱位承诺均由业务人员执行。"
            ),
        ),
    ),
    # 注意这里有三种结果，不是两种：
    #   船期 = 有结果但未核验（teaching_fixture，不能当业务事实用）
    #   运价 = 无结果
    #   舱位 = 无结果
    tools=(
        ToolSpec(
            name="sailing_schedule",
            title="查询船期",
            description="按起运港/目的港/箱型取回船期；此处返回教学构造结构，未经验证。",
            payload=SAILING_SCHEDULE_PAYLOAD,
            available=True,
            verified=False,
            state_note="取回的是教学构造结构（teaching_fixture），没有承运人来源，不能作为业务事实使用。",
        ),
        ToolSpec(
            name="rate_card",
            title="查询运价",
            description="取回承运人报价；本地无可核验报价资料。",
            payload=RATE_CARD_PAYLOAD,
            available=False,
            verified=False,
            state_note="本地没有可核验的报价资料，运价必须由业务人员另行取得。",
        ),
        ToolSpec(
            name="space_check",
            title="确认舱位",
            description="确认可用舱位；需由船公司/订舱口实时确认。",
            payload=SPACE_CHECK_PAYLOAD,
            available=False,
            verified=False,
            state_note="舱位只能由船公司/订舱口实时确认，模型不能代为承诺。",
        ),
    ),
    fact_tools=("sailing_schedule", "rate_card", "space_check"),
    persona="你是一名严谨的天津货代业务助理。",
    output_rules=(
        "只在有可核验来源时给出船期或运价；没有来源就写「待业务资料」，不要给数字。",
        "不得承诺舱位，舱位必须标注为人工确认点。",
        "标注为 teaching_fixture / verified=false 的资料只能作为结构示例引用，不得写成事实。",
        "输出面向客户交付：先给结论与候选方案，再列出缺失条件与下一步动作。",
    ),
)
