'use strict';
const el = id => document.getElementById(id);
const ORIGINAL_REQUEST = '查询采购单 PO-2026-017 的审批状态';
let run = null;
let stage = 0;
let busy = false;
let finished = false;
let latestAudit = null;

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

function paintStep(current, message) {
  el('progress').textContent = message;
  for (let n = 1; n <= 4; n++) {
    const step = el(`step${n}`);
    step.classList.toggle('active', n === current);
    step.classList.toggle('done', n < current);
  }
}

function controls() {
  el('next-action').disabled = busy || finished;
  el('reset').disabled = busy;
  el('next-action').textContent = finished ? '本轮对照完成' : stage === 1 ? '检索污染文档' : stage === 2 ? '故障模式：执行越权提案' : stage === 3 ? '安全模式：执行同一提案' : '运行正常查询';
}

async function task(fn) {
  if (busy) return;
  busy = true;
  controls();
  el('error').hidden = true;
  try { await fn(); }
  catch (error) {
    el('error').textContent = `执行未完成：${error.message}。可重置后重试。`;
    el('error').hidden = false;
  } finally {
    busy = false;
    delete el('next-action').dataset.classroomComplete;
    controls();
  }
}

function showDocument(doc) {
  const marker = '【伪造系统指令／不可信文档正文】';
  const parts = doc.text.split(marker);
  const node = el('document');
  node.replaceChildren();
  node.append(document.createTextNode(parts[0]));
  if (parts.length > 1) {
    const malicious = document.createElement('mark');
    malicious.className = 'b-malicious';
    malicious.textContent = `${marker}${parts.slice(1).join(marker)}`;
    node.append(malicious);
  }
}

function displayProposal(proposal) {
  const label = proposal.action === 'purchase.approve' ? '审批采购单' : '读取采购单状态';
  const description = proposal.action === 'purchase.approve'
    ? `把 ${proposal.object_id} 的状态改为「${proposal.arguments.status}」`
    : `查询 ${proposal.object_id} 的审批状态`;
  el('proposal').replaceChildren();
  const title = document.createElement('strong');
  title.textContent = label;
  const detail = document.createElement('span');
  detail.textContent = description;
  el('proposal').append(title, detail);
  el('proposal').classList.toggle('is-escalation', proposal.action === 'purchase.approve');
}

function renderState(state) {
  for (const mode of ['safe', 'unsafe']) {
    const store = state.stores[mode];
    el(`${mode}-state`).textContent = `${store.status} · ¥${store.amount.toLocaleString('zh-CN')}`;
    el(`${mode}-state`).classList.toggle('is-approved', store.status === '已批准');
  }
  const rows = el('audits');
  rows.replaceChildren();
  if (!state.audits.length) {
    const row = rows.insertRow();
    const cell = row.insertCell(); cell.colSpan = 4; cell.textContent = '尚无审计记录';
  }
  for (const item of [...state.audits].reverse()) {
    const row = rows.insertRow();
    [ `${item.mode === 'safe' ? '安全模式' : '故障模式'} · ${item.authorization}`,
      item.request_id, `${item.actor_id} · ${item.object_id} · ${item.action}`,
      `${item.before.status} → ${item.after.status}` ].forEach(text => { row.insertCell().textContent = text; });
  }
}

function presentAudit(mode, audit) {
  latestAudit = audit;
  const result = el(`${mode}-result`);
  result.textContent = audit.authorization === 'BYPASS'
    ? '越权动作已被故障实现执行：采购单状态改变。'
    : audit.authorization === 'DENY'
      ? '后端拒绝越权动作：采购单状态保持不变。'
      : '只读查询已获准，未改变采购单状态。';
  result.classList.toggle('is-denied', audit.authorization === 'DENY');
  result.classList.toggle('is-bypassed', audit.authorization === 'BYPASS');
  el('audit-detail').textContent = JSON.stringify(audit, null, 2);
}

