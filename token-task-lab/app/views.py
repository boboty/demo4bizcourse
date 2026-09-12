"""Front / back projections of a run record.

Two rules this module exists to enforce.

1. Demo 1 must never show a token number. `front_view` is built from an
   allow-list, so a new field on the record cannot leak into the business half
   by accident.

2. Demo 1 must show what *this run* produced, not what the scenario file says.
   The scenario's `known` / `missing` / `next_actions` are written before any
   model runs — presenting them as the model's work would make the second
   lecture's claim ("watch the AI break the task down") false. They are still
   shown, but only as an explicitly labelled 场景验收基准 to compare against,
   while the main area renders `observations`: the actual parse / gaps / facts /
   judge / deliver output of this run.
"""

from __future__ import annotations

from .models import RunRecord

# Everything Demo 1 is allowed to see. Deliberately excludes the preset
# baseline fields — those travel inside `baseline` so the page has to label
# them as pre-written rather than free to render them as "the AI's answer".
FRONT_FIELDS = (
    "run_id",
    "created_at",
    "scenario",
    "scenario_name",
    "mode",
    "mode_label",
    "request_text",
    "task",
    "dependencies",
    "evidence_level",
    "run_status",
)

# Field names that must never appear in a front view, checked by the test suite.
# Truncation is a system-side fact about the calls behind the text: it belongs
# to Demo 2, so Demo 1 stays free of it along with every other run-side number.
FORBIDDEN_IN_FRONT = (
    "usage",
    "steps",
    "model",
    "input_tokens",
    "output_tokens",
    "cached_tokens",
    "total_tokens",
    "latency_ms",
    "model_calls",
    "tool_calls",
    "claim_audit",
    "usage_raw",
    "provider",
    "token_evidence",
    "usage_summary",
    "finish_reason",
    "truncated",
    "truncated_steps",
    "output_evidence",
    "freeze_ready",
)

# Which chain step answers which Demo 1 question. The low-efficiency mode's
# repeated phases map onto the same questions as their C-mode counterparts —
# D differs in cost, not in business content.
OBSERVATION_PHASES: dict[str, tuple[str, str]] = {
    "direct": ("result", "AI 直接给出的结果"),
    "answer": ("result", "AI 基于全量上下文的回答"),
    "parse": ("understanding", "AI 实际任务理解"),
    "d-parse-1": ("understanding", "AI 实际任务理解"),
    "gaps": ("gaps", "AI 实际识别缺口"),
    "facts": ("facts", "本次事实获取结果"),
    "d-context-1": ("facts", "本次事实获取结果"),
    "judge": ("judgment", "AI 业务判断与人工确认点"),
    "d-judge-strong": ("judgment", "AI 业务判断与人工确认点"),
    "verify": ("verification", "AI 校验结果"),
    "d-verify-1": ("verification", "AI 校验结果"),
    "deliver": ("delivery", "最终结论与停止点"),
    "d-deliver": ("delivery", "最终结论与停止点"),
}


def observations_for(record: RunRecord) -> list[dict]:
    """This run's own business output, step by step, with no token data."""
    observations = []
    for step in record.steps:
        mapped = OBSERVATION_PHASES.get(step.phase)
        if mapped is None:
            # A deliberate D-mode duplicate, or a structural placeholder.
            continue
        role, label = mapped
        observations.append(
            {
                "role": role,
                "label": label,
                "phase": step.phase,
                "action": step.action,
                "status": step.status,
                "text": step.result,
                "facts": [fact.model_dump() for fact in (step.facts or [])],
                "executed": step.status != "not_executed",
            }
        )
    return observations


def baseline_for(record: RunRecord) -> dict:
    """场景验收基准 — written before the run, shown for comparison only."""
    matches = record.request_text.strip() == (record.scenario_request_text or "").strip()
    return {
        "label": "场景验收基准",
        "note": (
            "课前写定的场景答案，用来和本次实际识别结果对照。"
            "它不是本次运行产生的，不能当作 AI 的输出展示。"
        ),
        "matches_request": matches,
        "mismatch_note": None
        if matches
        else "本次输入与场景原始请求不一致，下面的基准已不适用，只看上方实际结果。",
        "scenario_request_text": record.scenario_request_text,
        "known": list(record.known),
        "missing": list(record.missing),
        "next_actions": list(record.next_actions),
        "human_gates": list(record.human_gates),
    }


