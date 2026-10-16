const fs = require('node:fs');
const path = require('node:path');
const { chromium } = require('/Users/yanbo/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');

(async () => {
  const out = path.resolve(__dirname, '../evidence/integration-worker');
  fs.mkdirSync(out, { recursive: true });
  const browser = await chromium.launch({ channel: 'chrome', headless: true });
  const context = await browser.newContext({ viewport: { width: 1440, height: 1100 }, acceptDownloads: true });
  const blocked = [];
  const pageErrors = [];
  let failNextA = false;
  const result = { browser: 'Chrome', viewport: { width: 1440, height: 1100 }, steps: [], external_requests_blocked: blocked, injected_failure: null };
  const page = await context.newPage();
  page.on('pageerror', error => pageErrors.push(error.message));
  await context.route('**/*', async route => {
    const url = new URL(route.request().url());
    if (url.origin !== 'http://127.0.0.1:8016') { blocked.push(url.href); await route.abort(); return; }
    if (failNextA && route.request().method() === 'POST' && url.pathname === '/api/v1/a/documents/PO-A-017/identify') {
      failNextA = false;
      result.injected_failure = { path: url.pathname, status: 503, request_id: 'integration-fault-503' };
      await route.fulfill({ status: 503, contentType: 'application/json', headers: { 'X-Request-ID': 'integration-fault-503' }, body: JSON.stringify({ error: { code: 'SERVICE_UNAVAILABLE', message: '本轮浏览器故障恢复演练：注入的一次性本地请求失败', request_id: 'integration-fault-503' } }) });
      return;
    }
    await route.continue();
  });

  const state = async key => page.evaluate(async name => {
    const url = name === 'b' ? '/api/v1/state' : `/api/v1/${name}/state`;
    const response = await fetch(url); return response.json();
  }, key);
  const resetFlow = async ({ name, button, stateKey, stalePath, staleBody = {} }, before) => {
    await page.getByRole('button', { name: button, exact: true }).click();
    const current = await state(stateKey);
    if (Object.keys(current.runs).length || current.audits.length) throw new Error(`${name} 重置未清空本课状态`);
    const stale = await page.evaluate(async ({ path, body }) => {
      const response = await fetch(path, { method: 'POST', headers: { 'content-type': 'application/json' }, body: JSON.stringify(body) });
      return { status: response.status, body: await response.json() };
    }, { path: stalePath, body: staleBody });
    if (stale.status !== 404) throw new Error(`${name} 重置后旧 run 未失效：${stale.status}`);
    const after = {};
    for (const key of ['a', 'b', 'c', 'd']) after[key] = await state(key);
    for (const key of ['a', 'b', 'c', 'd']) if (key !== stateKey && JSON.stringify(before[key]) !== JSON.stringify(after[key])) throw new Error(`${name} 重置改变了 ${key.toUpperCase()} 状态`);
    result.steps.push({ name: `${name} 独立重置清空本课状态、使旧 run 返回 404、其他 Demo 状态保持不变`, result: 'PASS' });
    return after;
  };

  try {
    await page.goto('http://127.0.0.1:8016/demo/a');
    await page.getByText('本地服务正常', { exact: false }).waitFor();
    const expected = ['/demo/a', '/demo/b', '/demo/c', '/demo/d'];
    for (const url of expected) {
      if (await page.locator('.demo-nav a').count() !== 4) throw new Error(`${url} 导航入口不是唯一四项`);
      const hrefs = await page.locator('.demo-nav a').evaluateAll(nodes => nodes.map(node => new URL(node.href).pathname));
      if (JSON.stringify(hrefs) !== JSON.stringify(expected)) throw new Error(`${url} 导航地址错误：${hrefs}`);
    }
    result.steps.push({ name: 'A/B/C/D 页面导航各有唯一入口且同一 8016 服务可访问', result: 'PASS' });

    failNextA = true;
    await page.getByRole('button', { name: '1 规则检查' }).click();
    await page.getByRole('alert').getByText('本轮浏览器故障恢复演练', { exact: false }).waitFor();
    await page.screenshot({ path: path.join(out, 'A-service-error.png'), fullPage: true });
    result.steps.push({ name: '浏览器拦截器注入一次 HTTP 503，页面显示错误与 request ID', result: 'PASS', request_id: 'integration-fault-503' });
    await page.getByRole('button', { name: '重置 A 演示' }).click();
    await page.getByText('A 已独立重置', { exact: false }).waitFor();
    await page.locator('#document-select').selectOption('PO-A-017');
    await page.getByRole('button', { name: '1 规则检查' }).click();
    await page.getByText('确定性规则识别完成', { exact: false }).waitFor();
    await page.getByRole('button', { name: '2 离线辅助识别' }).click();
    await page.waitForFunction(() => document.querySelector('#assistant-finding').textContent.includes('AI-FP-AMOUNT-01'));
    const assistantFindingText = await page.locator('#assistant-finding').textContent();
    if (!assistantFindingText.includes('128000 元')) {
      await page.screenshot({ path: path.join(out, 'A-assistant-missing-evidence.png'), fullPage: true });
      throw new Error(`A 未显示固定误报证据；#assistant-finding=${assistantFindingText}`);
    }
    await page.screenshot({ path: path.join(out, 'A-false-positive.png'), fullPage: true });
    await page.getByRole('button', { name: '3 人工修正误报' }).click();
    await page.getByText('人工修正已记录', { exact: false }).waitFor();
    await page.getByRole('button', { name: '4 脱敏预览' }).click();
    await page.getByText('脱敏预览已生成', { exact: false }).waitFor();
    if (!(await page.locator('#process').isEnabled())) throw new Error('完成预览后人工确认未启用');
    await page.screenshot({ path: path.join(out, 'A-redaction-preview.png'), fullPage: true });
    await page.getByRole('button', { name: '5 人工确认进入下一步' }).click();
    await page.getByText('授权通过并完成前后比较与审计', { exact: false }).waitFor();
    const aRun = await page.evaluate(async () => { const s = await (await fetch('/api/v1/a/state')).json(); return Object.values(s.runs)[0]; });
    if (!aRun.review || !aRun.preview || !aRun.redacted_text || aRun.review.corrected_category !== 'ordinary') throw new Error('A 后端运行未保存修正/预览/确认阶段');
    await page.screenshot({ path: path.join(out, 'A-human-confirmed.png'), fullPage: true });
    result.steps.push({ name: 'A Chrome 完成规则、明确离线误报、人工证据修正、预览和显式确认', result: 'PASS' });

    await page.setViewportSize({ width: 390, height: 844 });
    const mobile = await page.evaluate(() => ({ width: innerWidth, scrollWidth: document.documentElement.scrollWidth }));
    if (mobile.scrollWidth > mobile.width) throw new Error(`A 手机视图横向溢出：${JSON.stringify(mobile)}`);
    await page.screenshot({ path: path.join(out, 'A-mobile.png'), fullPage: true });
    await page.setViewportSize({ width: 1440, height: 1100 });
    const aPersisted = await state('a');
    await page.reload(); await page.getByText('本地服务正常', { exact: false }).waitFor();
    if (JSON.stringify(aPersisted.runs) !== JSON.stringify((await state('a')).runs)) throw new Error('A 刷新后后端状态变化');
    result.steps.push({ name: 'A 手机视口无横向溢出；刷新页面不改变后端 run', result: 'PASS', viewport: mobile });

    await page.goto('http://127.0.0.1:8016/demo/b');
    await page.getByText('本地服务正常', { exact: false }).waitFor();
    await page.getByRole('button', { name: '一键完整复演' }).click();
    await page.getByText('对比完成：相同运行', { exact: false }).waitFor();
    let bState = await state('b');
    if (bState.stores.unsafe.status !== '已批准' || bState.stores.safe.status !== '待审批') throw new Error('B 故障状态或安全拒绝状态不符');
    await page.getByRole('button', { name: '安全模式：执行相同提案' }).click();
    await page.getByText('对比完成：相同运行', { exact: false }).waitFor();
    bState = await state('b');
    if (bState.stores.safe.status !== '待审批' || !bState.audits.some(item => item.authorization === 'DENY')) throw new Error('B 安全拒绝未保持状态并审计');
    await page.screenshot({ path: path.join(out, 'B-complete-chain.png'), fullPage: true });
    result.steps.push({ name: 'B Chrome 正常读取、污染写提案、故障写入、安全拒绝同一提案并留审计', result: 'PASS' });
    const bPersisted = await state('b');
    await page.reload(); await page.getByText('本地服务正常', { exact: false }).waitFor();
    if (JSON.stringify(bPersisted) !== JSON.stringify(await state('b'))) throw new Error('B 刷新页面时业务状态发生变化');

    await page.goto('http://127.0.0.1:8016/demo/c');
    await page.getByText('本地服务正常', { exact: false }).waitFor();
    await page.getByLabel('调用案例').selectOption('C-CASE-102');
    await page.getByRole('button', { name: '完整复演至人工认定' }).click();
    await page.getByText('完整自动复演已停在人工认定之前', { exact: false }).waitFor();
    const cRun = await page.evaluate(async () => { const s = await (await fetch('/api/v1/c/state')).json(); return Object.values(s.runs)[0]; });
    if (cRun.phase !== 'evidence_checked' || cRun.review !== null || cRun.explanation.final_decision !== null) throw new Error('C 自动复演没有停在人工作出认定之前');
    await page.locator('#decision').selectOption('违规');
    await page.locator('#rationale').fill('演示调用和准入白名单不符；已对照原始日志、审批及制度证据。');
    await page.getByRole('button', { name: '4 提交人工认定' }).click();
    await page.getByText('人工最终认定为“违规”', { exact: false }).waitFor();
    const cDownloadWait = page.waitForEvent('download');
    await page.getByRole('button', { name: '导出候选问题清单 JSON' }).click();
    const cDownload = await cDownloadWait;
    await cDownload.saveAs(path.join(out, 'C-candidate-questions.json'));
    const cQuestions = JSON.parse(fs.readFileSync(path.join(out, 'C-candidate-questions.json'), 'utf8'));
    if (!cQuestions.items.length) throw new Error('C 候选问题下载为空');
    await page.screenshot({ path: path.join(out, 'C-human-review.png'), fullPage: true });
    result.steps.push({ name: 'C Chrome 规则、辅助解释、原始证据、人工认定及候选 JSON 下载', result: 'PASS', questions: cQuestions.items.length });
    const cPersisted = await state('c');
    await page.reload(); await page.getByText('本地服务正常', { exact: false }).waitFor();
    if (JSON.stringify(cPersisted) !== JSON.stringify(await state('c'))) throw new Error('C 刷新页面时业务状态发生变化');

    await page.goto('http://127.0.0.1:8016/demo/d');
    await page.getByText('本地服务正常', { exact: false }).waitFor();
    await page.getByRole('button', { name: '一键复演至人工核查前' }).click();
    await page.getByText('辅助分析完成', { exact: false }).waitFor();
    const dRun = await page.evaluate(async () => { const s = await (await fetch('/api/v1/d/state')).json(); return Object.values(s.runs)[0]; });
    if (dRun.phase !== 'explained' || dRun.review !== null || dRun.brief !== null) throw new Error('D 自动复演越过人工核查阶段');
    await page.locator('#rationale').fill('样本没有凭据来源、API 响应字节数或网络出口证据，不能证明账号失陷或数据外传。');
    await page.getByRole('button', { name: '3 提交人工核查' }).click();
    await page.getByText('人工核查已记录', { exact: false }).waitFor();
    await page.getByRole('button', { name: '4 生成四栏简报' }).click();
    await page.getByText('四栏简报已生成', { exact: false }).waitFor();
    if (await page.locator('.brief-column').count() !== 4) throw new Error('D 页面没有四栏简报');
    await page.screenshot({ path: path.join(out, 'D-four-column-brief.png'), fullPage: true });
    const dDownloadWait = page.waitForEvent('download');
    await page.getByRole('button', { name: '导出四栏简报 JSON' }).click();
    const dDownload = await dDownloadWait;
    await dDownload.saveAs(path.join(out, 'D-four-column-brief.json'));
    const dBrief = JSON.parse(fs.readFileSync(path.join(out, 'D-four-column-brief.json'), 'utf8'));
    if (!['已证实事实', 'AI 推测', '待核查', '建议动作'].every(key => dBrief[key]?.length)) throw new Error('D 下载 JSON 四栏不完整');
    result.steps.push({ name: 'D Chrome 日志、规则、AI 推测、人工核查、四栏简报及 JSON 下载', result: 'PASS' });
    const dPersisted = await state('d');
    await page.reload(); await page.getByText('本地服务正常', { exact: false }).waitFor();
    if (JSON.stringify(dPersisted) !== JSON.stringify(await state('d'))) throw new Error('D 刷新页面时业务状态发生变化');

    let before = {};
    for (const key of ['a', 'b', 'c', 'd']) before[key] = await state(key);
    await page.goto('http://127.0.0.1:8016/demo/a');
    before = await resetFlow({ name: 'A', button: '重置 A 演示', stateKey: 'a', stalePath: `/api/v1/a/documents/PO-A-017/process/${aRun.id}`, staleBody: { confirmation: 'CONFIRM_NEXT_STEP' } }, before);
    await page.goto('http://127.0.0.1:8016/demo/b');
    before = await resetFlow({ name: 'B', button: '重置全部状态', stateKey: 'b', stalePath: `/api/v1/runs/${Object.keys(before.b.runs)[0]}/executions`, staleBody: { mode: 'safe', action: 'purchase.read', object_id: 'PO-2026-017', arguments: {} } }, before);
    await page.goto('http://127.0.0.1:8016/demo/c');
    before = await resetFlow({ name: 'C', button: '重置 C 演示', stateKey: 'c', stalePath: `/api/v1/c/runs/${cRun.id}/analyze` }, before);
    await page.goto('http://127.0.0.1:8016/demo/d');
    before = await resetFlow({ name: 'D', button: '重置 D 演示', stateKey: 'd', stalePath: `/api/v1/d/runs/${dRun.id}/analyze` }, before);
    for (const key of ['a', 'b', 'c', 'd']) {
      if (Object.keys(before[key].runs).length || before[key].audits.length) throw new Error(`最终 ${key.toUpperCase()} 未处于初态`);
    }
    const bInitial = await state('b');
    if (bInitial.stores.unsafe.status !== '待审批' || bInitial.stores.safe.status !== '待审批') throw new Error('B 最终采购单状态不是初态');
    await page.screenshot({ path: path.join(out, 'D-final-reset.png'), fullPage: true });
    result.steps.push({ name: '四 Demo 课堂顺序结束后分别独立重置，最终全部回到初态', result: 'PASS' });

    if (blocked.length) throw new Error(`发现外网请求：${blocked.join(', ')}`);
    if (pageErrors.length) throw new Error(`浏览器异常：${pageErrors.join(' | ')}`);
    result.external_request_count = blocked.length;
    result.page_error_count = pageErrors.length;
    result.result = 'PASS';
    fs.writeFileSync(path.join(out, 'browser-integrated.json'), JSON.stringify(result, null, 2) + '\n');
    console.log(JSON.stringify({ result: result.result, steps: result.steps.length, external_requests: blocked.length, page_errors: pageErrors.length, evidence: out }, null, 2));
  } catch (error) {
    result.result = 'FAIL'; result.error = error.stack || error.message; result.external_request_count = blocked.length; result.page_errors = pageErrors;
    fs.writeFileSync(path.join(out, 'browser-integrated.json'), JSON.stringify(result, null, 2) + '\n');
    console.error(JSON.stringify({ result: result.result, completed_steps: result.steps, error: result.error, evidence: out }, null, 2));
    process.exitCode = 1;
  } finally {
    await browser.close();
  }
})();
