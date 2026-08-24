# 4-Demo Classroom Runbook

本 Runbook 将课堂固定为 Gate + 四个 Demo。课堂 Python 统一使用项目 `.venv`；每个新 Terminal 都重新执行 `source .venv/bin/activate`。不改变 app 业务语义、`cases/pay_order.yaml`、`suites/nightly.yaml`、`schedules/nightly.yaml`、self-heal 治理规则、Failure taxonomy、Stability 判据或已有真实 evidence 数字。

## 0. Gate

首次准备（项目目录内）：

```bash
python3 -m venv .venv  # 仅在 .venv 不存在时执行
source .venv/bin/activate
python -m pip install -r requirements.txt
```

正式 Gate：

```bash
source .venv/bin/activate
python -m pytest
git diff --check
```

Gate 只确认命令成功，不在 Runbook 中硬编码测试数量。每个后续新 Terminal 的第一行都要重新执行：

```bash
source .venv/bin/activate
```

同时保留 `./scripts/preflight_ios.sh`，并保留人工门禁：启动 Appium 时必须观察到 XCUITest Driver 真实 load 成功；出现 `Could not load driver` 立即 STOP。

课堂只保留一张可选 STATIC BRIDGE 卡：

> 测试用例 ≠ 可执行测试任务；本课从执行开始。

不再要求课堂逐个打开自然语言用例、AI draft 或 review notes。

## Demo 1：移动端真机自动化框架搭建

目的不是业务支付测试，而是证明：

```text
Mac → Appium → XCUITest Driver → WebDriverAgent → XCTest → 真实 iPhone Safari
```

Android 只讲架构：`Android：Appium → UiAutomator2 Driver → ADB → UiAutomator2 Server / UiAutomator → Android`。课堂不增加 Android 真机 live。

### Live 顺序

1. 新 Terminal：`source .venv/bin/activate`，执行 `./scripts/preflight_ios.sh`。
2. 启动 Appium，完成 XCUITest Driver load 人工 Gate。
3. 执行 `appium driver run xcuitest open-wda`。
4. 在 Xcode 展示 `WebDriverAgentRunner`、Signing、Personal Team 和 Bundle ID，执行 `Product → Test`。
5. 观察 iPhone 出现 `Automation Running`；明确停止 Xcode Test 后再进入 Round0。
6. 新 Terminal 重新 source `.venv`，检查 8000 和 4723 是否空闲。若占用，只定位进程，不盲杀：

   ```bash
   source .venv/bin/activate
   lsof -nP -iTCP:8000 -sTCP:LISTEN
   lsof -nP -iTCP:4723 -sTCP:LISTEN
   ```

7. 使用 `IOS_UDID`、`IOS_TEAM_ID`、`IOS_WDA_BUNDLE_ID` 执行 Round0：

   ```bash
   source .venv/bin/activate
   MAC_LAN_IP='<MAC-LAN-IP>' IOS_UDID='<IPHONE-UDID>' IOS_TEAM_ID='<APPLE-TEAM-ID>' \
   IOS_WDA_BUNDLE_ID='<PERSONAL-WDA-BUNDLE-ID>' ROUND0_WAIT_FOR_ENTER=1 \
   python scripts/run_round0_ios.py
   ```

8. 观察 Safari 自动打开、`#round0-action` 自动点击、页面状态改变和 screenshot evidence；用 QuickTime 人工确认投屏。

`run_round0_ios.py` 自己占用 8000 和 4723，因此 T-30 / Demo 1 之前不要启动 FastAPI 或独立 Appium。Demo 1 结束后，才允许启动 FastAPI。

### 讲师判断

- 这是 TRUE_DEVICE 框架链路 Gate，不是业务支付 PASS。
- Xcode Test 停止、Round0 完整、投屏确认后，才进入 Demo 2。
- Round0 baseline 失败就 STOP，不跳到后续 UI Self-Heal。

## Demo 2：接口自动化执行

Demo 1 完成后启动 FastAPI，并保持运行供 Demo 3 使用。新 Terminal 先 source：

```bash
source .venv/bin/activate
./scripts/reset_demo.sh
./scripts/start_demo.sh
```

检查 localhost 和 LAN `/health`，并确认 iPhone Safari 可以访问业务页：

```bash
source .venv/bin/activate
curl -fsS http://127.0.0.1:8000/health
curl -fsS http://<MAC-LAN-IP>:8000/health
```

课堂核心：重复的事情继续交给确定性工具；Agent 不替代 HTTP executor。API wrapper 只编排现有 `tools/api.py`、Skills 和 `runner/retry_policy.py`，不复制业务规则，也不描述成“Agent 亲自发 HTTP 请求”。

### API-only 课堂入口