def front_view(record: RunRecord) -> dict:
    """Demo 1 业务正面：本次运行的实际结果 + 场景基准；无 Token、无调用次数。"""
    payload = record.model_dump(include=set(FRONT_FIELDS))
    payload["observations"] = observations_for(record)
    payload["baseline"] = baseline_for(record)
    return payload


def back_view(record: RunRecord) -> dict:
    """Demo 2 运行背面：步骤、usage、输出与异常。

    `output_evidence` / `truncated_steps` travel inside the record itself (see
    `RunRecord`), so a replayed record always reports truncation from its own
    steps. The two readiness flags are added here because they are properties,
    and the back page must be able to show 计量完整 and 输出完整 as two separate
    facts rather than one verdict.
    """
    payload = record.model_dump()
    payload["classroom_ready"] = record.classroom_ready
    payload["freeze_ready"] = record.freeze_ready
    return payload


# --------------------------------------------------------------------------
# Demo 1 的实时执行视图
# --------------------------------------------------------------------------

# 每一步在课堂上怎么说。两个说法：还没跑完时念第一个，跑完了念第二个。
# 这里只有业务口径——Demo 1 的执行过程不出现 Token、模型名、调用次数。
LIVE_STEP_LABELS: dict[str, tuple[str, str]] = {
    "direct": ("正在直接回答客户问题……", "已直接回答客户问题"),
    "context": ("正在装载当前可用业务资料……", "已装载当前可用业务资料"),
    "answer": ("正在基于全量上下文形成结果……", "已形成结果"),
    "parse": ("正在理解客户需求……", "已理解客户需求"),
    "d-parse-1": ("正在理解客户需求……", "已理解客户需求"),
    "gaps": ("正在识别完成任务还缺什么……", "已识别缺失条件"),
    "facts": ("正在获取业务事实……", "已获取业务事实"),
    "d-context-1": ("正在获取业务事实……", "已获取业务事实"),
    "judge": ("正在做业务判断……", "已完成业务判断"),
    "d-judge-strong": ("正在做业务判断……", "已完成业务判断"),
    "verify": ("正在校验结果……", "已完成校验"),
    "d-verify-1": ("正在校验结果……", "已完成校验"),
    "deliver": ("正在形成最终交付结果……", "已形成最终交付结果"),
    "d-deliver": ("正在形成最终交付结果……", "已形成最终交付结果"),
}
LIVE_STEP_FALLBACK = ("正在处理这一步……", "已完成这一步")

# 这些字段如果出现在 Demo 1 的执行过程里，就等于把 Token 提前泄底。
# 由测试守住，不是靠自觉。
LIVE_FORBIDDEN_FIELDS = (
    "input_tokens",
    "output_tokens",
    "cached_tokens",
    "total_tokens",
    "model_calls",
    "tool_calls",
    "latency_ms",
    "finish_reason",
    "truncated",
    "usage",
    "model",
)


def live_step_labels(phase: str) -> tuple[str, str]:
    return LIVE_STEP_LABELS.get(phase, LIVE_STEP_FALLBACK)


def live_plan(steps: list[StepRecord]) -> list[dict]:
    """执行前把这条链要走的步骤交给页面（只有步骤名，没有状态）。

    页面拿到的是「打算做什么」，每一步到底是完成、被阻塞还是停下等人，只能由
    真实执行推过来的事件填上去。
    """
    plan = []
    for step in steps:
        running, done = live_step_labels(step.phase)
        plan.append(
            {
                "step": step.step,
                "phase": step.phase,
                "action": step.action,
                "running_label": running,
                "done_label": done,
            }
        )
    return plan


