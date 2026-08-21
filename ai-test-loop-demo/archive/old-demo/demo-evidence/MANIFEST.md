# demo-evidence 清单

每一项证据都配一条可重跑命令；命令在仓库根目录（`ai-test-loop-demo/`）下、激活 `.venv` 后执行。所有命令已在写这份 MANIFEST 时逐条重跑验证过。

## page30/counterfactual/ — 反证实验（第35页证据来源）

| 文件 | 内容 | 重跑命令 |
|---|---|---|
| `service.diff` | 注入 BUG 的实现 vs 真实实现的 diff（14 行新增） | `python experiments/counterfactual/run_counterfactual.py` |
| `service-diff.png` | 上面那份 diff 的 1920×1080 可读版 | `python demo-evidence/tools/render_card.py --text-file demo-evidence/page30/counterfactual/service.diff --out demo-evidence/page30/counterfactual/service-diff.png --title "app/service.py vs 反证实验注入的 BUG 实现" --subtitle "experiments/counterfactual/service_buggy.py — 14 行新增，其余原样"` |
| `generated-suite-output.txt` | 同一份 BUG 实现下，`tests/generated/` 的独立执行结果（4 passed，全绿） | `python experiments/counterfactual/run_counterfactual.py` |
| `generated-suite-output.png` | 上面结果的 1920×1080 可读版 | `python demo-evidence/tools/render_card.py --text-file demo-evidence/page30/counterfactual/generated-suite-output.txt --out demo-evidence/page30/counterfactual/generated-suite-output.png --title "tests/generated/ 在 BUG 实现下的独立执行结果" --subtitle "python experiments/counterfactual/run_counterfactual.py"` |
| `verified-suite-output.txt` | 同一份 BUG 实现下，`tests/verified/` 的独立执行结果（1 failed，`assert 0 == 100`） | `python experiments/counterfactual/run_counterfactual.py` |
| `verified-suite-output.png` | 上面结果的 1920×1080 可读版 | `python demo-evidence/tools/render_card.py --text-file demo-evidence/page30/counterfactual/verified-suite-output.txt --out demo-evidence/page30/counterfactual/verified-suite-output.png --title "tests/verified/ 在同一份 BUG 实现下的独立执行结果" --subtitle "python experiments/counterfactual/run_counterfactual.py"` |

`run_counterfactual.py` 一次运行会把 `app/service.py` 临时换成 `experiments/counterfactual/service_buggy.py`、跑两套件、再用 `finally` 换回来（已用 MD5 核对过还原干净），三个 `.txt` 一次性全部重新生成。

## page35/ — 独立验收驳回证据 + 课件内嵌小卡（第35页）

| 文件 | 内容 | 重跑命令 |
|---|---|---|
| `independent-review-rejection.txt` | `run_independent_review.py` 对 generated 的 REJECTED 输出 + AC-004 判据原文 + "不重跑pytest"的说明，拼在一起 | `python demo-evidence/page35/compose_review_evidence.py` |
| `independent-review-rejection.png` | 上面内容的 1920×1080 可读版 | `python demo-evidence/tools/render_card.py --text-file demo-evidence/page35/independent-review-rejection.txt --out demo-evidence/page35/independent-review-rejection.png --title "独立验收驳回 generated 套件：判据可见" --subtitle "python scripts/run_independent_review.py"` |
| `tiles/tile-bug-diff.png` | 课件内嵌小卡：注入的 BUG（只放核心 if 块，不是终端全文） | `python demo-evidence/tools/render_hero_tile.py --out-dir demo-evidence/page35/tiles` |
| `tiles/tile-generated-green.png` | 课件内嵌小卡：`4 passed`（大字号） | 同上 |
| `tiles/tile-verified-red.png` | 课件内嵌小卡：`1 failed` + `assert 0 == 100`（大字号） | 同上 |

`tiles/` 下三张是"一眼看清"的课件内嵌版（尺寸配第35页证据画廊的 2.06:1 卡片比例）；同一批内容的完整终端细节版是上面 `page30/counterfactual/` 里的三张 1920×1080 图，两者互为详略对照，来源是同一次 `run_counterfactual.py` 运行。

## 工具

| 文件 | 用途 |
|---|---|
| `tools/render_card.py` | 把任意文本文件渲染成 1920×1080 终端风格图，自动换行、自动调字号保证不截断，用于 demo-evidence 完整细节版 |
| `tools/render_hero_tile.py` | 渲染课件内嵌用的"一眼看清"小卡（大字号、1-3行关键信息），用于第35页证据画廊 |

## 脱敏对照表

| 原始内容 | 替换为 | 出现位置 |
|---|---|---|
| `<local-user>/Documents/bizcourse/Demo/ai-test-loop-demo`（本机真实用户路径，pytest `rootdir` 行自动带出） | `/workspace/ai-test-loop-demo` | `page30/counterfactual/generated-suite-output.{txt,png}`、`verified-suite-output.{txt,png}`；替换逻辑固化在 `experiments/counterfactual/run_counterfactual.py` 的 `desensitize()` 里，每次重跑都会自动生效，不需要手工二次处理 |

检查范围：`demo-evidence/` 下所有 `.txt`/`.png` 对应的源文本都过了一遍 `grep -n "yanbo\|<user-home-prefix>/"`，确认只有上表这一处命中；接口地址、字段名、token、内网域名在本仓库场景下不适用（本地 FastAPI 应用，无真实外部接口/客户数据），未发现需要替换的实例。

## 已知缺口（如实记录，不打算这一轮补）

第20、38页的演示锚点改造只涉及占位块的文字结构（现场要跑什么/分段节奏/观察点），本轮没有另外产出这两页对应的真实截图备份——因为这两页的演示内容（AI现场生成测试点/编码智能体现场执行任务包）依赖当天用哪个具体工具、跑哪个真实案例，此刻没有一次可以截图的真实运行可依据，不打算用摆拍或占位截图充数。`demo-backup.html` 目前只收录了第30/35页有真实产出的证据（OpenAPI闭环反证实验 + 独立验收驳回）。