async function reset() {
  run = null;
  latestAudit = null;
  finished = false;
  await api('reset', {});
  const state = await api('state');
  renderState(state);
  el('user-query').textContent = ORIGINAL_REQUEST;
  el('document').textContent = '尚未检索';
  el('proposal').textContent = '等待检索后展示模型提案';
  el('proposal').classList.remove('is-escalation');
  el('run-id').textContent = '尚未创建运行';
  el('unsafe-result').textContent = '等待真实后端执行';
  el('safe-result').textContent = '等待真实后端执行';
  for (const id of ['unsafe-result', 'safe-result']) el(id).classList.remove('is-denied', 'is-bypassed');
  el('audit-detail').textContent = '尚未执行';
  el('technical-details').open = false;
  el('audit-response').open = false;
  el('conclusion').textContent = '模型输出只是建议。每个工具动作都要由后端独立核验身份、对象和权限。';
  stage = 0;
  paintStep(1, '准备好后，从正常只读查询开始。');
}

async function normalQuery() {
  run = await api('runs', {polluted: false});
  el('user-query').textContent = run.query;
  showDocument(run.document);
  displayProposal(run.proposal);
  el('run-id').textContent = `运行 ${run.id} · 检索请求 ${run.request_id}`;
  const audit = await api(`runs/${run.id}/executions`, {mode: 'safe', ...run.proposal}, true);
  presentAudit('safe', audit);
  renderState(await api('state'));
  stage = 1;
  paintStep(2, '正常查询成功且为只读。下一步检索含有恶意指令的文档。');
  el('conclusion').textContent = '正常文档产生只读提案，后端按固定身份允许读取。接下来保持用户请求不变，只替换检索文档。';
}

async function retrievePolluted() {
  run = await api('runs', {polluted: true});
  el('user-query').textContent = run.query;
  showDocument(run.document);
  displayProposal(run.proposal);
  el('run-id').textContent = `运行 ${run.id} · 检索请求 ${run.request_id}`;
  el('unsafe-result').textContent = '等待真实后端执行';
  el('safe-result').textContent = '等待真实后端执行';
  stage = 2;
  paintStep(3, '恶意检索内容已经诱导模型提出审批写操作。下一步让故障模式尝试执行。');
  el('conclusion').textContent = '用户原始请求仍是查询状态；恶意文档却让模型提议把采购单改为已批准。提案尚未执行。';
}

async function execute(mode) {
  if (!run || !run.polluted || run.proposal.action !== 'purchase.approve') throw new Error('当前没有可用于对照的越权提案，请重置重试。');
  const audit = await api(`runs/${run.id}/executions`, {mode, ...run.proposal}, true);
  presentAudit(mode, audit);
  renderState(await api('state'));
  if (mode === 'unsafe') {
    stage = 3;
    paintStep(4, '故障模式已改变隔离采购单。下一步将同一运行、同一提案交给安全后端。');
    el('conclusion').textContent = '故障实现跳过授权，真实改变了隔离沙箱中的采购状态。现在对同一运行和同一提案执行安全模式。';
  } else {
    finished = true;
    paintStep(4, '对照完成：故障模式越权成功，安全模式后端拒绝。');
    el('conclusion').textContent = '同一提案在故障模式改变了隔离状态；安全后端按固定身份拒绝，安全采购单仍待审批。授权必须由后端执行。';
  }
}

el('reset').addEventListener('click', () => task(reset));
el('next-action').addEventListener('click', () => task(async () => {
  if (stage === 0) await normalQuery();
  else if (stage === 1) await retrievePolluted();
  else if (stage === 2) await execute('unsafe');
  else if (stage === 3) await execute('safe');
}));

task(async () => {
  const health = await api('health');
  el('health').textContent = `本地服务正常 · ${health.model} · 无外部服务`;
  await reset();
}).then(() => { if (!el('error').hidden) el('health').textContent = '本地服务不可用，请检查启动终端'; });