def live_step_start(step: int, phase: str, action: str) -> dict:
    """一步真的开始执行了。页面上的「正在……」由这条事件点亮。"""
    running, _ = live_step_labels(phase)
    return {
        "type": "step_start",
        "step": step,
        "phase": phase,
        "action": action,
        "running_label": running,
    }


def live_step(step: StepRecord) -> dict:
    """一步真实执行的业务侧投影：只说做了什么、结果如何，不说花了多少。"""
    running, done = live_step_labels(step.phase)
    return {
        "type": "step",
        "step": step.step,
        "phase": step.phase,
        "action": step.action,
        "status": step.status,
        "running_label": running,
        "done_label": done,
        # 工具事实三态原样带过来：拿到了 ≠ 能用，这一步就是讲这个的。
        "facts": [
            {
                "title": fact.title,
                "state": fact.state,
                "state_label": fact.state_label,
                "note": fact.note,
            }
            for fact in (step.facts or [])
        ],
    }


# --------------------------------------------------------------------------
# Demo 2 的动态视图：Token 累计重放
# --------------------------------------------------------------------------

# 重放画面上的「当前动作」。这是业务口径的动词短语，和记录里存的步骤名分开：
# 记录里是 action 原文（第 1 步「解析客户需求」），课堂投屏念的是这里的话。
REPLAY_ACTION_LABELS: dict[str, str] = {
    "direct": "正在直接回答客户问题",
    "context": "正在装载当前可用业务资料",
    "answer": "正在基于全量上下文生成结果",
    "parse": "正在解析客户需求",
    "d-parse-1": "正在解析客户需求",
    "gaps": "正在判断缺口",
    "facts": "正在获取业务事实",
    "d-context-1": "正在获取业务事实",
    "judge": "正在做业务判断",
    "d-judge-strong": "正在做业务判断",
    "verify": "正在校验",
    "d-verify-1": "正在校验",
    "deliver": "正在形成最终结果",
    "d-deliver": "正在形成最终结果",
}


def replay_frames(record: RunRecord) -> tuple[list[dict], bool]:
    """把一条记录拆成逐帧的 Token 累计序列。

    每一帧的 ``from_tokens`` / ``to_tokens`` 都是在这里加出来的，浏览器只负责
    把数字从前者滚动到后者——前端不做任何加法，也就没有地方可以编造中间值。

    ``measured`` 是「每一步模型调用都返回了 usage」。工具步骤的 Token 增量是 0，
    那是它真实的增量，不是缺失；模型步骤没有 usage 则是缺失，此时它的 to_tokens
    等于 from_tokens，由 ``measured=False`` 说明这一段不能当完整结果累计。

    ``cached_tokens`` 不参与累加：它是 input_tokens 的组成部分，再加一次就是把
    同一批 Token 数两遍。
    """
    frames: list[dict] = []
    running = 0
    measured = True

    for index, step in enumerate(record.steps, start=1):
        start = running

        if step.model:
            kind = "model"
            if step.input_tokens is None or step.output_tokens is None:
                step_tokens = None
                measured = False
                note = "本次模型调用：provider 没有返回 usage"
                delta_label = "该步 Token 未计量"
            else:
                step_tokens = step.input_tokens + step.output_tokens
                running += step_tokens
                note = f"本次模型调用：输入 {step.input_tokens} + 输出 {step.output_tokens}"
                delta_label = f"本步模型 Token +{step_tokens}"
        elif step.tool_calls:
            kind = "tool"
            step_tokens = 0
            # 课堂念的是工具的中文标题（记录里 facts 带 title）；只有名单时退回名字。
            titles = [fact.title for fact in (step.facts or [])] or list(step.tools)
            note = f"调用 {step.tool_calls} 个业务工具" + (
                f"：{'、'.join(titles)}" if titles else ""
            )
            delta_label = "本步模型 Token +0"
        else:
            kind = "none"
            step_tokens = 0
            note = "本步既没有模型调用，也没有工具调用"
            delta_label = "本步模型 Token +0"

        frames.append(
            {
                "index": index,
                "step": step.step,
                "phase": step.phase,
                "action": step.action,
                # 步骤条上的短名：记录的 action 原文在冒号后还有一句自我说明
                # （「校验：不得把未核验资料写成事实」），念出来太长。
                "short_label": step.action.split("：")[0],
                "action_label": REPLAY_ACTION_LABELS.get(step.phase, "正在处理这一步"),
                "kind": kind,
                "status": step.status,
                "model": step.model,
                "tool_calls": step.tool_calls,
                "input_tokens": step.input_tokens,
                "output_tokens": step.output_tokens,
                "step_tokens": step_tokens,
                "measured": step_tokens is not None,
                "from_tokens": start,
                "to_tokens": running,
                "note": note,
                "delta_label": delta_label,
            }
        )

    return frames, measured


