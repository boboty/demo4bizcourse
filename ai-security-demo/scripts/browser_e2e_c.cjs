const fs = require('node:fs');
const { chromium } = require('/Users/yanbo/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');

(async () => {
  const out = 'evidence/demo-c-worker-r2';
  fs.mkdirSync(out, { recursive: true });
  const browser = await chromium.launch({ channel: 'chrome', headless: true });
  const context = await browser.newContext({ viewport: { width: 1440, height: 1100 }, acceptDownloads: true });
  const blocked = [];
  let failNextRun = false;
  await context.route('**/*', async route => {
    const url = new URL(route.request().url());
    if (url.origin !== 'http://127.0.0.1:8016') { blocked.push(url.href); await route.abort(); return; }
    if (failNextRun && route.request().method() === 'POST' && url.pathname === '/api/v1/c/runs') {
      failNextRun = false;
      await route.fulfill({ status: 503, contentType: 'application/json', headers: { 'X-Request-ID': 'browser-failure-103' }, body: JSON.stringify({ error: { code: 'SERVICE_UNAVAILABLE', message: '浏览器注入的本地故障演示', request_id: 'browser-failure-103' } }) });
      return;
    }
    await route.continue();
  });
  const page = await context.newPage();
  const result = { browser: 'Chrome', external_requests_blocked: blocked, steps: [] };
  try {
    await page.goto('http://127.0.0.1:8016/demo/c');
    await page.getByText('本地服务正常', { exact: false }).waitFor();
    await page.getByLabel('调用案例').selectOption('C-CASE-102');
    await page.getByRole('button', { name: '完整复演至人工认定' }).click();
    await page.getByText('完整自动复演已停在人工认定之前', { exact: false }).waitFor();
    if (!(await page.getByRole('button', { name: '4 提交人工认定' }).isEnabled())) throw new Error('完整复演未停在可供人工确认的阶段');
    await page.locator('#evidence').getByText('LIST-AI-TOOL-01', { exact: false }).first().waitFor();
    const replayRun = JSON.parse(await page.locator('#detail').textContent());
    const allowlistHit = replayRun.analysis.hits.find(hit => hit.rule_id === 'RULE-C-TOOL-ALLOWLIST');
    if (!allowlistHit || allowlistHit.evidence.whitelist_id !== 'LIST-AI-TOOL-01' || !allowlistHit.source_evidence_ids.includes('EVC-C-WHITELIST-01')) throw new Error('规则命中未链接稳定白名单证据');
    if (replayRun.audit_ids.length !== 4 || new Set(replayRun.audit_ids).size !== 4) throw new Error('流程审计 ID 出现重复');
    await page.screenshot({ path: `${out}/browser-replay-before-review.png`, fullPage: true });
    result.steps.push({ name: '自动复演停在人工认定前；命中链接白名单原文且阶段审计ID唯一', result: 'PASS' });

    const downloadWait = page.waitForEvent('download');
    await page.getByRole('button', { name: '导出候选问题清单 JSON' }).click();
    const download = await downloadWait;
    const downloadPath = `${out}/candidate-questions.json`;
    await download.saveAs(downloadPath);
    const questions = JSON.parse(fs.readFileSync(downloadPath, 'utf8'));
    if (!questions.items.length || questions.items.some(item => !['待核实', '待补证'].includes(item.status))) throw new Error('候选问题导出内容不符合预期');
    const allowlistQuestion = questions.items.find(item => item.question_id === 'Q-RULE-C-TOOL-ALLOWLIST');
    if (!allowlistQuestion?.evidence_links.includes('EVC-C-WHITELIST-01')) throw new Error('候选问题导出未引用白名单原文');
    result.steps.push({ name: '导出候选问题 JSON 并关联白名单证据', result: 'PASS', items: questions.items.length });

    await page.getByLabel('认定结论').selectOption('违规');
    await page.getByLabel('人工理由').fill('调用 browser-shell 未列入 LIST-AI-TOOL-01，且通过 direct_api 提交商业敏感内容。');
    await page.getByRole('button', { name: '4 提交人工认定' }).click();
    await page.getByText('人工最终认定为“违规”', { exact: false }).waitFor();
    const reviewed = await page.evaluate(async () => (await (await fetch('/api/v1/c/state')).json()));
    const reviewedRun = reviewed.runs[replayRun.id];
    if (reviewedRun.audit_ids.length !== 5 || new Set(reviewedRun.audit_ids).size !== 5 || reviewedRun.audit_ids.length !== reviewed.audits.filter(entry => entry.run_id === replayRun.id).length) throw new Error('人工认定后的运行审计引用不唯一或未完整关联');
    await page.screenshot({ path: `${out}/browser-human-review.png`, fullPage: true });
    result.steps.push({ name: '人工认定并写入唯一审计索引', result: 'PASS' });

    const details = JSON.parse(await page.locator('#detail').textContent());
    const oldRun = details.id;
    await page.evaluate(async () => {
      await fetch('/api/v1/a/documents/PO-A-017/identify', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: '{}' });
      await fetch('/api/v1/runs', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ polluted: true }) });
    });
    const beforeA = await page.evaluate(async () => (await (await fetch('/api/v1/a/state')).json()));
    const beforeB = await page.evaluate(async () => (await (await fetch('/api/v1/state')).json()));
    await page.getByRole('button', { name: '重置 C 演示' }).click();
    await page.getByText('C 已独立重置', { exact: false }).waitFor();
    const stale = await page.evaluate(async id => {
      const response = await fetch(`/api/v1/c/runs/${id}/analyze`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: '{}' });
      return { status: response.status, body: await response.json() };
    }, oldRun);
    const afterA = await page.evaluate(async () => (await (await fetch('/api/v1/a/state')).json()));
    const afterB = await page.evaluate(async () => (await (await fetch('/api/v1/state')).json()));
    if (stale.status !== 404 || JSON.stringify(beforeA.runs) !== JSON.stringify(afterA.runs) || JSON.stringify(beforeA.audits) !== JSON.stringify(afterA.audits) || JSON.stringify(beforeB.runs) !== JSON.stringify(afterB.runs) || JSON.stringify(beforeB.audits) !== JSON.stringify(afterB.audits)) throw new Error('C reset failed to isolate state or invalidate run');
    await page.evaluate(async () => { await fetch('/api/v1/a/reset', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: '{}' }); await fetch('/api/v1/reset', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: '{}' }); });
    await page.screenshot({ path: `${out}/browser-reset.png`, fullPage: true });
    result.steps.push({ name: 'C reset invalidates old run and preserves A/B', result: 'PASS' });

    failNextRun = true;
    await page.getByRole('button', { name: '开始运行' }).click();
    await page.getByRole('alert').getByText('browser-failure-103', { exact: false }).waitFor();
    await page.screenshot({ path: `${out}/browser-error-feedback.png`, fullPage: true });
    result.steps.push({ name: '可见错误反馈携带 request ID', result: 'PASS' });
    if (blocked.length) throw new Error(`发现未拦截的外网请求：${blocked.join(', ')}`);
    result.external_requests_blocked = blocked;
    result.result = 'PASS';
  } catch (error) {
    result.result = 'FAIL'; result.error = error.stack || String(error);
    await page.screenshot({ path: `${out}/browser-failure.png`, fullPage: true }).catch(() => {});
    throw error;
  } finally {
    fs.writeFileSync(`${out}/browser-e2e.json`, JSON.stringify(result, null, 2));
    await context.close(); await browser.close();
  }
})().catch(error => { console.error(error); process.exitCode = 1; });
