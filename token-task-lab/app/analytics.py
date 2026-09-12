"""Demo 3：从 Token 计数报表升级到任务级运行报表。

这个模块只做一件事：把 `runs/` 里**已有的**记录按任务聚合成三层指标。

* 不调用 provider，不产生新记录，不推断记录里没有的东西。
* 单位是「任务」：一条有效 run record = 一件业务任务。
* 每一项的口径都写在它自己的注释里，测试按这些口径逐条钉住。

课堂要证明的是：只统计 Token、调用次数和响应时间，不足以解释 Token 的变化；
要解释它，至少还要知道这些 Token 支撑了多少件任务。
"""

from __future__ import annotations

from .models import RunRecord

# 任务级状态。run 级只有这几种：ok / waiting_human / error / not_executed。
# 「阻塞」不是 run 级状态——它是步骤级状态（例如 C 档的「获取可核验业务事实」
# 因为拿不到可核验事实被标 blocked）。所以下面统计的是「至少有一处业务步骤被
# 阻塞的运行」，并把这个口径写在页面上，不假装它是 run 自己的状态。
RUN_STATUS_OK = "ok"
RUN_STATUS_WAITING_HUMAN = "waiting_human"
RUN_STATUS_ERROR = "error"


def _item(
    key: str,
    label: str,
    *,
    value: float | int | None = None,
    display: str = "—",
    unit: str = "",
    hint: str | None = None,
    tone: str | None = None,
) -> dict:
    return {
        "key": key,
        "label": label,
        "value": value,
        "display": display,
        "unit": unit,
        "hint": hint,
        "tone": tone,
    }


def _int(value: float | int | None) -> str:
    return "—" if value is None else f"{int(round(value)):,}"


def _one(value: float | None) -> str:
    return "—" if value is None else f"{value:,.1f}"


def _pct(part: int, whole: int) -> str:
    return "—" if not whole else f"{part / whole * 100:.0f}%"


def valid_records(records: list[RunRecord]) -> tuple[list[RunRecord], dict[str, int]]:
    """完整样本：真实执行 + Token 计量完整 + 有明确 run_status。

    被排除的三类都单独计数，页面上照实写出来——「完整样本 N 条 / 记录 M 条」比
    一个来路不明的总数可信：结构示例（没跑过模型）、Token 没计量完整的（provider
    没返回 usage）、以及没有运行状态的。输出是否被截断不参与筛选：那是输出完整性，
    和 Token 计量是两件事。
    """
    valid: list[RunRecord] = []
    excluded = {"structure_only": 0, "token_incomplete": 0, "no_status": 0}
    for record in records:
        if record.evidence_level != "live":
            excluded["structure_only"] += 1
            continue
        if record.token_evidence != "measured" or record.usage.total_tokens is None:
            excluded["token_incomplete"] += 1
            continue
        if not record.run_status:
            excluded["no_status"] += 1
            continue
        valid.append(record)
    return valid, excluded


def _sum(records: list[RunRecord], getter) -> int | None:
    """Sum, or None when nothing in the sample actually reported the field."""
    values = [getter(record) for record in records]
    values = [value for value in values if value is not None]
    if not values:
        return None
    return sum(values)


def _mean(values: list[float]) -> float | None:
    return sum(values) / len(values) if values else None


