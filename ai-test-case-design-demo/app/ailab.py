"""AI 实验：为 Demo 3～6 生成可直接复制到外部 AI 对话的完整提示词，并把粘贴回来的输出与本地确定性结果比较。

本模块不调用任何 LLM。提示词全部由本地业务资产拼装，自带所需数据；解析只做稳定标记行与 ID 提取，
失败时返回明确提示而不抛错。冻结资产与确定性算法本身不被修改。
"""
import json
import re
from decimal import Decimal, InvalidOperation
from typing import Any, Dict, List, Optional, Tuple

from app.assets import load
from app.engine import calculate_finance_refund, execute_v1_0_cases
from app.migration import build_migration
from app.selection import MANUAL_SCENARIO_ID, PROTECTED_SCENARIO_IDS, SUPPORTED_BUDGETS, select_scenarios

PROMPT_KINDS = ("d3_select", "d4_eval1", "d4_eval2", "d5_review1", "d5_review2", "d6_impact")
MAX_TEXT = 60000
EVIDENCE_LABEL = {"fact": "事实", "inference": "推断", "missing": "缺失", "conflict": "冲突",
                  "independent_source": "独立来源"}
VALIDITY_LABEL = {"candidate": "候选", "needs_confirmation": "待确认"}
ACTION_WORDS = (("作废", "obsolete"), ("废弃", "obsolete"), ("obsolete", "obsolete"),
                ("修改", "modify"), ("更新", "modify"), ("modify", "modify"),
                ("保留", "retain"), ("不变", "retain"), ("retain", "retain"), ("keep", "retain"))
MARKER_NAMES = ("FINAL_SELECTION", "EXPECTATIONS", "CLASSIC_B_REFUND", "EVIDENCE_USED", "CONCLUSION_REVISED",
                "AFFECTED_RULES", "AFFECTED_SCENARIOS", "NEW_CASE_COUNT")


