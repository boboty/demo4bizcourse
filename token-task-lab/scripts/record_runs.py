#!/usr/bin/env python3
"""课前把 A/B/C/D 真实跑一遍，存成课堂可回放的记录。

    export LLM_BASE_URL=...   # 例如 https://api.openai.com/v1
    export LLM_API_KEY=...
    export LLM_MODEL=...
    export LLM_STRONG_MODEL=...   # 可选；D 档用它演示「不必要的强模型」

    python scripts/record_runs.py            # 跑全部四档
    python scripts/record_runs.py C D        # 只跑指定档

每一档都是一次真实调用，记录只写 provider 返回的数字。若 provider 没有配置，
脚本会拒绝运行——它不会生成任何占位的 Token 数字。
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.config import load_provider_config, runs_dir  # noqa: E402
from app.engine import MODES, RunEngine  # noqa: E402
from app.provider import OpenAICompatibleProvider  # noqa: E402
from app.scenarios import get_scenario  # noqa: E402
from app.store import RunStore  # noqa: E402

DEFAULT_SCENARIO = "tianjin-freight"


def fmt(value: int | None) -> str:
    return "—" if value is None else f"{value:,}"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("modes", nargs="*", default=list(MODES), help="要跑的档位，默认 A B C D")
    parser.add_argument("--scenario", default=DEFAULT_SCENARIO)
    parser.add_argument("--request-text", default="")
    args = parser.parse_args()

    modes = [m.upper() for m in args.modes]
    unknown = [m for m in modes if m not in MODES]
    if unknown:
        print(f"未知档位：{', '.join(unknown)}；可用：{', '.join(MODES)}", file=sys.stderr)
        return 2

    scenario = get_scenario(args.scenario)
    if scenario is None:
        print(f"未知 scenario：{args.scenario}", file=sys.stderr)
        return 2

    config = load_provider_config()
    if not config.configured:
        print(
            "provider 未配置，缺少：" + "、".join(config.missing_settings),
            file=sys.stderr,
        )
        print("本脚本只做真实运行；没有 provider 时请改用结构示例记录。", file=sys.stderr)
        return 1

    request_text = args.request_text.strip() or scenario.request_text
    engine = RunEngine(provider=OpenAICompatibleProvider(config), config=config)
    store = RunStore(runs_dir())
    # 同一次执行的四档共用一个 experiment_id：课堂上可以说清这是同一件任务、同一批实验。
    experiment_id = str(uuid4())

    print(f"provider      : {config.base_url}  model={config.model}"
          f"  strong={config.strong_model or '(未配置，D 档回退同一模型)'}")
    print(f"scenario      : {scenario.key}  输出目录：{store.root}")
    print(f"experiment_id : {experiment_id}\n")

    rows = []
    failures = []
    unmeasured = []
    truncated = []
    for mode in modes:
        print(f"运行 {mode} ...", end=" ", flush=True)
        record = engine.execute(
            scenario=scenario,
            mode=mode,
            request_text=request_text,
            experiment_id=experiment_id,
        )
        usage = record.usage
        print(
            f"{record.run_status}  调用 {usage.model_calls} 次模型 / {usage.tool_calls} 次工具  "
            f"输入 {fmt(usage.input_tokens)}  输出 {fmt(usage.output_tokens)}  "
            f"缓存 {fmt(usage.cached_tokens)}  耗时 {fmt(usage.latency_ms)}ms"
        )
        if record.error:
            # 一次失败的调用不是一份可回放的记录：照实报出来，但不留在 runs/ 里。
            failures.append(record)
            print(f"    错误：{record.error}  ——未保存")
            continue
        if not record.classroom_ready:
            # 真的调了模型，但 provider 没给 Token 读数。这是真实运行，不是 Token 实验记录。
            unmeasured.append(record)
            print(
                f"    警告：token_evidence={record.token_evidence}，"
                "本次模型真实运行，但不能作为 Token 实验记录  ——已保存并标记"
            )
        if record.output_evidence == "truncated":
            # 计量完整但输出不完整：数字是真的，内容却只有前半段。
            truncated.append(record)
            print(
                "    警告：第 "
                + "、".join(str(index) for index in record.truncated_steps)
                + " 步被长度上限截断（finish_reason=length），输出不完整"
                "  ——已保存并标记，不可用于课堂冻结"
            )
        elif record.output_evidence == "unknown":
            print("    提示：provider 未上报 finish_reason，输出完整性无法确认  ——已保存并标记")
        rows.append((record, store.save(record)))

    if rows:
        print("\n已保存：")
        for record, path in rows:
            mark = "" if record.classroom_ready else f"  [{record.token_evidence}]"
            if record.output_evidence == "truncated":
                mark += f"  [输出被截断 {len(record.truncated_steps)} 次]"
            elif record.output_evidence == "unknown":
                mark += "  [finish_reason 未上报]"
            print(
                f"  [{record.mode}] {record.run_id}{mark}"
                f"  ->  {path.relative_to(store.root.parent)}"
            )
        ready = [record for record, _ in rows if record.classroom_ready]
        frozen = [record for record, _ in rows if record.freeze_ready]
        print(
            f"\n课堂可用于 Token 实验的记录：{len(ready)}/{len(modes)} 档"
            f"（experiment_id={experiment_id}）"
        )
        # 计量完整与输出完整是两个判断，分开报：可冻结要求两者同时成立。
        print(
            f"适合课堂冻结的档位：{len(frozen)}/{len(modes)} 档"
            "（Token 已计量 且 无 finish_reason=length 截断）"
        )

    # 对比表放在成败判定之前：截断或失败时更需要看见这张表，而不是被跳过。
    live = [record for record, _ in rows if record.evidence_level == "live"]
    if live:
        print("\n各档对比（全部来自本次真实调用）：")
        header = (
            f"{'档位':<4}{'模型调用':>8}{'工具调用':>8}{'输入':>12}{'输出':>10}"
            f"{'缓存':>10}{'耗时ms':>10}{'截断':>6}"
        )
        print(header)
        print("-" * len(header))
        for record in live:
            u = record.usage
            print(
                f"{record.mode:<4}{u.model_calls:>8}{u.tool_calls:>8}"
                f"{fmt(u.input_tokens):>12}{fmt(u.output_tokens):>10}"
                f"{fmt(u.cached_tokens):>10}{fmt(u.latency_ms):>10}"
                f"{len(record.truncated_steps):>6}"
            )
        print("截断 > 0 的档位输出不完整，不要作为完整结果使用。")

    exit_code = 0
    if truncated:
        print(
            f"\n有 {len(truncated)} 档输出被长度上限截断（{', '.join(r.mode for r in truncated)}）："
            "Token 读数完整，但那几次调用只写了前半段。\n"
            "这组记录已保存并标记为不可冻结，不要用作课件数字；"
            "请按提示里的字数上限收紧该步骤的提示词后重跑。",
            file=sys.stderr,
        )
        exit_code = 1
    if failures:
        print(
            f"\n有 {len(failures)} 档失败未保存（{', '.join(r.mode for r in failures)}）。"
            "先修好 provider 再重跑，课堂不要拿半截记录讲。",
            file=sys.stderr,
        )
        exit_code = 1
    if unmeasured:
        print(
            f"\n有 {len(unmeasured)} 档没有 Token 读数（{', '.join(r.mode for r in unmeasured)}）："
            "provider 真实返回了回答但没有返回 usage。\n"
            "这些记录不能用于 Token 对比实验，也不会计入课堂可用记录。"
            "请换一个会返回 usage 的 provider 或网关后重跑。",
            file=sys.stderr,
        )
        exit_code = 1

    if exit_code:
        return exit_code

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
