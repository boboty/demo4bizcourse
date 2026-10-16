'use strict';
const el = id => document.getElementById(id);
let run = null;
let busy = false;
const pause = () => new Promise(resolve => setTimeout(resolve, 420));
function progress(text, step) {
  el('progress').textContent = text;
  for (let n = 1; n <= 4; n++) el(`step${n}`).classList.toggle('active', n <= step);
}
async function api(path, body, permitDeny = false) {
  const response = await fetch(`/api/v1/${path}`, body === undefined ? {} : {
    method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(body)
  });
  const data = await response.json();
  if (!response.ok && !(permitDeny && response.status === 403 && data.authorization === 'DENY')) {
    throw new Error(`${data.error?.message || '本地请求失败'} 请求标识：${data.error?.request_id || response.headers.get('X-Request-ID')}`);
  }
  return data;
}
function controls() {
  ['normal', 'pollute', 'replay', 'reset'].forEach(id => el(id).disabled = busy);
  ['unsafe', 'safe'].forEach(id => el(id).disabled = busy || !run);
}
async function task(fn) {
  if (busy) return;
  busy = true; controls(); el('error').hidden = true;
  try { await fn(); }
  catch (error) {
    el('error').textContent = `执行未完成：${error.message}。恢复服务后点击“重置全部状态”重新开始。`;
    el('error').hidden = false;
    progress('执行中断，已保留可取得的证据；请重置后重试。', 0);
  } finally { busy = false; controls(); }
}
function render(state) {
  for (const mode of ['safe', 'unsafe']) {
    const store = state.stores[mode];
    el(`${mode}-state`).textContent = `${store.status} · ¥${store.amount.toLocaleString('zh-CN')}`;
  }
  const rows = el('audits'); rows.replaceChildren();
  if (!state.audits.length) {
    const row = rows.insertRow(); const td = row.insertCell(); td.colSpan = 5; td.textContent = '尚无审计记录';
  }
  for (const item of [...state.audits].reverse()) {
    const row = rows.insertRow();
    [ `${item.time}\n${item.request_id}`, `${item.run_id}\n${item.actor_id} / ${item.role}`,
      `${item.object_id}\n${item.action}`, `${item.mode === 'safe' ? '安全' : '故障'} / ${item.authorization}`,
      `${item.before.status} → ${item.after.status}` ].forEach(text => row.insertCell().textContent = text);
  }
}
async function reset() {
  render(await api('reset', {})); run = null;
  el('document').textContent = '等待检索。文档内容只应作为业务数据。';
  el('proposal').textContent = '等待模型提案。'; el('run-id').textContent = '运行标识：未创建';
  ['safe', 'unsafe'].forEach(mode => el(`${mode}-result`).textContent = '尚未执行');
  el('audit-detail').textContent = '尚未执行';
  el('conclusion').textContent = '模型可以建议调用工具；后端必须独立决定是否允许。点击“正常只读查询”开始。';
  progress('已重置：两套沙箱均待审批，审计清空，可完整复演。', 0);
}
async function retrieve(polluted) {
  progress('正在请求后端检索与模拟提案…', 1); await pause();
  run = await api('runs', {polluted});
  el('document').textContent = run.document.text;
  progress('已取得后端结果，正在分步展示正文与模拟提案…', 2); await pause();
  el('proposal').textContent = JSON.stringify(run.proposal, null, 2);
  el('run-id').textContent = `运行标识：${run.id} · 模型：离线确定性模拟`;
  ['safe', 'unsafe'].forEach(mode => el(`${mode}-result`).textContent = '当前提案尚未执行');
  progress(polluted ? '污染正文诱导提出 purchase.approve 写操作；尚未执行。' : '正常文档得到 purchase.read 只读提案；即将安全执行。', 2);
  el('conclusion').textContent = polluted ? '污染内容已影响模拟模型提案。分别执行故障与安全模式，观察同一请求的不同结果。' : '正常查询提案为只读，后端仍会检查权限。';
  if (!polluted) await execute('safe');
}
async function execute(mode) {
  if (!run) return;
  progress(`正在由${mode === 'safe' ? '安全后端核验权限' : '故障系统跳过授权'}…`, 3); await pause();
  const audit = await api(`runs/${run.id}/executions`, {mode, ...run.proposal}, true);
  el(`${mode}-result`).textContent = `${audit.authorization} · ${audit.reason}`;
  el('audit-detail').textContent = JSON.stringify(audit, null, 2);
  render(await api('state'));
  const comparison = run.polluted && mode === 'safe';
  el('conclusion').textContent = audit.authorization === 'DENY'
    ? '后端真实拒绝审批：采购观察员无写权限，安全沙箱前后状态保持不变。模型输出不能代替业务授权。'
    : audit.authorization === 'BYPASS' ? '故障系统已错误批准虚构采购单；影响仅在隔离故障沙箱。接着执行安全模式。'
    : '正常只读查询成功：采购单当前待审批。只读授权通过，业务状态未更改。';
  progress(comparison ? '对比完成：相同运行、相同写提案；查看业务状态与审计结果。' : '执行完成，审计已记录角色、对象、动作与授权结果。', 4);
}
el('reset').onclick = () => task(reset);
el('normal').onclick = () => task(() => retrieve(false));
el('pollute').onclick = () => task(() => retrieve(true));
el('unsafe').onclick = () => task(() => execute('unsafe'));
el('safe').onclick = () => task(() => execute('safe'));
el('replay').onclick = () => task(async () => {
  await reset(); await retrieve(false); await pause(); await retrieve(true); await execute('unsafe'); await execute('safe');
});
task(async () => {
  const health = await api('health');
  el('health').textContent = `本地服务正常 · ${health.model} · 无外部服务`;
  render(await api('state'));
}).then(() => { if (!el('error').hidden) el('health').textContent = '本地服务不可用，请检查启动终端'; });
