const fs = require('node:fs');
const path = require('node:path');
const { chromium } = require('/Users/yanbo/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');

(async () => {
  const out = path.resolve(__dirname, '../../evidence/demo-d-worker');
  fs.mkdirSync(out, { recursive: true });
  const browser = await chromium.launch({ channel: 'chrome', headless: true });
  const context = await browser.newContext({ viewport: { width: 1440, height: 1160 }, acceptDownloads: true });
  const blocked = [];
  const page = await context.newPage();
  const result = { browser: 'Chrome', external_requests_blocked: blocked, steps: [] };
  await context.route('**/*', async (route) => {
    const url = new URL(route.request().url());
    if (url.origin !== 'http://127.0.0.1:8016') { blocked.push(url.href); await route.abort(); return; }
    await route.continue();
  });
  try {
    await page.goto('http://127.0.0.1:8016/demo/d');
    await page.getByText('本地服务正常', { exact: false }).waitFor();
    const links = await page.locator('.demo-nav a').allTextContents();
    if (!links.some((item) => item.includes('Demo C')) || !links.some((item) => item.includes('Demo D'))) throw new Error('D 导航或课程互通入口缺失');
    await page.getByRole('button', { name: '一键复演至人工核查前' }).click();
    await page.getByText('辅助分析完成', { exact: false }).waitFor();
    if (!(await page.getByRole('button', { name: '3 提交人工核查' }).isEnabled())) throw new Error('复演未停在人工核查之前');
    const runId = await page.evaluate(async () => {
      const state = await (await fetch('/api/v1/d/state')).json();
      return Object.keys(state.runs)[0];
    });
    const beforeReview = await page.evaluate(async (id) => (await (await fetch('/api/v1/d/state')).json()).runs[id], runId);
    if (beforeReview.phase !== 'explained' || beforeReview.review !== null || beforeReview.brief !== null) throw new Error('复演越过人工核查，或预先生成了简报');
    if (new Set(beforeReview.audit_ids).size !== beforeReview.audit_ids.length || beforeReview.audit_ids.length !== 3) throw new Error('复演阶段审计 ID 重复或数量不符');
    if (!beforeReview.analysis.findings.some((item) => item.rule_id === 'RULE-D-AUTH-RATE') || !beforeReview.analysis.findings.some((item) => item.rule_id === 'RULE-D-OFF-HOURS') || !beforeReview.analysis.findings.some((item) => item.rule_id === 'RULE-D-REPEATED-DENY')) throw new Error('规则分析未覆盖三类预期异常');
    if (!beforeReview.analysis.normal_log_ids.includes('LOG-D-004')) throw new Error('页面样本缺少正常记录参照');
    await page.screenshot({ path: `${out}/browser-replay-before-review.png`, fullPage: true });
    result.steps.push({ name: '真实 Chrome 复演至人工核查前，三类规则和正常参照可见', result: 'PASS' });

    await page.locator('#rationale').fill('');
    await page.getByRole('button', { name: '3 提交人工核查' }).click();
    await page.getByRole('alert').getByText('人工核查必须填写理由', { exact: false }).waitFor();
    await page.screenshot({ path: `${out}/browser-error-feedback.png`, fullPage: true });
    result.steps.push({ name: '空理由被后端拒绝并显示可读错误', result: 'PASS' });

    await page.locator('#rationale').fill('原始日志只证明非工作时段出现一次成功登录；样本没有凭据来源、API 响应字节数或网络出口记录，无法支持账号失陷或数据外传。');
    await page.getByRole('button', { name: '3 提交人工核查' }).click();
    await page.getByText('人工核查已记录', { exact: false }).waitFor();
    await page.getByRole('button', { name: '4 生成四栏简报' }).click();
    await page.getByText('四栏简报已生成', { exact: false }).waitFor();
    if (await page.locator('.brief-column').count() !== 4) throw new Error('简报没有四栏');
    if (!(await page.locator('#brief').getByText('人工核查后排除', { exact: false }).count())) throw new Error('简报没有反映人工排除决定');
    const reportState = await page.evaluate(async (id) => (await (await fetch('/api/v1/d/state')).json()).runs[id], runId);
    const brief = reportState.brief;
    if (!brief || !brief['已证实事实'].length || !brief['AI 推测'].length || !brief['待核查'].length || !brief['建议动作'].length) throw new Error('四栏报告缺少可追溯项目');
    if (brief['已证实事实'].some((item) => item.text.includes('已通过 API 外传数据'))) throw new Error('AI 过度推断进入已证实事实');
    if (!brief['建议动作'][0].text.includes('不执行')) throw new Error('报告没有表明建议动作为文本');
    await page.screenshot({ path: `${out}/browser-brief-after-review.png`, fullPage: true });
    const downloadWait = page.waitForEvent('download');
    await page.getByRole('button', { name: '导出四栏简报 JSON' }).click();
    const download = await downloadWait;
    const file = `${out}/four-column-brief.json`;
    await download.saveAs(file);
    const exported = JSON.parse(fs.readFileSync(file, 'utf8'));
    if (exported.id !== brief.id || Object.keys(exported).filter((key) => ['已证实事实', 'AI 推测', '待核查', '建议动作'].includes(key)).length !== 4) throw new Error('下载 JSON 与页面简报不一致');
    const completedState = await page.evaluate(async (id) => (await (await fetch('/api/v1/d/state')).json()).runs[id], runId);
    if (new Set(completedState.audit_ids).size !== 5 || completedState.audit_ids.length !== 5) throw new Error('包含人工核查及简报的审计 ID 不唯一');
    result.steps.push({ name: '人工排除后生成四栏 JSON，各栏证据可回跳，审计ID唯一', result: 'PASS' });

    const before = await page.evaluate(async () => {
      const [a, b, c] = await Promise.all(['/api/v1/a/state', '/api/v1/state', '/api/v1/c/state'].map(async (url) => (await (await fetch(url)).json())));
      return { a: [a.runs, a.audits], b: [b.runs, b.audits], c: [c.runs, c.audits] };
    });
    await page.getByRole('button', { name: '重置 D 演示' }).click();
    await page.getByText('D 演示已重置', { exact: false }).waitFor();
    const stale = await page.evaluate(async (id) => {
      const response = await fetch(`/api/v1/d/runs/${id}/analyze`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: '{}' });
      return { status: response.status, body: await response.json() };
    }, runId);
    const after = await page.evaluate(async () => {
      const [a, b, c] = await Promise.all(['/api/v1/a/state', '/api/v1/state', '/api/v1/c/state'].map(async (url) => (await (await fetch(url)).json())));
      return { a: [a.runs, a.audits], b: [b.runs, b.audits], c: [c.runs, c.audits] };
    });
    if (stale.status !== 404 || JSON.stringify(before) !== JSON.stringify(after)) throw new Error('D 重置未使旧 run 失效或修改了 A/B/C 状态');
    await page.screenshot({ path: `${out}/browser-reset.png`, fullPage: true });
    result.steps.push({ name: 'D 独立重置清空审计和报告、旧 run 失效且 A/B/C 未改变', result: 'PASS' });

    await page.getByRole('button', { name: '一键复演至人工核查前' }).click();
    await page.getByText('辅助分析完成', { exact: false }).waitFor();
    const second = await page.evaluate(async () => {
      const state = await (await fetch('/api/v1/d/state')).json();
      const run = Object.values(state.runs)[0];
      return { counts: run.analysis.findings.map((item) => [item.rule_id, item.log_ids.length]), phase: run.phase, audits: run.audit_ids };
    });
    if (second.phase !== 'explained' || second.counts.length !== 3 || new Set(second.audits).size !== 3) throw new Error('重置后的重复复演不稳定');
    await page.getByRole('button', { name: '重置 D 演示' }).click();
    await page.getByText('D 演示已重置', { exact: false }).waitFor();
    result.steps.push({ name: '重置后重复复演阶段、规则命中及审计数稳定', result: 'PASS' });

    if (blocked.length) throw new Error(`发现外网请求：${blocked.join(', ')}`);
    result.external_requests_blocked = blocked;
    result.result = 'PASS';
  } catch (error) {
    result.result = 'FAIL';
    result.error = error.stack || String(error);
    await page.screenshot({ path: `${out}/browser-failure.png`, fullPage: true }).catch(() => {});
    throw error;
  } finally {
    fs.writeFileSync(`${out}/browser-e2e.json`, JSON.stringify(result, null, 2));
    await context.close();
    await browser.close();
  }
})().catch((error) => { console.error(error); process.exitCode = 1; });
