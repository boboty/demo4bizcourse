# Round 6A Acceptance Checklist

## A. Engineering freeze

- [ ] Round 1–5 工程代码、task schema、Suite、Run Plan、Failure taxonomy、Flaky 判据未被本轮修改。
- [ ] `python3 -m pytest`：34 passed。
- [ ] `git diff --check`：PASS。
- [ ] 未修改任何课件文件。
- [ ] 未增加 Suite parallel、device pool、scheduler、dashboard 或 Agent planner。

## B. Demo 0

- [ ] 自然语言 case 可打开。
- [ ] AI draft 可打开，并明确它是静态/真实生成后资产，不是现场自动生成保证。
- [ ] review notes 可打开。
- [ ] 最终 `cases/pay_order.yaml` 与 schema v1 可打开。

## C. Demo 1 TRUE_DEVICE

- [ ] physical iPhone、Safari、Appium/XCUITest、WDA 前置通过。
- [ ] V1 baseline PASS。
- [ ] V2 + old locator 真实 failure。
- [ ] Failure Bundle 有真实 page source，`#pay-now` 匹配数=0。
- [ ] Candidate 来源明确：LIVE 或预先保存的真实 Candidate。
- [ ] Review deterministic Gate APPROVED。
- [ ] Candidate Verify=3/3。
- [ ] Write Back 只改变 locator。
- [ ] AI-off final rerun PASS。
- [ ] restore 后 baseline 可恢复、旧 locator failure 可再次制造。

## D. Demo 2

- [ ] Suite execution_mode=serial。
- [ ] Run Plan execution_mode=serial。
- [ ] Round 4 result 展示 total=5、passed=4、failed=1。
- [ ] PRODUCT BUG evidence 保留真实 UI/API facts，不改 expected assertions。
- [ ] before/after commit retry history 可展示。
- [ ] Failure Cause 展示四类与 UNCLASSIFIED。
- [ ] Flaky 展示 12/6/6、AUTOMATION、FLAKY。
- [ ] Shared State 展示同一 order_id、两个 timeline、状态污染。

## E. Claim accuracy

- [ ] 没有把 controlled local experiment 写成 TRUE_DEVICE。
- [ ] 没有把 Run Plan test result FAIL 写成 PASS。
- [ ] 没有把 FLAKY 写成 Failure Cause。
- [ ] 没有声称 Suite 支持 parallel。
- [ ] 没有声称存在 multi-device pool 或 cron daemon。
- [ ] 没有声称 Agent 可以自由改变正式 regression path。
- [ ] 没有声称四种 Failure 都来自真机。

## F. Git / evidence policy

- [ ] `instructor/` 课堂资产属于 `track`。
- [ ] `artifacts/` 原始运行输出、history、日志、截图、设备信息保持 `ignore`。
- [ ] 公开只使用脱敏摘要和静态文档；不提交真实 Appium log、device info、session id 或真机截图。