```bash
source .venv/bin/activate
python instructor/run_api_demo.py normal
python instructor/run_api_demo.py timeout-before
python instructor/run_api_demo.py timeout-after
```

需要一次性完整演示时可执行：

```bash
source .venv/bin/activate
python instructor/run_api_demo.py all
```

`normal` 顺序固定为：`reset → config normal → prepare → POST pay → GET facts → 固定断言 → cleanup`。

`timeout-before` 必须现场看到：`HTTP 504`、业务 facts 未提交、`RETRY_ALLOWED`、只 Retry 一次、最终 facts PASS。

`timeout-after` 必须现场看到：`HTTP 504`、业务 facts 已提交、`NO_RETRY_ALREADY_COMMITTED`、不发送第二次支付请求。

wrapper 会把结构化课堂 artifact 保存到被 Git 忽略的 `artifacts/runs/api-demo/`；运行日志、请求结果和历史只作 `ignore` runtime，不提交原始运行数据。

课堂判断：**脚本负责执行明确规则；Agent 的价值从需要结合上下文进行可验证判断开始。**

## Demo 3：真机 UI + AI Self-Heal

将真机 UI Self-Heal 主体放在这里，保留所有真实 evidence Gate。FastAPI 已由 Demo 2 启动并继续运行。

### 01 Business baseline

保持已经验证通过的完整 runtime 命令：

```bash
source .venv/bin/activate

MAC_LAN_IP='<MAC-LAN-IP>' \
IOS_UDID='<IPHONE-UDID>' \
IOS_TEAM_ID='<APPLE-TEAM-ID>' \
IOS_WDA_BUNDLE_ID='<PERSONAL-WDA-BUNDLE-ID>' \
python scripts/run_pay_order_ios.py
```

baseline FAIL → STOP，不进入 Self-Heal。FAIL 时保留当前 step、error、cleanup error 和 evidence 目录输出。

### 02 Real Failure Bundle

这一节只负责 V1 baseline evidence → V2 → 旧 locator `#pay-now` 真实失败 → 保存完整 Failure Bundle：

```bash
source .venv/bin/activate
./scripts/restore_self_heal_baseline.sh

MAC_LAN_IP='<MAC-LAN-IP>' IOS_UDID='<IPHONE-UDID>' IOS_TEAM_ID='<APPLE-TEAM-ID>' IOS_WDA_BUNDLE_ID='<PERSONAL-WDA-BUNDLE-ID>' \
python scripts/run_round2_self_heal.py --stop-after-failure
```

课堂必须看到：

- `STOPPED_AFTER_REAL_FAILURE`
- `failure_step=pay_order`
- old locator = `#pay-now`
- old locator DOM match = `0`
- `EXPECTED_LOCATOR_FAILURE`
- 脚本打印真实 failure bundle 路径

这一步内部再次执行 V1 baseline 是正常的：它让同一个 Failure Bundle 携带 V1 baseline PASS 证据，不重复 Demo 3 01 的教学目的。

### 03 Interactive AI Candidate

#### 自动定位真实 Failure Bundle

```bash
source .venv/bin/activate
FAILDIR=$(find evidence -maxdepth 2 -type d -name 'v2-old-locator-failure' -print | sort | tail -1)
echo "$FAILDIR"
test -f "$FAILDIR/failure-context.json" && \
test -f "$FAILDIR/page-source.html" && \
test -f "$FAILDIR/failure-screenshot.png" && \
echo "Failure Bundle: READY"
```

不要使用 `ls -td evidence/round2-*`，因为它会错误匹配 `evidence/round2-pass-summary.md`。

#### 03A Generate Codex Task

```bash
source .venv/bin/activate
FAILDIR=$(find evidence -maxdepth 2 -type d -name 'v2-old-locator-failure' -print | sort | tail -1)
PROMPT_FILE="/tmp/round2-candidate-prompt.txt"
python scripts/render_round2_candidate_prompt.py \
  "$FAILDIR/failure-context.json" \
  "$FAILDIR/page-source.html" \
  "$FAILDIR/failure-screenshot.png" \
  | tee "$PROMPT_FILE"
pbcopy < "$PROMPT_FILE"
```

课堂动作：Prompt 已复制到剪贴板；打开当前仓库中的交互式 Codex，Cmd+V 粘贴并执行。Codex 会自行读取三个真实 Failure Bundle 文件，并直接写入 `artifacts/runs/interactive/round2-candidate.json`，不需要讲师再复制 JSON。若当前 Codex 环境无法读取图片文件，再人工拖入 screenshot 作为 fallback，但不是默认主流程。AI 输入是 Failure Context + Old Locator + Target Semantic + Real DOM + Real Screenshot + Restricted Output Schema，而不是一句“按钮坏了，帮我修”。主页面不提前泄露 locator 答案。

