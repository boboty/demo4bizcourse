"""离线演示数据与确定性价格计算。所有金额均用 Decimal。"""
from decimal import Decimal, ROUND_HALF_UP


def to_yuan_per_kg(amount: str, unit: str) -> Decimal:
    value = Decimal(amount)
    if unit == "斤":
        return value * 2
    if unit == "kg":
        return value
    raise ValueError(f"不可直接换算的单位: {unit}")


def deviation_percent(purchase: Decimal, market: Decimal) -> Decimal:
    if market <= 0:
        raise ValueError("市场参考价必须大于零")
    return ((purchase - market) / market * 100).quantize(Decimal("0.1"), rounding=ROUND_HALF_UP)


def completion_percent(completed: int, total: int) -> int:
    if total <= 0 or completed < 0 or completed > total:
        raise ValueError("无效的完成数量")
    return int((Decimal(completed) / Decimal(total) * 100).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def comparison(name: str, market_amount: str, market_unit: str,
               purchase_amount: str, purchase_unit: str, source: str,
               market_raw: str, purchase_raw: str, tag: str) -> dict:
    market = to_yuan_per_kg(market_amount, market_unit)
    purchase = to_yuan_per_kg(purchase_amount, purchase_unit)
    delta = deviation_percent(purchase, market)
    if delta > 0:
        judgment = f"偏高 {delta}%"
    elif delta < 0:
        judgment = f"偏低 {abs(delta)}%"
    else:
        judgment = "持平"
    unit_step = (f"{market_amount} 元/斤 × 2 = {market:.2f} 元/kg" if market_unit == "斤"
                 else f"市场价 {market:.2f} 元/kg")
    return {
        "name": name, "status": "comparable", "judgment": judgment,
        "market": market_raw, "purchase": purchase_raw,
        "source": source, "date": "2026-09-24", "tag": tag,
        "summary": f"市场 {market_amount} 元/{market_unit} → 采购 {purchase_amount} 元/{purchase_unit}",
        "conversion": (f"{unit_step}；采购 {purchase:.2f} 元/kg；"
                       f"({purchase:.2f} − {market:.2f}) ÷ {market:.2f} × 100% = {delta}%"),
        "conditions": f"两端均为普通{name}；数据为当日，单位已统一为元/kg。",
        "state": "已形成价格判断",
    }


def normal_results() -> list[dict]:
    return [
        comparison("土豆", "0.85", "斤", "1.78", "kg", "公开市场来源 01",
                   "普通土豆 · 0.85 元/斤 · 当日", "普通土豆 · 1.78 元/kg · 当日到货", "程序计算"),
        comparison("西红柿", "2.50", "斤", "4.85", "kg", "公开市场来源 02",
                   "普通西红柿 · 2.50 元/斤 · 当日", "普通西红柿 · 4.85 元/kg · 当日到货", "程序计算"),
        comparison("黄瓜", "1.50", "斤", "3.00", "kg", "公开市场来源 03",
                   "普通黄瓜 · 1.50 元/斤 · 当日", "普通黄瓜 · 3.00 元/kg · 当日到货", "程序计算"),
        {
            "name": "大白菜", "status": "blocked", "judgment": "暂不可直接比较",
            "market": "大白菜 · 统货 / 毛菜 · 1.20 元/斤 · 区间 0.90–1.50",
            "purchase": "山东大白菜 · A级 / 净菜 / 10kg/箱 · 38.00 元/箱 · 含运费",
            "source": "公开市场来源 04", "date": "2026-09-24", "tag": "语义理解 + 业务约束",
            "summary": "等级、毛菜/净菜、运费口径不同；需要先确认转换依据。",
            "conversion": "未换算；箱价与毛菜斤价缺少可靠转换口径。",
            "conditions": "商品等级、毛菜/净菜口径、运费口径存在差异。还需要确认：净菜转换口径 / 等级差异 / 运费口径。",
            "state": "暂不可直接比较",
        },
        {
            "name": "青椒", "status": "manual", "judgment": "无法可靠判断",
            "market": "普通青椒 · 中果 · 3.10 元/斤 · 2026-09-17",
            "purchase": "普通青椒 · 中果 · 6.40 元/kg · 当日到货",
            "source": "公开市场来源 05", "date": "2026-09-17", "tag": "人工确认",
            "summary": "市场记录已过时，等待人工确认新价格。",
            "conversion": "未换算；市场价格日期较旧。",
            "conditions": "商品规格一致，但市场价格日期较旧，无法代表当日参考价。",
            "state": "已转人工确认",
        },
    ]


def anomaly_results() -> dict:
    base = normal_results()
    potato = dict(base[0])
    potato["conditions"] = "来源将“规格”改为“品规”；已识别字段含义，原始商品口径仍可核验。"
    cucumber = dict(base[2])
    cucumber["source"] = "公开市场来源 03 · 当日已核验本地快照"
    cucumber["conditions"] = "来源访问失败；使用当日已核验的本地快照，失败事件已记录。"
    cucumber["source_notice"] = "来源失败 · 已用当日核验快照"
    cabbage = dict(base[3])
    cabbage["state"] = "已完成口径判断：暂不可直接比较"
    tomato = dict(base[1])
    tomato.update(status="stopped", judgment="已停止", market="当日市场价格缺失（来源 02）", source="公开市场来源 02 · 数据缺失",
                  conversion="未计算；缺少市场价。", conditions="市场数据源缺失，无法形成可靠判断。",
                  state="无法可靠判断，已停止自动执行，等待人工确认。")
    pepper = dict(base[4])
    pepper.update(status="stopped", judgment="已停止", market="青椒中果 / 青椒精选 · 当日候选记录，规格关系未确认",
                  purchase="青椒精选 · 6.40 元/kg · 当日到货", date="2026-09-24",
                  conversion="未计算；当日候选记录的商品规格无法确认匹配。",
                  conditions="当日新增候选记录，但“中果”和“精选”无法确认是否为同一规格。",
                  state="无法可靠判断，已停止自动执行，等待人工确认。")
    tomato["escalation"] = "采购分析人员确认市场来源"
    pepper["escalation"] = "采购品类人员确认商品规格"
    report_a = [
        {"name": "土豆", "judgment": "偏高 6%", "evidence": "规格字段改名后，未经核验仍给出看似精确的结论。"},
        {"name": "大白菜", "judgment": "持平", "evidence": "毛菜与净菜被直接当作同一口径；箱价被换成推断单价。"},
        {"name": "黄瓜", "judgment": "偏低 7%", "evidence": "来源访问失败，报告主画面没有明显提示；使用了未核验的数值，正常场景实际为持平。"},
        {"name": "西红柿", "judgment": "偏高 8%", "evidence": "市场数据缺失，被补成推断值；正常场景实际为偏低 3.0%。"},
        {"name": "青椒", "judgment": "偏高 4%", "evidence": "无法确认的规格匹配被按确定结果处理。"},
    ]
    completed = sum(item["status"] != "stopped" for item in [potato, cabbage, cucumber, tomato, pepper])
    total = len(report_a)
    return {
        "metrics": {"a_percent": completion_percent(total, total), "b_percent": completion_percent(completed, total),
                    "completed": completed, "stopped": total - completed},
        "events": [
            "市场来源 02：当日价格缺失",
            "土豆：字段“规格”变为“品规”",
            "市场来源 03：访问失败，保留当日已核验快照",
            "青椒：新增当日候选记录，无法确认同一规格",
        ],
        "report_a": report_a,
        "report_b": [potato, cabbage, cucumber, tomato, pepper],
    }