def _compact(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


# ───────────────────────── 通用：标记行与数字解析 ─────────────────────────

def parse_markers(text: str) -> Dict[str, str]:
    """提取 `KEY=value` / `KEY: value` 形式的标记行（容忍 markdown 修饰；同名取最后一次）。"""
    found = {}  # type: Dict[str, str]
    for line in (text or "").splitlines():
        cleaned = re.sub(r"[`*>#|]", " ", line).strip()
        match = re.match(r"^(?:[-•]\s*)?([A-Z][A-Z_]{3,40})\s*[=:：]\s*(.+?)\s*$", cleaned)
        if match and match.group(1) in MARKER_NAMES:
            found[match.group(1)] = match.group(2).strip().strip("<>[]")
    return found


def _amount(raw: Optional[str]) -> Optional[str]:
    if raw is None:
        return None
    match = re.search(r"-?\d+(?:\.\d+)?", raw.replace(",", ""))
    if not match:
        return None
    try:
        return str(Decimal(match.group(0)).quantize(Decimal("0.01")))
    except InvalidOperation:
        return None


def _split_ids(raw: str, pattern: str) -> List[str]:
    seen = []  # type: List[str]
    for token in re.findall(pattern, raw or ""):
        if token not in seen:
            seen.append(token)
    return seen


# ───────────────────────── 共用材料块 ─────────────────────────

def _prd_block() -> str:
    prd = load("prd/prd_v1_0.json")
    lines = ["《%s》（V%s）" % (prd["title"], prd["version"])]
    lines += ["%s：%s" % (p["source_id"], p["text"]) for p in prd["paragraphs"]]
    lines.append("待确认事项（尚未确定，不能当作正式规则）：")
    lines += ["%s：%s" % (q["question_id"], q["text"]) for q in prd["open_questions"]]
    return "\n".join(lines)


def _case_line(case: Dict[str, Any]) -> str:
    data = case["input"]
    items = "、".join("%s=%s" % (i["sku"], i["gross"]) for i in data["items"])
    promo = data.get("promotion") or {}
    promo_text = ("满%s减%s（已启用）" % (promo.get("threshold"), promo.get("discount"))
                  if promo.get("enabled") else "无满减优惠")
    return "%s｜%s｜商品原价 %s｜%s｜原订单优惠 %s｜实付 %s｜退货SKU %s｜测试预期退款 %s" % (
        case["case_id"], case["title"], items, promo_text, data["original_discount"], data["paid"],
        "、".join(data["return_skus"]), case["expected"]["refund"])


def _executed() -> Tuple[Dict[str, Any], Dict[str, Any]]:
    fixture = load("cases/v1_0_executable.json")
    return fixture, execute_v1_0_cases(fixture)


def _test_material_block() -> str:
    fixture, report = _executed()
    basis = fixture["cases"][0]["expected"]["basis"]
    lines = ["【测试假设（测试编写方给出，所有用例通用）】",
             "预期口径：" + basis,
             "优惠假设：" + fixture["promotion_policy"],
             "舍入：四舍五入到分。",
             "",
             "【20条金额用例】（ID｜标题｜输入｜测试预期）"]
    lines += [_case_line(c) for c in fixture["cases"]]
    lines += ["", "【实际执行证据（对被测实现真实运行的结果）】",
              "共 %d 条，通过 %d 条，失败 %d 条。" % (report["total"], report["passed"], report["failed"]),
              "ID｜结果｜实际退款｜测试预期退款"]
    for row in report["cases"]:
        lines.append("%s｜%s｜%s｜%s" % (row["case_id"], "PASS" if row["passed"] else "FAIL",
                                       row["actual"]["refund"], row["expected"]["refund"]))
    return "\n".join(lines)


def _finance_block(review_hint: str) -> str:
    finance = load("finance/after_sales_funds.json")
    lines = ["【补充材料：独立财务规范（YS-FIN-AFTERSALES-01，由财务部门维护，独立于测试编写方的业务来源）】"]
    lines += ["%s：%s" % (rule["rule_id"], rule["text"]) for rule in finance["rules"]]
    lines.append(review_hint)
    return "\n".join(lines) + "\n\n"


def _review_format(recompute: bool = False) -> str:
    lines = [
        "【输出格式】",
        "1. 先列出发现（不超过6条）。每条必须写明“依据：<材料编号或原文>”或“无法确认：<缺少什么证据>”，"
        "把“材料能证明的结论”和“只能当作假设的内容”分开写，不要把假设写成事实，也不要为了显得有发现而编造问题。",
    ]
    if recompute:
        lines.append("2. 复算区块：以“RECOMPUTE:”独占一行开头，随后 TC01 到 TC20 每条一行，格式 TC01=<金额>。"
                     "金额为按财务规范独立计算、两位小数；若公式结果为负数，写 REVIEW。")
    lines.append("%d. 全文最后，单独各占一行输出下面%s行（等号后只写一个值，不要加解释）：" % (3 if recompute else 2, "四" if recompute else "三"))
    lines += [
        "EXPECTATIONS=<SUPPORTED|UNSUPPORTED|CONTRADICTED>   （SUPPORTED=所给材料足以证明这些预期金额正确；"
        "UNSUPPORTED=材料不足以证明；CONTRADICTED=所给材料证明预期金额有错）",
        "CLASSIC_B_REFUND=<金额，两位小数；仅凭所给材料无法确定则写 UNKNOWN>   （订单 A=199、B=99、C=59，满300减50，实付307，只退B 时应退的金额）",
        "EVIDENCE_USED=<你实际依据的材料编号，逗号分隔，如 P40,Q30；没有则写 NONE>",
    ]
    if recompute:
        lines.append("CONCLUSION_REVISED=<YES|NO>   （与上一轮评价相比，结论是否需要修正；没有上一轮评价则写 NO）")
    return "\n".join(lines) + "\n"


# ───────────────────────── Demo 3：场景选择 ─────────────────────────

def _scenario_rows(scenarios: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    rows = []
    for s in scenarios:
        r = s["risk"]
        rows.append({"scenario_id": s["scenario_id"], "title": s["title"], "rule_ids": list(s.get("rule_ids", [])),
                     "impact": r["impact"], "probability": r["probability"], "hard_to_detect": r["hard_to_detect"],
                     "risk_score": r["impact"] * r["probability"] * r["hard_to_detect"],
                     "cost": s["execution_cost"], "validity": s.get("validity"), "stage": s.get("stage"),
                     "category": s.get("category")})
    return rows


def _check_budget(budget: int) -> None:
    if budget not in SUPPORTED_BUDGETS:
        raise ValueError("budget must be one of %s" % (SUPPORTED_BUDGETS,))


def build_d3_prompt(budget: int) -> Dict[str, Any]:
    _check_budget(budget)
    scenarios = load("scenarios/candidates_v1_0.json")["scenarios"]
    rules = load("business/rules_v1_0.json")["rules"]
    rows = _scenario_rows(scenarios)
    prd = load("prd/prd_v1_0.json")
    lines = [
        "你是一名资深业务测试设计顾问。请在有限的测试预算内，为“悦选商城售后退货退款”挑选要执行的测试场景。",
        "",
        "【任务】从下面的候选场景中选出不超过 %d 条（预算上限 %d 条，可以少于但不得超过）。" % (budget, budget),
        "选择需要综合考虑业务风险、执行成本、业务规则覆盖，以及规则证据是否已确认。只能使用清单内的场景ID，不得自造场景。",
        "",
        "【业务需求 V%s】" % prd["version"],
    ]
    lines += ["%s：%s" % (p["source_id"], p["text"]) for p in prd["paragraphs"]]
    lines += ["", "【业务规则及证据状态】（规则ID｜内容｜证据状态；“缺失/推断”表示需求没有写清，尚未确认）"]
    lines += ["%s｜%s｜%s" % (r["rule_id"], r["statement"], EVIDENCE_LABEL[r["evidence_status"]]) for r in rules]
    lines += ["", "【候选场景 %d 条】（场景ID并不连续，以清单为准）" % len(rows),
              "风险分 = 影响 × 发生概率 × 难发现度，分值越大风险越高；执行成本越大越贵；“待确认”表示场景预期依赖尚未确认的规则。",
              "等价类说明：SC04 与 SC05 校验的是同一类无效退货数量风险，通常只需选其中一条。",
              "场景ID｜场景｜关联规则｜影响｜概率｜难发现｜风险分｜执行成本｜场景状态"]
    for r in rows:
        lines.append("%s｜%s｜%s｜%d｜%d｜%d｜%d｜%d｜%s" % (
            r["scenario_id"], r["title"], "、".join(r["rule_ids"]), r["impact"], r["probability"],
            r["hard_to_detect"], r["risk_score"], r["cost"], VALIDITY_LABEL.get(r["validity"], r["validity"])))
    lines += [
        "",
        "【输出格式】",
        "1. 先用表格列出入选场景：| 序号 | 场景ID | 入选原因 | 主要覆盖的规则 | 它防范的关键风险 |",
        "2. 再写“可能遗漏”：说明因预算被放弃的最重要的风险（最多3条），以及仍未覆盖或依据未确认的业务规则。",
        "3. 全文最后，单独一行写出最终清单，格式严格如下（只写场景ID，英文逗号分隔，数量不超过 %d）：" % budget,
        "FINAL_SELECTION: SC01, SC02, ...",
    ]
    return {
        "kind": "d3_select", "title": "AI 场景选择提示词（预算 %d 条）" % budget, "prompt": "\n".join(lines),
        "includes": ["V1.0 需求 P10～P60", "12 条业务规则及证据状态", "41 条候选场景（风险、成本、关联规则）", "预算 %d 条与输出格式" % budget],
        "withholds": ["算法的入选名单与排序结果", "SC36 的人工补漏结论"],
    }


def _evidence_by_rule() -> Dict[str, Dict[str, Any]]:
    return {r["rule_id"]: r for r in load("business/rules_v1_0.json")["rules"]}


def analyze_d3(budget: int, manual: bool, text: str) -> Dict[str, Any]:
    _check_budget(budget)
    scenarios = load("scenarios/candidates_v1_0.json")["scenarios"]
    by_id = {r["scenario_id"]: r for r in _scenario_rows(scenarios)}
    rules = _evidence_by_rule()
    base = select_scenarios(budget, False)
    final = select_scenarios(budget, manual)
    base_ids, final_ids = list(base["selected_ids"]), list(final["selected_ids"])

    markers = parse_markers(text)
    source = "FINAL_SELECTION"
    chosen_raw = markers.get("FINAL_SELECTION")
    if chosen_raw is None:
        source = "fallback"
        chosen_raw = text or ""
    tokens = _split_ids(chosen_raw, r"\bSC\d{2,3}\b")
    ai_ids = [t for t in tokens if t in by_id]
    illegal = [t for t in tokens if t not in by_id]
    raw_count = len(re.findall(r"\bSC\d{2,3}\b", chosen_raw))

    def split(a: List[str], b: List[str]) -> Dict[str, List[str]]:
        return {"common": [i for i in a if i in b], "ai_only": [i for i in a if i not in b],
                "algorithm_only": [i for i in b if i not in a]}

    def totals(ids: List[str]) -> Dict[str, int]:
        return {"count": len(ids), "risk_total": sum(by_id[i]["risk_score"] for i in ids),
                "cost_total": sum(by_id[i]["cost"] for i in ids)}

    coverage = []
    for rule_id, rule in rules.items():
        def covering(ids: List[str], rid: str = rule_id) -> List[str]:
            return [i for i in ids if rid in by_id[i]["rule_ids"]]
        coverage.append({"rule_id": rule_id, "statement": rule["statement"], "evidence_status": rule["evidence_status"],
                         "baseline": covering(base_ids), "final": covering(final_ids), "ai": covering(ai_ids)})

    notes = []  # type: List[str]
    if not tokens:
        notes.append("没有解析到任何合法的场景ID。请确认 AI 输出末尾包含 “FINAL_SELECTION: SC01, SC02, …”，或手动补全后再粘贴。")
    elif source == "fallback":
        notes.append("未找到 FINAL_SELECTION 行，已按全文出现的场景ID解析，可能把“未入选”的ID也算进来，请人工核对。")
    if illegal:
        notes.append("以下ID不在本次候选清单内，已忽略：%s。" % "、".join(illegal))
    if len(ai_ids) > budget:
        notes.append("AI 选了 %d 条，超过预算 %d 条：这是一次不合规的选择，需要它重新裁剪。" % (len(ai_ids), budget))
    if raw_count > len(tokens):
        notes.append("清单中有重复出现的场景ID，已按一次计算。")
    missing_protected = [i for i in PROTECTED_SCENARIO_IDS if ai_ids and i not in ai_ids]
    if missing_protected:
        notes.append("AI 未选 %s：算法在课堂中固定保留这两条“正常流程”基线，AI 是否应保留需要人来判断。" % "、".join(missing_protected))
    if "SC04" in ai_ids and "SC05" in ai_ids:
        notes.append("AI 同时选了 SC04 与 SC05，二者属于同一无效数量等价类，可能浪费一个名额。")
    if "SC05" in ai_ids and "SC04" not in ai_ids:
        notes.append("AI 选了 SC05 而不是 SC04：同一等价类的不同代表，对照时不应判为分歧。")
    if MANUAL_SCENARIO_ID in ai_ids:
        notes.append("AI 自行选入了 %s（金卡+混合支付+优惠失效+渠道超时），这是一个多维高风险组合，依赖的规则仍待确认。" % MANUAL_SCENARIO_ID)
    elif ai_ids:
        notes.append("AI 没有选 %s：该组合依赖多个待确认规则，后面的人工补漏阶段会专门讨论它。" % MANUAL_SCENARIO_ID)

    return {
        "budget": budget, "manual": manual, "source": source if tokens else None, "parsed": bool(ai_ids),
        "ai": dict(totals(ai_ids), ids=ai_ids, illegal_ids=illegal, over_budget=len(ai_ids) > budget),
        "algorithm": dict(totals(base_ids), ids=base_ids),
        "final": dict(totals(final_ids), ids=final_ids, manual_addition=final["manual_addition"]),
        "compare_baseline": split(ai_ids, base_ids), "compare_final": split(ai_ids, final_ids),
        "scenarios": {i: by_id[i] for i in sorted(set(ai_ids + base_ids + final_ids))},
        "coverage": coverage,
        "uncovered": {"baseline": [c["rule_id"] for c in coverage if not c["baseline"]],
                      "final": [c["rule_id"] for c in coverage if not c["final"]],
                      "ai": [c["rule_id"] for c in coverage if ai_ids and not c["ai"]]},
        "notes": notes,
    }


# ───────────────────────── Demo 4：AI 评价测试结果 ─────────────────────────

def build_d4_prompt(round_no: int, previous: str = "") -> Dict[str, Any]:
    head = [
        "你是一名测试质量评审专家。下面是一份需求、一组测试用例的预期假设，以及这些用例对真实实现的执行结果（全部通过）。"
        "请评价这次测试的质量。只能依据下面提供的材料作结论，不得用你对其他商城业务的印象补造规定。",
        "",
        "【评价要求】请分以下四个方面分别回答，并明确区分：",
        "1. 执行层：20/20 通过，证明了什么？",
        "2. 断言层：用例的预期值是怎样得出的？计算过程是否自洽？预期值本身来自哪里？",
        "3. 业务层：这些预期金额是否有需求文档或业务规范的依据？哪些只是测试编写方的假设？",
        "4. 遗漏风险：这批用例没有覆盖、但可能造成资金损失的情形。",
        "最后明确回答：能否仅凭“20/20 PASS”得出“退款金额在业务上正确”？理由是什么？",
        "",
        "【需求文档】",
        _prd_block(),
        "",
        _test_material_block(),
        "",
    ]
    if round_no == 1:
        body = "\n".join(head) + "\n" + _review_format()
        return {"kind": "d4_eval1", "title": "AI 测试结果评价提示词（第1次：未揭示财务规范）", "prompt": body,
                "includes": ["PRD V1.0（含待确认事项）", "测试假设与 20 条用例预期", "20/20 PASS 实际执行证据", "输出格式"],
                "withholds": ["独立财务规范", "正确的退款金额"]}
    previous = (previous or "").strip()[:20000]
    intro = ("\n你上一轮的评价如下（当时没有看到财务规范）：\n<<<\n%s\n>>>\n请对照新材料，逐条指出上一轮哪些结论保持不变、哪些需要修正，并说明为什么。\n" % previous
             if previous else "\n这是一次全新的评价：请直接依据新增的财务规范，独立复算并重新评价上述测试。\n")
    hint = ("请据此独立复算每条用例的应有退款（各用例均为首次退货，此前已退款为 0），"
            "对比测试预期，指出哪些用例的预期与规范不一致，并把原先“20/20 PASS”的含义重新表述一遍。")
    body = "\n".join(head) + intro + "\n" + _finance_block(hint) + _review_format(True)
    return {"kind": "d4_eval2", "title": "AI 测试结果复评提示词（第2次：加入财务规范）", "prompt": body,
            "includes": ["第1次的全部材料", "独立财务规范 F10～F40", "上一轮评价（%s）" % ("已粘贴" if previous else "未提供，按全新评价"),
                         "TC01～TC20 复算格式"],
            "withholds": ["规范中的算例", "任何预先算好的金额"]}


def finance_reference() -> Dict[str, Dict[str, str]]:
    """按独立财务规范重算 20 条用例（本地实际计算；仅在揭示后展示）。"""
    rows = {}
    for case in load("cases/v1_0_executable.json")["cases"]:
        data = case["input"]
        result = calculate_finance_refund(data, return_skus=data["return_skus"])
        rows[case["case_id"]] = {"refund": result["refund"], "status": result["status"],
                                 "test_expected": case["expected"]["refund"], "title": case["title"]}
    return rows


def _markers_view(markers: Dict[str, str]) -> Dict[str, Any]:
    return {"expectations": (markers.get("EXPECTATIONS") or "").upper() or None,
            "classic_b_refund": markers.get("CLASSIC_B_REFUND"),
            "classic_b_amount": _amount(markers.get("CLASSIC_B_REFUND")),
            "evidence_used": markers.get("EVIDENCE_USED"),
            "conclusion_revised": (markers.get("CONCLUSION_REVISED") or "").upper() or None}


def analyze_d4(round_no: int, text: str) -> Dict[str, Any]:
    markers = parse_markers(text)
    view = _markers_view(markers)
    notes = []  # type: List[str]
    if not markers:
        notes.append("没有识别到 EXPECTATIONS / CLASSIC_B_REFUND 标记行；课堂可直接阅读 AI 原文，页面不做自动比较。")
    result = {"round": round_no, "markers": view, "parsed": bool(markers), "notes": notes}
    if round_no == 1:
        if view["classic_b_amount"]:
            result["vs_test_expected"] = "same" if view["classic_b_amount"] == "85.13" else "different"
        return result
    reference = finance_reference()
    recomputed = {}  # type: Dict[str, str]
    block = text.split("RECOMPUTE", 1)[1] if "RECOMPUTE" in (text or "") else (text or "")
    for tc, value in re.findall(r"\b(TC\d{2})\s*[=:：]\s*(REVIEW|UNKNOWN|-?\d+(?:\.\d+)?)", block, flags=re.I):
        recomputed.setdefault(tc.upper(), value.upper() if value.isalpha() else _amount(value) or value)
    rows = []
    for tc, ref in reference.items():
        want = "REVIEW" if ref["status"] == "financial_review_required" else ref["refund"]
        got = recomputed.get(tc)
        rows.append({"case_id": tc, "title": ref["title"], "test_expected": ref["test_expected"], "finance_refund": want,
                     "ai": got, "match": got == want if got is not None else None,
                     "expectation_wrong": ref["test_expected"] != ref["refund"] or ref["status"] != "refund_calculated"})
    graded = [r for r in rows if r["ai"] is not None]
    result.update(
        reference=rows, recompute_found=len(graded), recompute_match=sum(1 for r in graded if r["match"]),
        wrong_expectations=sum(1 for r in rows if r["expectation_wrong"]),
        classic_b_correct=(view["classic_b_amount"] == reference["TC01"]["refund"]) if view["classic_b_amount"] else None,
        correct_classic_b=reference["TC01"]["refund"])
    if not graded:
        notes.append("没有解析到 RECOMPUTE 区块中的 TC01=金额 行；仍可对照下方本地参考值阅读 AI 原文。")
    return result


# ───────────────────────── Demo 5：独立审查 ─────────────────────────

REVIEW_SPLIT = "【补充材料：独立财务规范"


def build_d5_prompt(round_no: int) -> Dict[str, Any]:
    head = [
        "你是一名独立的测试验证者（Independent Verifier）。你没有参与需求编写、用例设计和实现，"
        "只能依据下面提供的材料作结论，不得用你对其他商城业务的印象补造规定。",
        "",
        "【任务】审查这批测试用例的预期结果和执行报告：找出有充分证据支持的问题；"
        "对于无法由所给材料确认的内容，明确写“无法确认”，并说明需要什么证据才能确认。"
        "不要因为全部通过就默认预期正确，也不要为了显得有发现而编造问题。",
        "",
        "【需求文档】",
        _prd_block(),
        "",
        _test_material_block(),
        "",
    ]
    hint = "请根据这份独立来源重新检查退款计算依据和测试预期，并说明与上面材料相比，你的审查结论有哪些变化。"
    block = _finance_block(hint) if round_no == 2 else ""
    prompt = "\n".join(head) + "\n" + block + _review_format()
    return {
        "kind": "d5_review%d" % round_no,
        "title": "AI 独立审查提示词（Review %d：%s）" % (round_no, "加入独立财务规范" if round_no == 2 else "不含财务规范"),
        "prompt": prompt,
        "includes": ["PRD V1.0（含待确认事项）", "20 条用例与预期", "20/20 PASS 执行报告"] + (["独立财务规范 F10～F40"] if round_no == 2 else []),
        "withholds": ["正确的退款金额"] + ([] if round_no == 2 else ["独立财务规范"]),
        "finance_block": block,
    }


def analyze_d5(text1: str, text2: str, label1: str = "", label2: str = "") -> Dict[str, Any]:
    m1, m2 = _markers_view(parse_markers(text1)), _markers_view(parse_markers(text2))

    def keywords(text: str) -> Dict[str, bool]:
        return {"mentions_85_13": "85.13" in (text or ""), "mentions_49": bool(re.search(r"(?<![\d.])49(?:\.00)?(?!\d)", text or "")),
                "mentions_36_13": "36.13" in (text or "")}
    r1, r2 = build_d5_prompt(1)["prompt"], build_d5_prompt(2)["prompt"]
    diff = build_d5_prompt(2)["finance_block"]
    notes = []  # type: List[str]
    if not (text1 or "").strip() or not (text2 or "").strip():
        notes.append("两轮输出都粘贴后才做并排对照。")
    else:
        e1, e2 = m1["expectations"], m2["expectations"]
        if e1 and e2 and e1 == e2:
            notes.append("两轮 EXPECTATIONS 相同（%s）：请检查是否有实质变化——新增证据没有改变结论，也是一种结果。" % e1)
        if e1 == "CONTRADICTED":
            notes.append("第一轮就判定预期被材料推翻：请核对其 EVIDENCE_USED=%s 是否真的来自所给材料，还是模型自行假设的规则。" % (m1["evidence_used"] or "未给出"))
        if label1.strip() and label1.strip() == label2.strip():
            notes.append("两轮使用同一模型：差别只来自新增输入。")
        elif label1.strip() and label2.strip():
            notes.append("两轮使用不同模型/Agent：若第一轮仍未发现关键金额问题，说明更换模型不等于获得新的业务证据。")
    return {"round1": dict(m1, **keywords(text1), label=label1), "round2": dict(m2, **keywords(text2), label=label2),
            "input_difference": {"only_in_round2": diff.strip().splitlines()[0], "round1_contains_finance": "F10" in r1 or "YS-FIN-AFTERSALES-01" in r1,
                                 "round2_contains_finance": "F10" in r2 and "YS-FIN-AFTERSALES-01" in r2,
                                 "identical_after_removing_block": r2.replace(diff, "") == r1},
            "notes": notes}


# ───────────────────────── Demo 6：变更影响分析 ─────────────────────────

def _history_case_line(case: Dict[str, Any]) -> str:
    inp = dict(case["input"])
    if isinstance(inp.get("items"), list):
        inp["items"] = {i["sku"]: i["gross"] for i in inp["items"]}
    for noisy in ("order_id", "policy", "rounding"):
        inp.pop(noisy, None)
    scope = "｜断言范围 " + case["assertion_scope"] if case.get("assertion_scope") else ""
    return "%s｜%s｜%s｜用例依赖规则 %s｜场景 %s｜输入 %s｜预期 %s%s" % (
        case["case_id"], case["title"], case["kind"], "、".join(case["rule_ids"]),
        "、".join(case["scenario_ids"]), _compact(inp), _compact(case["expected"]), scope)


def _d6_universe() -> Tuple[Dict[str, Any], Dict[str, Any]]:
    history = load("history/v1_0_validated_baseline.json")
    scenes = {s["scenario_id"]: s for s in history["scenarios"]}
    scenes.update({s["scenario_id"]: s for s in load("scenarios/candidates.json")["scenarios"]})
    used = []  # type: List[str]
    for case in history["cases"]:
        for sid in case["scenario_ids"]:
            if sid not in used:
                used.append(sid)
    return history, {sid: scenes[sid] for sid in used}


def build_d6_prompt() -> Dict[str, Any]:
    history, scenes = _d6_universe()
    prd0, prd1 = load("prd/prd_v1_0.json"), load("prd/prd_v1_1.json")
    rules = load("business/rules_v1_0.json")["rules"]
    finance = load("finance/after_sales_funds.json")["rules"]
    lines = [
        "你是一名测试资产维护顾问。悦选商城售后需求从 V1.0 升级到 V1.1。请只依据下面的材料，分析这次变更对既有测试资产的影响，"
        "并给出每条历史用例的处置建议：保留 / 修改 / 作废，以及需要新增的用例。",
        "",
        "【判断原则】",
        "- 沿“变更 → 规则 → 场景 → 用例”的依赖链判断，不要凭印象；",
        "- 区分“行为或断言发生变化（需要修改/作废/新增）”和“只是需求来源或依据被更新、行为与金额不变（仍可保留）”；",
        "- 能保留就不要重建，避免为凑数量而重做已验证的资产；也不要漏掉真正受影响的用例。",
        "",
        "【V1.0 基线需求】",
    ]
    lines += ["%s：%s" % (p["source_id"], p["text"]) for p in prd0["paragraphs"]]
    lines += ["", "【V1.0 业务规则】（规则ID｜内容）"]
    lines += ["%s｜%s" % (r["rule_id"], r["statement"]) for r in rules]
    lines += ["", "【已独立验证的财务规范（历史金额用例的依据）】"]
    lines += ["%s：%s" % (r["rule_id"], r["text"]) for r in finance]
    lines += ["", "【V1.1 三项变更】（变更ID｜对应规则｜新增或替换的需求原文）"]
    lines += ["%s｜%s｜%s：%s" % (c["change_id"], c["rule_id"], c["source_id"], c["text"].replace("本 Demo", "本需求")) for c in prd1["changes"]]
    lines += ["", "【历史场景】（场景ID｜标题｜关联规则）"]
    lines += ["%s｜%s｜%s" % (sid, s["title"], "、".join(s["rule_ids"])) for sid, s in scenes.items()]
    lines += ["", "【历史测试用例 %d 条（均已独立验证）】（ID｜标题｜类型｜用例依赖规则｜场景｜输入｜预期）" % len(history["cases"])]
    lines += [_history_case_line(c) for c in history["cases"]]
    lines += [
        "",
        "【输出格式】",
        "1. 受影响规则与场景：说明为什么受影响（沿依赖链）。然后各占一行输出：",
        "AFFECTED_RULES: <规则ID，英文逗号分隔>",
        "AFFECTED_SCENARIOS: <上面历史场景清单中的场景ID，英文逗号分隔>",
        "2. 逐条处置表：每条历史用例必须独占一行，不得合并或用范围表示，格式：",
        "| 用例ID | 保留/修改/作废 | 理由（说明是行为变化，还是仅来源更新） |",
        "3. 新增用例建议：每条独占一行，编号 N01、N02……，格式：| N01 | 标题 | 关联规则 | 关键断言 | 为什么现有用例不能覆盖 |",
        "4. 最后单独一行：NEW_CASE_COUNT=<新增用例的条数>",
    ]
    return {"kind": "d6_impact", "title": "AI 需求变更影响分析提示词（V1.0 → V1.1）", "prompt": "\n".join(lines),
            "includes": ["V1.0 基线需求与规则", "已验证财务规范", "V1.1 三项变更原文", "%d 个历史场景" % len(scenes),
                         "%d 条历史用例（依赖规则、场景、输入、预期）" % len(history["cases"])],
            "withholds": ["确定性影响分析的结果（受影响规则/场景、保留·修改·作废·新增数量）", "回归执行结果"]}


def _action_of(segment: str) -> Optional[str]:
    best = None
    for word, action in ACTION_WORDS:
        index = segment.lower().find(word)
        if index >= 0 and (best is None or index < best[0]):
            best = (index, action)
    return best[1] if best else None


def analyze_d6(text: str) -> Dict[str, Any]:
    migration = build_migration()
    _, universe = _d6_universe()
    markers = parse_markers(text)
    algo = {a["case_id"]: a["action"] for a in migration["case_actions"] if a["before"]}
    algo_titles = {a["case_id"]: a["title"] for a in migration["case_actions"]}

    rules_ai = _split_ids(markers.get("AFFECTED_RULES", ""), r"\bR-[A-Z]+(?:-[A-Z]+)*\b|\bF\d{2}\b")
    scenes_ai = [s for s in _split_ids(markers.get("AFFECTED_SCENARIOS", ""), r"\b(?:HS-[A-Z0-9]+(?:-\d+)?|SC\d{2,3})\b") if s in universe]
    rules_algo = list(migration["affected_rules"])
    scenes_algo = [s["scenario_id"] for s in migration["affected_scenarios"] if s["scenario_id"] in universe]

    ai_actions = {}  # type: Dict[str, str]
    for line in (text or "").splitlines():
        ids = re.findall(r"\bH-[A-Z]+\d*(?:-\d+)?\b", line)
        if len(ids) != 1 or ids[0] not in algo:
            continue
        action = _action_of(line.split(ids[0], 1)[1])
        if action:
            ai_actions[ids[0]] = action
    rows, groups = [], {"agree": [], "missed": [], "over_reaction": [], "different_change": [], "unparsed": []}
    for cid, expected in algo.items():
        got = ai_actions.get(cid)
        if got is None:
            kind = "unparsed"
        elif got == expected:
            kind = "agree"
        elif expected in ("modify", "obsolete") and got == "retain":
            kind = "missed"
        elif expected == "retain":
            kind = "over_reaction"
        else:
            kind = "different_change"
        groups[kind].append(cid)
        rows.append({"case_id": cid, "title": algo_titles[cid], "algorithm": expected, "ai": got, "result": kind})

    new_ids = _split_ids("\n".join(l for l in (text or "").splitlines() if re.match(r"^[\s|*-]*N\d{2}\b", l)), r"\bN\d{2}\b")
    declared = _amount(markers.get("NEW_CASE_COUNT"))
    ai_new = len(new_ids) if new_ids else (int(float(declared)) if declared else None)
    changed_ai = sum(1 for v in ai_actions.values() if v in ("modify", "obsolete"))
    changed_algo = sum(1 for v in algo.values() if v in ("modify", "obsolete"))
    notes = []  # type: List[str]
    parsed_any = bool(ai_actions or rules_ai)
    if not parsed_any:
        notes.append("没有解析到处置表或 AFFECTED_RULES 标记；请确认 AI 按格式逐行输出了“| 用例ID | 处置 | 理由 |”。")
    elif groups["unparsed"]:
        notes.append("有 %d 条历史用例没有解析到处置（可能被合并成范围或漏写），已单独列出。" % len(groups["unparsed"]))
    if ai_new is not None and declared and new_ids and int(float(declared)) != len(new_ids):
        notes.append("NEW_CASE_COUNT=%s 与新增清单实际条数 %d 不一致，以清单为准。" % (declared, len(new_ids)))
    provenance_rules = [r for r in ("R-PARTIAL-AMOUNT", "R-PROMO-RECALC") if r in rules_algo and r not in rules_ai]
    if provenance_rules and parsed_any:
        notes.append("确定性分析把 C30 涉及的规则（%s）也计入“受影响”，但那只是需求来源被正式化，金额与行为不变；AI 只列行为发生变化的规则也是一种合理读法，差别在“受影响”的定义。" % "、".join(provenance_rules))
    return {
        "parsed": parsed_any,
        "rules": {"ai": rules_ai, "algorithm": rules_algo, "common": [r for r in rules_ai if r in rules_algo],
                  "ai_only": [r for r in rules_ai if r not in rules_algo], "algorithm_only": [r for r in rules_algo if r not in rules_ai]},
        "scenarios": {"ai": scenes_ai, "algorithm": scenes_algo, "common": [s for s in scenes_ai if s in scenes_algo],
                      "ai_only": [s for s in scenes_ai if s not in scenes_algo], "algorithm_only": [s for s in scenes_algo if s not in scenes_ai],
                      "note": "仅比较提示词中给出的历史场景（共 %d 个）。" % len(universe)},
        "cases": rows, "groups": groups,
        "counts": {"history_total": len(algo), "ai_parsed": len(ai_actions),
                   "ai": {k: sum(1 for v in ai_actions.values() if v == k) for k in ("retain", "modify", "obsolete")},
                   "algorithm": {k: sum(1 for v in algo.values() if v == k) for k in ("retain", "modify", "obsolete")},
                   "ai_new": ai_new, "algorithm_new": migration["summary"]["add"],
                   "ai_changed_existing": changed_ai, "algorithm_changed_existing": changed_algo,
                   "ai_rebuild_total": (changed_ai + (ai_new or 0)) if ai_actions else None,
                   "algorithm_rebuild_total": changed_algo + migration["summary"]["add"],
                   "full_regeneration": migration["comparison"]["full_regeneration"]},
        "notes": notes,
    }


# ───────────────────────── 入口 ─────────────────────────

def build_prompt(kind: str, budget: int = 15, previous: str = "") -> Dict[str, Any]:
    if kind == "d3_select":
        result = build_d3_prompt(budget)
    elif kind == "d4_eval1":
        result = build_d4_prompt(1)
    elif kind == "d4_eval2":
        result = build_d4_prompt(2, previous)
    elif kind in ("d5_review1", "d5_review2"):
        result = build_d5_prompt(int(kind[-1]))
        result.pop("finance_block", None)
    elif kind == "d6_impact":
        result = build_d6_prompt()
    else:
        raise ValueError("unknown prompt kind: %s" % kind)
    result["chars"] = len(result["prompt"])
    return result


def analyze(kind: str, text: str = "", text2: str = "", budget: int = 15, manual: bool = False,
            label1: str = "", label2: str = "") -> Dict[str, Any]:
    if kind == "d3_select":
        return analyze_d3(budget, manual, text)
    if kind in ("d4_eval1", "d4_eval2"):
        return analyze_d4(int(kind[-1]), text)
    if kind == "d5_compare":
        return analyze_d5(text, text2, label1, label2)
    if kind == "d6_impact":
        return analyze_d6(text)
    raise ValueError("unknown analysis kind: %s" % kind)