def replay_view(record: RunRecord) -> dict:
    """Demo 2 的「这一条记录是怎么把 Token 长出来的」。

    全部数据来自已存记录本身：重放不重新调用 provider，也不做任何推测。
    """
    frames, all_measured = replay_frames(record)
    model_frames = [frame for frame in frames if frame["kind"] == "model"]
    final_tokens = frames[-1]["to_tokens"] if frames else 0

    # 最后一帧必须等于记录自己报的合计，否则这份记录不自洽。
    totals_match = (
        record.usage.total_tokens is not None and final_tokens == record.usage.total_tokens
    )
    complete = bool(model_frames) and all_measured and totals_match

    warnings: list[str] = []
    if record.evidence_level != "live":
        warnings.append(
            "这次没有真实模型调用：页面上的只是调用链结构，Token 字段全部为 null，"
            "没有 Token 可以重放。"
        )
    if record.token_evidence == "not_reported":
        warnings.append(
            "provider 没有返回 usage：这是真实模型调用，但没有任何 Token 读数，"
            "不能作为 Token 实验记录。"
        )
    elif record.token_evidence == "partial":
        warnings.append("只有部分模型调用返回了 usage：Token 合计不完整，只能作为参考。")
    if model_frames and not all_measured:
        warnings.append(
            "有模型步骤没有 Token 读数：本次重放的累计值只是已计量步骤的小计，"
            "不能当作完整结果。"
        )
    if record.output_evidence == "truncated":
        steps = "、".join(str(index) for index in record.truncated_steps)
        warnings.append(
            f"第 {steps} 步的输出被长度上限截断：Token 读数依然真实，"
            "但这一次的输出不完整，不适合按正常结果讲。"
        )
    elif record.output_evidence == "unknown":
        warnings.append("provider 没有返回 finish_reason：输出的完整性未获证明。")
    if not frames:
        warnings.append("这份记录里没有步骤，没有过程可以重放。")
    elif not model_frames and record.evidence_level == "live":
        warnings.append("这份记录里没有模型调用，没有 Token 可以累计。")
    if model_frames and all_measured and not totals_match:
        warnings.append(
            "逐帧累计值与记录里的 Token 合计不一致：这份记录不自洽，不能用于课堂重放。"
        )

    return {
        "source": "run_record",
        "run_id": record.run_id,
        "created_at": record.created_at,
        "scenario": record.scenario,
        "mode": record.mode,
        "mode_label": record.mode_label,
        "request_text": record.request_text,
        "run_status": record.run_status,
        "frames": frames,
        "final_tokens": final_tokens,
        # complete：累计值等于记录自己的 usage.total_tokens，可以当完整结果讲。
        # playable：这份记录本来就是一节可以正常演示的课堂记录。
        "complete": complete,
        "playable": bool(record.classroom_ready and record.freeze_ready and model_frames),
        "classroom_ready": record.classroom_ready,
        "freeze_ready": record.freeze_ready,
        "warnings": warnings,
        "totals": {
            "business_tasks": 1,
            "model_calls": record.usage.model_calls,
            "tool_calls": record.usage.tool_calls,
            "total_tokens": record.usage.total_tokens,
            "run_status": record.run_status,
        },
    }