def build_report(
    records: list[RunRecord], *, mode: str | None = None, modes: list[str] | None = None
) -> dict:
    """三层指标报表。``mode`` 为 None 时统计全部有效样本。

    所有派生指标都在这里算好，页面只负责显示——这样每一条口径都能被测到，
    也不会在浏览器里再算一遍。
    """
    selected = [record for record in records if mode is None or record.mode == mode]
    valid, excluded = valid_records(selected)
    tasks = len(valid)

    # ---- 可加总的基础量 -------------------------------------------------
    total_tokens = _sum(valid, lambda r: r.usage.total_tokens)
    model_calls = _sum(valid, lambda r: r.usage.model_calls)
    tool_calls = _sum(valid, lambda r: r.usage.tool_calls)
    input_tokens = _sum(valid, lambda r: r.usage.input_tokens)
    output_tokens = _sum(valid, lambda r: r.usage.output_tokens)
    # 缓存单独加总，绝不并入 total_tokens：cached 是 input 的组成部分，
    # 再加一次就是把同一批 Token 数了两遍。provider 全程没上报过缓存时保持 None。
    cached_tokens = _sum(valid, lambda r: r.usage.cached_tokens)

    # 运行耗时：run 级总耗时（usage.latency_ms = 该 run 各步骤耗时之和，工具步骤
    # 记 0）。不是「单次模型调用的平均耗时」，两者不混算。
    run_latencies = [r.usage.latency_ms for r in valid if r.usage.latency_ms is not None]
    avg_run_latency_ms = _mean(run_latencies)

    # 状态计数。ok = 正常完成；waiting_human = 停在人工确认点；error = 执行出错；
    # blocked = 至少有一处业务步骤被阻塞（步骤级判定，见文件头说明）。
    ok_runs = [r for r in valid if r.run_status == RUN_STATUS_OK]
    waiting_runs = [r for r in valid if r.run_status == RUN_STATUS_WAITING_HUMAN]
    error_runs = [r for r in valid if r.run_status == RUN_STATUS_ERROR]
    blocked_runs = [
        r for r in valid if any(step.status == "blocked" for step in r.steps)
    ]

    # 任务结构特征（不是复杂度评分）：这些都是记录里能直接数出来的结构量。
    steps_per_task = _mean([len(r.steps) for r in valid]) if valid else None
    input_per_task = input_tokens / tasks if input_tokens is not None and tasks else None
    # 校验步骤：C 档的 phase 是 verify，D 档是 d-verify-1 / d-verify-2（重复校验），
    # 两者都算「这一步做了校验」，所以按 phase 是否含 verify 判定。
    verify_share = (
        sum(1 for r in valid if any("verify" in s.phase for s in r.steps)) / tasks
        if tasks
        else None
    )

    per_task = (lambda total: total / tasks if total is not None and tasks else None)
    tokens_per_task = per_task(total_tokens)

    # ---- 第一层：基础调用指标 -------------------------------------------
    # 最常见的四个数字。这一层故意不给任务级口径——课堂上先让信息「不够」。
    layer1 = [
        _item(
            "total_tokens", "Token 总量",
            value=total_tokens, display=_int(total_tokens),
            hint="全部有效运行的 usage.total_tokens 之和",
        ),
        _item(
            "model_calls", "模型调用次数",
            value=model_calls, display=_int(model_calls), unit="次",
            hint="全部有效运行的模型调用次数之和",
        ),
        _item(
            "avg_latency", "平均响应时间",
            value=avg_run_latency_ms,
            display="—" if avg_run_latency_ms is None else f"{avg_run_latency_ms / 1000:.1f}",
            unit="秒",
            hint="run 级总耗时（该 run 各步骤耗时之和）的平均值，不是单次模型调用的平均耗时",
        ),
        _item(
            "error_runs", "异常运行",
            value=len(error_runs),
            display=f"{_int(len(error_runs))} 次 / {_pct(len(error_runs), tasks)}",
            tone="warn" if error_runs else None,
            hint="run_status=error 的运行数与占比",
        ),
    ]

    # ---- 第二层：调用结构指标 -------------------------------------------
    tokens_per_call = (
        total_tokens / model_calls if total_tokens is not None and model_calls else None
    )
    input_per_call = (
        input_tokens / model_calls if input_tokens is not None and model_calls else None
    )
    layer2 = [
        _item(
            "input_tokens", "Input Token 合计",
            value=input_tokens, display=_int(input_tokens),
            hint="各行 usage.input_tokens 之和",
        ),
        _item(
            "output_tokens", "Output Token 合计",
            value=output_tokens, display=_int(output_tokens),
            hint="各行 usage.output_tokens 之和",
        ),
        _item(
            "cached_tokens", "Cached Token 合计",
            value=cached_tokens,
            display="未上报" if cached_tokens is None else _int(cached_tokens),
            hint="usage.cached_tokens 之和；它是 input 的组成部分，不并入 Token 总量",
        ),
        _item(
            "model_calls", "模型调用次数",
            value=model_calls, display=_int(model_calls), unit="次",
            hint="与第一层同一个数，这里放在调用结构里看",
        ),
        _item(
            "tool_calls", "工具调用次数",
            value=tool_calls, display=_int(tool_calls), unit="次",
            hint="各步 tool_calls 之和",
        ),
        _item(
            "tokens_per_call", "平均每次模型调用 Token",
            value=tokens_per_call, display=_one(tokens_per_call),
            hint="Token 总量 ÷ 模型调用次数",
        ),
        _item(
            "input_per_call", "平均每次调用输入 Token",
            value=input_per_call, display=_one(input_per_call),
            hint="Input Token 合计 ÷ 模型调用次数——上下文规模的代理量，不是「复杂度分数」",
        ),
    ]

    # ---- 第三层：任务级指标 ---------------------------------------------
    layer3 = [
        _item("task_count", "任务数", value=tasks, display=_int(tasks), unit="件",
              hint="一条有效 run record 计 1 件任务"),
        _item("tokens_per_task", "Token / 任务", value=tokens_per_task,
              display=_one(tokens_per_task), hint="Token 总量 ÷ 任务数"),
        _item("model_calls_per_task", "模型调用 / 任务",
              value=per_task(model_calls), display=_one(per_task(model_calls)),
              hint="模型调用次数 ÷ 任务数"),
        _item("tool_calls_per_task", "工具调用 / 任务",
              value=per_task(tool_calls), display=_one(per_task(tool_calls)),
              hint="工具调用次数 ÷ 任务数"),
        _item("avg_task_latency", "平均任务耗时",
              value=avg_run_latency_ms,
              display="—" if avg_run_latency_ms is None else f"{avg_run_latency_ms / 1000:.1f}",
              unit="秒",
              hint="与第一层同一个数：run 级总耗时（该 run 各步骤耗时之和）的平均值"),
    ]

    status_items = [
        _item("completed", "完成", value=len(ok_runs),
              display=f"{_int(len(ok_runs))} 件 / {_pct(len(ok_runs), tasks)}",
              hint="run_status=ok：正常跑完的任务"),
        _item("blocked", "含阻塞步骤", value=len(blocked_runs),
              display=f"{_int(len(blocked_runs))} 件 / {_pct(len(blocked_runs), tasks)}",
              tone="warn" if blocked_runs else None,
              hint="至少有一处业务步骤 status=blocked 的任务（run 级状态里没有 blocked，这一项按步骤判定）"),
        _item("waiting_human", "转人工", value=len(waiting_runs),
              display=f"{_int(len(waiting_runs))} 件 / {_pct(len(waiting_runs), tasks)}",
              hint="run_status=waiting_human：停在人工确认点的任务"),
        _item("failed", "失败", value=len(error_runs),
              display=f"{_int(len(error_runs))} 件 / {_pct(len(error_runs), tasks)}",
              hint="run_status=error：执行出错的任务"),
    ]

    structure_items = [
        _item("steps_per_task", "执行步骤 / 任务", value=steps_per_task,
              display=_one(steps_per_task), hint="各 run 的 steps 条数平均值"),
        _item("input_per_task", "输入上下文 Token / 任务", value=input_per_task,
              display=_one(input_per_task), hint="Input Token 合计 ÷ 任务数，上下文规模代理量"),
        _item("verify_share", "含校验步骤的运行",
              value=verify_share,
              display="—" if verify_share is None else f"{verify_share * 100:.0f}%",
              hint="steps 里出现校验步骤（phase=verify）的运行占比"),
    ]

    # ---- 收束：任务量 × 单任务 Token -------------------------------------
    final = {
        "task_count": tasks,
        "tokens_per_task": tokens_per_task,
        "total_tokens": total_tokens,
        "display_task_count": _int(tasks),
        "display_tokens_per_task": _one(tokens_per_task),
        "display_total_tokens": _int(total_tokens),
        "formula": "任务量 × 单任务 Token = Token 总量",
        "question": "Token 增长，到底来自更多真实任务，还是同样任务变得更贵？",
    }

    return {
        "source": "run_records",
        "mode_filter": mode,
        "sample": {
            "total_records": len(records),
            "selected_records": len(selected),
            "valid_records": tasks,
            "excluded": excluded,
            "modes": sorted({r.mode for r in records}),
            "note": (
                "样本来自 runs/ 里已有的真实运行记录。"
                "只纳入真实执行、Token 计量完整、有明确运行状态的记录；"
                "输出是否被截断不影响 Token 计量，因此不作为筛选条件。"
                "这是课前几次真机运行的聚合，用来演示指标体系，不是生产经营统计。"
            ),
        },
        "example": _example(valid),
        "layers": [
            {
                "key": "layer1",
                "title": "第一层｜我们通常先看到这些数字",
                "question": "这些数字能告诉我们用了多少，但能解释为什么吗？",
                "items": layer1,
            },
            {
                "key": "layer2",
                "title": "第二层｜调用结构：Token 是怎么花掉的",
                "question": "这些调用到底完成了多少真实工作？",
                "items": layer2,
            },
            {
                "key": "layer3",
                "title": "第三层｜任务级指标：这些调用支撑了多少任务",
                "question": (
                    "从这里开始，我们看的不再只是模型用了多少，"
                    "而是这些模型调用到底支撑了多少任务。"
                ),
                "items": layer3,
                "status_title": "状态分布",
                "status_items": status_items,
                "structure_title": "任务结构特征（不是复杂度评分）",
                "structure_note": (
                    "这里只列记录里能直接数出来的结构量：调用数、步骤数、上下文规模、"
                    "是否包含校验步骤。它们不是「任务复杂度」的数学分数。"
                ),
                "structure_items": structure_items,
            },
        ],
        "final": final,
    }


def _example(valid: list[RunRecord]) -> dict | None:
    """当前样本里最近的一条运行——把 Demo 3 和前两个 Demo 的那条记录接上。"""
    if not valid:
        return None
    record = max(valid, key=lambda item: item.created_at)
    return {
        "run_id": record.run_id,
        "mode": record.mode,
        "mode_label": record.mode_label,
        "created_at": record.created_at,
        "model_calls": record.usage.model_calls,
        "tool_calls": record.usage.tool_calls,
        "total_tokens": record.usage.total_tokens,
        "run_status": record.run_status,
    }
