'use strict';
const el = id => document.getElementById(id);
let cases = [];
let run = null;
let busy = false;
const pause = () => new Promise(resolve => setTimeout(resolve, 320));
function progress(message, step) {
  el('progress').textContent = message;
  for (let n = 1; n <= 5; n++) el(`step${n}`).classList.toggle('active', n <= step);
}
async function api(path, body) {
  const requestId = crypto.randomUUID();
  let response;
  try {
    response = await fetch(`/api/v1/${path}`, body === undefined ? {headers: {'X-Request-ID': requestId}} : {
      method: 'POST', headers: {'Content-Type': 'application/json', 'X-Request-ID': requestId}, body: JSON.stringify(body)
    });
  } catch (error) { throw new Error(`${error.message} 请求标识：${requestId}`); }
  const data = await response.json();
  if (!response.ok) throw new Error(`${data.error?.code || `HTTP_${response.status}`}：${data.error?.message || '请求失败'} 请求标识：${data.error?.request_id || response.headers.get('X-Request-ID') || requestId}`);
  return {data, response};
}
function controls() {
  const phase = run?.phase;
  for (const id of ['reset', 'start', 'case-select', 'replay', 'decision', 'rationale']) el(id).disabled = busy;
  el('export').disabled = busy || !run?.analysis;
  el('analyze').disabled = busy || phase !== 'started';
  el('explain').disabled = busy || phase !== 'analyzed';
  el('check').disabled = busy || phase !== 'explained';
  el('review').disabled = busy || phase !== 'evidence_checked';
  document.querySelectorAll('.evidence-check').forEach(item => item.disabled = busy || phase !== 'explained');
}
async function task(fn) {
  if (busy) return;
  busy = true; controls(); el('error').hidden = true;
  try { await fn(); }
  catch (error) {
    el('error').textContent = `执行未完成：${error.message}。可检查本地服务，或重置 C 后重试。`;
    el('error').hidden = false;
  } finally { busy = false; controls(); }
}
function renderAudits(audits) {
  const body = el('audits'); body.replaceChildren();
  if (!audits.length) { const row = body.insertRow(); const cell = row.insertCell(); cell.colSpan = 4; cell.textContent = '尚无审计记录'; }
  for (const item of [...audits].reverse()) {
    const row = body.insertRow();
    [`${item.time}\n${item.request_id}`, `${item.run_id}\n${item.actor_id} / ${item.role}`,
      `${item.object_id}\n${item.action}`, `${item.result}\n${item.reason}`].forEach(value => row.insertCell().textContent = value);
  }
}
async function refresh() {
  const {data} = await api('c/state');
  renderAudits(data.audits);
  if (run?.id && data.runs[run.id]) run = data.runs[run.id];
  el('detail').textContent = run ? JSON.stringify(run, null, 2) : '尚无运行';
}
function showCase(item) {
  el('log').textContent = JSON.stringify(item.log, null, 2);
  el('policy').textContent = `${item.policy.id}\n${item.policy.text}`;
  const root = el('evidence'); root.replaceChildren();
  for (const itemEvidence of item.evidence) {
    const section = document.createElement('article'); section.className = 'evidence-item';
    const label = document.createElement('label');
    const checkbox = document.createElement('input'); checkbox.type = 'checkbox'; checkbox.className = 'evidence-check'; checkbox.value = itemEvidence.id;
    label.append(checkbox, document.createTextNode(` ${itemEvidence.title} · ${itemEvidence.id}`));
    const text = document.createElement('pre'); text.textContent = itemEvidence.text;
    section.append(label, text); root.append(section);
  }
  controls();
}
async function loadCases() {
  const {data} = await api('c/cases');
  cases = data.items;
  const select = el('case-select'); select.replaceChildren();
  for (const item of cases) { const option = document.createElement('option'); option.value = item.id; option.textContent = `${item.id} · ${item.title}`; select.append(option); }
  showCase(cases[0]);
}
async function start() {
  run = null;
  const {data} = await api('c/runs', {case_id: el('case-select').value});
  run = data; showCase(data.case);
  el('analysis').textContent = '等待规则分析。';
  el('explanation').textContent = '解释器尚未运行。';
  el('evidence-status').textContent = '请逐项打开原文并勾选，随后按“核对所选证据”。';
  el('review-result').textContent = '等待原始证据核对后进行人工认定。';
  el('conclusion').textContent = '运行已创建，尚未分析；当前没有合规结论。';
  progress(`已创建 ${run.case_id} 运行 ${run.id}；本轮审计与 A/B 状态相互独立。`, 1);
  await refresh();
}
async function analyze() {
  progress('后端依据平台日志字段执行确定性规则…', 2); await pause();
  const {data} = await api(`c/runs/${run.id}/analyze`, {});
  el('analysis').textContent = JSON.stringify(data, null, 2);
  el('conclusion').textContent = data.status === 'no_hit' ? '规则暂未发现命中；仍须查看原始证据并由人工认定。' : data.status === 'evidence_needed' ? '关键日志字段缺失，当前只能作为补证线索。' : `规则发现 ${data.hits.length} 条风险线索，不能直接等同违规结论。`;
  progress(`确定性分析已完成：${data.hits.length} 条规则命中，原始证据尚待核对。`, 2); await refresh();
}
async function explain() {
  progress('离线模拟 AI 正在整理规则事实与不确定性…', 3); await pause();
  const {data} = await api(`c/runs/${run.id}/explain`, {});
  el('explanation').textContent = JSON.stringify(data, null, 2);
  progress('离线辅助解释完成；没有写入最终认定。', 3); await refresh();
}
async function checkEvidence() {
  const evidenceIds = [...document.querySelectorAll('.evidence-check:checked')].map(item => item.value);
  progress('后端正在校验核对对象是否属于本运行的原始证据…', 4); await pause();
  const {data} = await api(`c/runs/${run.id}/evidence-check`, {evidence_ids: evidenceIds});
  el('evidence-status').textContent = `已核对 ${data.checked.length} 项原始证据；所选证据完整：${data.complete ? '是' : '否'}。认定需引用这些证据。`;
  progress('原始证据核对已记录；下一步由人工决定。', 4); await refresh();
}
async function review() {
  progress('后端正在核对人工角色、原始证据引用、理由及结论…', 5); await pause();
  const evidenceIds = run.evidence_check.checked_ids;
  const {data} = await api(`c/runs/${run.id}/review`, {decision: el('decision').value, rationale: el('rationale').value, evidence_ids: evidenceIds});
  el('review-result').textContent = `${data.reviewer.name}（${data.reviewer.id} / ${data.reviewer.role}）认定：${data.decision}。理由：${data.rationale}。引用证据：${data.evidence_ids.join('、')}。`;
  el('conclusion').textContent = `人工最终认定为“${data.decision}”。规则筛查及离线解释均不替代本次人工判断。`;
  progress(`人工认定已记录：${data.decision}；结论与证据、理由、固定身份关联。`, 5); await refresh();
}
async function exportQuestions() {
  const {data} = await api(`c/runs/${run.id}/candidate-questions`);
  const blob = new Blob([JSON.stringify(data, null, 2)], {type: 'application/json;charset=utf-8'});
  const url = URL.createObjectURL(blob); const link = document.createElement('a');
  link.href = url; link.download = `demo-c-${run.id}-candidate-questions.json`; link.click();
  URL.revokeObjectURL(url);
  el('progress').textContent = `候选问题清单已导出：${data.items.length} 项，均标记为待核实；运行 ${data.run_id}。`;
}
async function reset() {
  const {data} = await api('c/reset', {});
  run = null; renderAudits(data.audits);
  el('analysis').textContent = '尚未分析。'; el('explanation').textContent = '尚未生成。解释器不能写入人工认定。';
  el('evidence-status').textContent = '尚未核对原始证据。'; el('review-result').textContent = '尚未认定。';
  el('rationale').value = ''; el('conclusion').textContent = '规则只能筛查线索；证据和制度原文须由人核对，最终认定始终由人工作出。';
  progress('C 已独立重置：运行与审计清空，旧运行标识失效。', 0); await refresh();
}
el('case-select').onchange = () => { showCase(cases.find(item => item.id === el('case-select').value)); };
el('reset').onclick = () => task(reset);
el('start').onclick = () => task(start);
el('analyze').onclick = () => task(analyze);
el('explain').onclick = () => task(explain);
el('check').onclick = () => task(checkEvidence);
el('review').onclick = () => task(review);
el('export').onclick = () => task(exportQuestions);
el('replay').onclick = () => task(async () => {
  await reset(); await start(); await pause(); await analyze(); await pause(); await explain(); await pause();
  document.querySelectorAll('.evidence-check').forEach(item => { item.checked = true; });
  await checkEvidence();
  progress('完整自动复演已停在人工认定之前；请人工选择结论、填写理由并按下认定按钮。', 4);
});
task(async () => {
  const {data} = await api('health');
  el('health').textContent = `本地服务正常 · ${data.model} · 无外部服务`;
  await loadCases(); await refresh();
}).catch(() => { el('health').textContent = '本地服务不可用，请检查启动终端'; });