#### 03B Check Candidate

```bash
source .venv/bin/activate
CANDIDATE="artifacts/runs/interactive/round2-candidate.json"
test -f "$CANDIDATE" && echo "Candidate: READY"
python -m json.tool "$CANDIDATE"
```

课堂必须看到 `Candidate: READY`；JSON 顶层只能包含 `target`、`old_locator`、`candidate`、`evidence`。`artifacts/runs/interactive/` 必须保持 ignored runtime，不提交 Git。

课堂判断：**AI 不需要把建议交给人搬运，但它也不能因为能写文件，就获得修改正式资产的权力。** AI Candidate ≠ 正式资产。

### 04 Deterministic Gate & Asset

自动重新定位真实 Failure Bundle，并导入固定 Candidate：

```bash
source .venv/bin/activate
FAILDIR=$(find evidence -maxdepth 2 -type d -name 'v2-old-locator-failure' -print | sort | tail -1)
CANDIDATE="artifacts/runs/interactive/round2-candidate.json"

MAC_LAN_IP='<MAC-LAN-IP>' \
IOS_UDID='<IPHONE-UDID>' \
IOS_TEAM_ID='<APPLE-TEAM-ID>' \
IOS_WDA_BUNDLE_ID='<PERSONAL-WDA-BUNDLE-ID>' \
python scripts/run_round2_self_heal.py \
  --failure-dir "$FAILDIR" \
  --interactive-candidate "$CANDIDATE"
```

这一条命令本身完成后续完整链路：

```text
Interactive Candidate
        ↓
Import
        ↓
Review / Policy Gate
        ↓
Unique DOM Match = 1
        ↓
True-device Verify 3/3
        ↓
Write Back
        ↓
AI-off V2 rerun
        ↓
Restore baseline
        ↓
再次制造 old-locator failure
        ↓
PASS
```

必须看到：`baseline_v1 PASS`（从真实 bundle 复核）、`old_locator_failure EXPECTED_LOCATOR_FAILURE`、`ai_candidate GENERATED`、Review APPROVED、Candidate verification 3/3 PASS、`post_writeback_rerun PASS`、`baseline_restore PASS`、repeat old-locator failure 和最终 `result PASS`。

课堂核心判断：第一次证明 AI 能找到变化；第二次证明系统没有把 AI 的不确定性直接带进正式回归。

### 安全复位 / 中断恢复

正常 Demo 3 PASS 后只是额外安全收口；如果中途异常，可人工执行：

```bash
source .venv/bin/activate
./scripts/restore_self_heal_baseline.sh
./scripts/reset_demo.sh
```

这不是 AI-off rerun evidence，也不是 Self-Heal 主链的一部分。

不得削弱 baseline、Failure Bundle、Interactive Candidate、Review / Policy Gate、3/3 Verify、Write Back、AI-off rerun、restore 或 repeat-failure 的真实证据要求。

## Demo 4：从 Case 到可信执行系统

将原规模化展示放在这里。正式 Suite 仍然只说 `serial`；不要声称已经有通用 parallel executor、device pool、cron daemon 或 dashboard。

保持完整链路：

```text
Case → Suite → Run Plan → Evidence → Report → Failure Cause → Stability → Test Independence
```

课堂展示：`cases/pay_order.yaml`、`suites/nightly.yaml`、`schedules/nightly.yaml`、脱敏真实 `evidence/round4-pass-summary.md`、本机 report / artifact，以及业务语义 Retry history。不要修改这些正式资产。

Retry History 真实定位：

```bash
find artifacts/runs -type f -name retry_history.json -print | sort
```

从真实运行产物中选择 `timeout_before_commit` 与 `timeout_after_commit` 对应的 `retry_history.json`；需要查看时执行 `open <真实路径>`。

可现场执行：

```bash
source .venv/bin/activate
python -m experiments.failure_classification
```

Shared-state / flaky 按课堂时间和需要展示保存结果或短实验，不改变既有判据。保留课堂结论：

- `Engineering acceptance PASS`
- `Run Plan execution completed`
- `Test Run Result FAIL`
- 测试系统成功完成了一次失败的测试。

现有脱敏真实 evidence 数字原样保留，包括 Round 4 的 `total=5、passed=4、failed=1`；不要用新运行数字替换它们。

## Demo 后 Reset

```bash
source .venv/bin/activate
./scripts/restore_self_heal_baseline.sh
./scripts/reset_demo.sh
```

人工关闭 FastAPI、Appium、QuickTime；保留 ignored runtime evidence 供课后核验，不把原始日志、截图、设备信息或历史运行记录加入 Git。
