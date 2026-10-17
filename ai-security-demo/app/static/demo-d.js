'use strict';
const $ = (id) => document.getElementById(id);
const esc = (value) => String(value).replace(/[&<>"']/g, (char) => ({'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'}[char]));
let currentRun = null;
let logs = [];
let analysis = null;
let explanation = null;
let busy = false;
let lastRequestId = '';

async function api(path, options = {}) {
  const requestId = crypto.randomUUID();
  let response;
  try {
    response = await fetch(path, {headers: {'content-type': 'application/json', 'X-Request-ID': requestId}, ...options});
  } catch (error) { throw new Error(`${error.message} · 请求标识 ${requestId}`); }
  const body = await response.json();
  lastRequestId = response.headers.get('X-Request-ID') || requestId;
  if (!response.ok) throw new Error(`${body.error?.message || `本地服务返回 HTTP ${response.status}`} · 请求标识 ${body.error?.request_id || lastRequestId}`);
  return body;
}

function post(path, data = {}) { return api(path, {method: 'POST', body: JSON.stringify(data)}); }
function phase() { return currentRun?.phase || 'initial'; }

function setError(message = '') {
  $('error').textContent = message;
  $('error').hidden = !message;
}

function progress(message, next) {
  $('progress').textContent = message;
  $('next-step').textContent = next ? `下一步：${next}` : '流程已完成，可重置后再次演示';
}

function setMainAction(id) {
  for (const name of ['start', 'analyze', 'explain', 'review', 'brief-button']) {
    const button = $(name);
    button.hidden = name !== id;
    button.disabled = busy || name !== id;
  }
}

function renderSignals() {
  const groups = [
    {title: '身份认证', type: '认证事件', ids: logs.filter((row) => row.event === 'login_success').map((row) => row.id)},
    {title: '接口访问', type: 'API 读取', ids: logs.filter((row) => row.event === 'api_read').map((row) => row.id)},
    {title: '权限审计', type: '访问被拒', ids: logs.filter((row) => row.event === 'permission_denied').map((row) => row.id)}
  ];
  $('signal-list').innerHTML = groups.map((group) => `<div class="d-signal"><strong>${group.title}</strong><div>${group.type} · ${group.ids.length} 条<div class="d-signal-ids">${group.ids.map(esc).join(' · ')}</div></div></div>`).join('');
  $('log-count').textContent = `${logs.length} 条合成记录`;
  $('time-basis').textContent = currentRun?.analysis?.time_basis || $('time-basis').textContent;
  $('logs').innerHTML = logs.map((row) => `<tr id="${esc(row.id)}"><td>${esc(row.id)}</td><td>${esc(row.time)}</td><td>${esc(row.account)}</td><td>${esc(row.source_ip)}</td><td>${esc(row.event)}<br>${esc(row.detail)}</td></tr>`).join('');
}

function logReference(id) { return `<button type="button" class="d-log-ref" data-log-id="${esc(id)}">${esc(id)}</button>`; }

function bindLogReferences(root = document) {
  root.querySelectorAll('[data-log-id]').forEach((button) => button.addEventListener('click', () => {
    const details = button.closest('.d-evidence')?.querySelector('.d-technical');
    if (details) details.open = true;
    const target = $(button.dataset.logId);
    target?.scrollIntoView({behavior: 'smooth', block: 'center'});
    target?.classList.add('d-row-highlight');
    window.setTimeout(() => target?.classList.remove('d-row-highlight'), 1200);
  }));
}

function renderAnalysis() {
  if (!analysis) return;
  const findings = analysis.findings || [];
  $('finding-count').textContent = String(findings.length);
  $('normal-count').textContent = String(analysis.normal_log_ids?.length || 0);
  $('findings').innerHTML = findings.map((item) => `<article class="d-finding"><h3>${esc(item.account)} · ${esc(item.severity)}</h3><p>${esc(item.title)}</p><p>${esc(item.evidence_text)}</p><small>来源日志：${item.log_ids.map(logReference).join('、')}</small></article>`).join('') || '<p class="d-lead">本次样本未命中规则。未命中不代表不存在风险。</p>';
  const select = $('finding');
  const previous = select.value;
  const inference = explanation ? `<option value="${esc(explanation.inference_id)}">AI 推测 · 凭据可能泄露并外传数据</option>` : '';
  select.innerHTML = inference + findings.map((item) => `<option value="${esc(item.id)}">${esc(item.title)} · ${esc(item.account)}</option>`).join('');
  if (previous && [...select.options].some((item) => item.value === previous)) select.value = previous;
  else if (explanation) select.value = explanation.inference_id;
  renderEvidenceOptions();
  bindLogReferences($('findings'));
}

function selectedFinding() {
  const value = $('finding').value;
  if (explanation && value === explanation.inference_id) return {log_ids: explanation.inference_evidence_ids || []};
  return analysis?.findings?.find((item) => item.id === value);
}

function renderEvidenceOptions() {
  const target = selectedFinding();
  const root = $('evidence-select');
  if (!target?.log_ids?.length) { root.textContent = '没有可引用的相关原始日志。'; controls(); return; }
  root.innerHTML = `<div class="d-log-choice">${target.log_ids.map((id, index) => `<label><input type="checkbox" name="evidence" value="${esc(id)}" ${index === 0 ? 'checked' : ''}> ${logReference(id)}</label>`).join('')}</div>`;
  bindLogReferences(root);
  root.querySelectorAll('input').forEach((input) => input.addEventListener('change', controls));
  controls();
}

function renderExplanation() {
  if (!explanation) return;
  $('risk-explanation').textContent = explanation.risk_explanation;
  $('inference').textContent = explanation.inference.replace('看似合理但尚未被证实：', '').replace('可能凭据泄露，并已通过 API 外传数据', '可能存在凭据泄露和经 API 外传数据的风险');
  $('uncertainty').textContent = explanation.uncertainty;
  $('inference-evidence').innerHTML = (explanation.inference_evidence_ids || []).map(logReference).join('、') || '没有直接关联日志';
  bindLogReferences($('left-ai'));
}

function renderBrief(brief) {
  const reviewFact = (brief['已证实事实'] || []).find((row) => row.text.startsWith('人工核查记录：'));
  const facts = (brief['已证实事实'] || []).filter((row) => !row.text.startsWith('人工核查记录：'));
  if (!facts.length && currentRun?.review) {
    for (const id of currentRun.review.evidence_ids) {
      const log = currentRun.logs.find((item) => item.id === id);
      if (log) facts.push({text: `${log.time} · ${log.account} · ${log.detail}`, evidence_ids: [id]});
    }
  }
  const inference = (brief['AI 推测'] || []).map((row) => ({
    ...row,
    summary: row.text.replace(/^看似合理但尚未被证实：/, '').replace('可能凭据泄露，并已通过 API 外传数据', '可能存在凭据泄露和经 API 外传数据的风险')
  }));
  const pending = (brief['待核查'] || []).map((row) => ({...row, summary: '缺少凭据来源、响应字节数与网络出口记录。'}));
  const suggestions = (brief['建议动作'] || []).map((row) => ({...row, summary: '按组织流程核对认证、API 响应与网络出口日志。'}));
  $('brief-review-note').textContent = reviewFact ? `人工核查：${currentRun.review.decision} · ${currentRun.review.rationale}` : '';
  const columns = [['已证实事实', facts], ['AI 推测', inference], ['待核查事项', pending], ['建议动作', suggestions]];
  $('brief').innerHTML = columns.map(([heading, rows]) => `<article class="d-brief-column"><h4>${heading}</h4>${(rows || []).map((row) => {
    const detail = row.text === row.summary ? '' : `<details><summary>查看完整说明</summary><p class="d-brief-detail">${esc(row.text)}</p></details>`;
    return `<div class="d-brief-item"><p>${esc(row.summary || row.text)}${row.status ? `<strong class="d-brief-status">${esc(row.status)}</strong>` : ''}</p><small>来源：${(row.evidence_ids || []).map((id) => id.startsWith('LOG-') ? logReference(id) : `<span>${esc(id === currentRun?.review?.id ? '人工核查记录' : id)}</span>`).join('、') || '无'}</small>${detail}</div>`;
  }).join('') || '<p>暂无。</p>'}</article>`).join('');
  $('brief-meta').textContent = `简报 ${brief.id} · 运行 ${brief.run_id} · 由后端生成；建议不执行任何系统操作。`;
  $('download-brief').disabled = false;
  bindLogReferences($('brief'));
}

function renderState(data) {
  const root = $('audit');
  if (!data.audits.length) { root.innerHTML = '<li>尚无审计记录。</li>'; return; }
  root.innerHTML = [...data.audits].reverse().map((item) => `<li><time>${esc(item.time)}</time> · ${esc(item.action)} / ${esc(item.result)} · 对象 ${esc(item.object_id)} · ${esc(item.actor_id)}（${esc(item.role)}）· 请求 ${esc(item.request_id)} · ${esc(item.reason)}</li>`).join('');
}

function setStage() {
  const current = phase();
  const panels = {initial: 'panel-start', started: 'panel-start', analyzed: 'panel-analyzed', explained: '', reviewed: 'panel-reviewed', briefed: 'panel-brief'};
  for (const panel of document.querySelectorAll('.d-panel')) panel.hidden = panel.id !== panels[current];
  $('review-form').hidden = current !== 'explained';
  const showAssistant = ['explained', 'reviewed', 'briefed'].includes(current);
  $('signal-list').hidden = showAssistant;
  $('left-ai').hidden = !showAssistant;
  $('log-intro').hidden = showAssistant;
  $('evidence-title').textContent = showAssistant ? 'AI 辅助研判' : '分散的日志记录';
  $('evidence-kicker').textContent = showAssistant ? '待核实推测' : '线索来源';
  const copy = {
    initial: ['课堂步骤 01', '先把线索放到一起', '待开始'],
    started: ['课堂步骤 02', '聚合异常事件', '日志已汇总'],
    analyzed: ['课堂步骤 03', '查看聚合出的候选事件', '等待辅助研判'],
    explained: ['课堂步骤 04', '判断推测是否有据', '人工核查中'],
    reviewed: ['课堂步骤 05', '把核查结论整理成简报', '人工核查已记录'],
    briefed: ['流程完成', '四栏事件简报', '结果已生成']
  };
  const [kicker, title, mark] = copy[current];
  $('focus-kicker').textContent = kicker;
  $('focus-title').textContent = title;
  $('focus-mark').textContent = mark;
  const activeStep = {initial: 0, started: 1, analyzed: 2, explained: 3, reviewed: 4, briefed: 4}[current];
  document.querySelectorAll('.steps span').forEach((step, index) => {
    step.classList.toggle('active', index === activeStep);
    step.classList.toggle('done', current === 'briefed' || index < activeStep);
    step.dataset.status = index === activeStep ? 'current' : (current === 'briefed' || index < activeStep) ? 'done' : 'upcoming';
    if (index === activeStep) step.setAttribute('aria-current', 'step'); else step.removeAttribute('aria-current');
  });
  const primary = {initial: 'start', started: 'analyze', analyzed: 'explain', explained: 'review', reviewed: 'brief-button'}[current];
  setMainAction(primary);
  $('replay').disabled = busy;
  $('reset').disabled = busy;
  if (currentRun) {
    $('log-intro').textContent = current === 'initial' ? '来自认证、API 网关与授权审计的片段，先看它们各自记录了什么。' : `本次运行 ${currentRun.id} 已将 ${logs.length} 条合成记录放入同一工作区。`;
    if (currentRun.review) $('review-result').textContent = `${currentRun.review.reviewer.name}：${currentRun.review.decision}。${currentRun.review.rationale}（关联 ${currentRun.review.evidence_ids.join('、')}）`;
    if (current === 'initial' || current === 'started') $('conclusion').textContent = current === 'started' ? '日志已汇总，尚未形成异常判断。下一步按账号和时间聚合事件。' : '尚无分析结论。建议与推测均不会自动执行或确认为事实。';
    else if (current === 'analyzed') $('conclusion').textContent = `${analysis?.findings.length || 0} 条规则线索已聚合；它们描述异常模式，不说明原因或后果。`;
    else if (current === 'explained') $('conclusion').textContent = 'AI 提出的凭据泄露与数据外传仍是推测。请核对相关日志并写出人工理由。';
    else if (current === 'reviewed') $('conclusion').textContent = `人工核查结论“${currentRun.review?.decision}”已关联本次原始日志；还不能据此认定账号失陷或数据外传。`;
    else $('conclusion').textContent = '简报已按事实、推测、待核查和建议分栏；建议内容不会触发封禁、隔离或生产操作。';
  } else $('conclusion').textContent = '尚无分析结论。建议与推测均不会自动执行或确认为事实。';
}

function controls() {
  const current = phase();
  if (current === 'explained') {
    const hasEvidence = document.querySelectorAll('input[name="evidence"]:checked').length > 0;
    $('review').disabled = busy || !hasEvidence || !$('rationale').value.trim();
  }
  if (currentRun?.phase === 'briefed') $('download-brief').disabled = busy;
  setStage();
}

async function refresh() {
  const data = await api('/api/v1/d/state');
  renderState(data);
  if (currentRun?.id && data.runs[currentRun.id]) currentRun = data.runs[currentRun.id];
  if (currentRun) {
    analysis = currentRun.analysis;
    explanation = currentRun.explanation;
    $('detail').textContent = JSON.stringify(currentRun, null, 2);
    renderSignals();
    if (analysis) renderAnalysis();
    if (explanation) renderExplanation();
    if (currentRun.brief) renderBrief(currentRun.brief);
  } else $('detail').textContent = '尚无运行。';
  controls();
}

async function start() {
  currentRun = await post('/api/v1/d/runs');
  logs = currentRun.logs;
  analysis = null; explanation = null;
  renderSignals();
  await refresh();
  progress(`已汇总 ${logs.length} 条来自三类来源的合成日志；还没有作出风险判断。`, '按账号和时间聚合异常事件');
  controls();
}

async function analyze() {
  analysis = await post(`/api/v1/d/runs/${currentRun.id}/analyze`);
  currentRun.phase = 'analyzed'; currentRun.analysis = analysis;
  await refresh();
  progress(`规则把 ${analysis.findings.length} 条候选线索聚合成同账号事件；${analysis.normal_log_ids.length} 条未命中记录保留作参照。`, '阅读辅助研判');
}

async function explain() {
  explanation = await post(`/api/v1/d/runs/${currentRun.id}/explain`);
  currentRun.phase = 'explained'; currentRun.explanation = explanation;
  $('finding').value = explanation.inference_id;
  renderExplanation(); renderAnalysis();
  await refresh();
  progress('辅助研判已生成。凭据泄露和数据外传仍是待核实推测。', '核对日志并提交人工结论');
}

async function review() {
  const evidence_ids = [...document.querySelectorAll('input[name="evidence"]:checked')].map((input) => input.value);
  const decision = document.querySelector('input[name="decision"]:checked')?.value;
  const result = await post(`/api/v1/d/runs/${currentRun.id}/review`, {finding_id: $('finding').value, decision, rationale: $('rationale').value.trim(), evidence_ids});
  currentRun.phase = 'reviewed'; currentRun.review = result;
  await refresh();
  progress('人工核查记录已写入后端审计；该结论不会把推测转换成已证实的账号失陷或数据外传。', '生成四栏事件简报');
}

async function brief() {
  const result = await post(`/api/v1/d/runs/${currentRun.id}/brief`);
  currentRun.phase = 'briefed'; currentRun.brief = result;
  await refresh();
  progress('后端已生成四栏简报。每项保留证据来源；建议仅为文字。', null);
}

async function resetDemo() {
  const data = await post('/api/v1/d/reset');
  currentRun = null; analysis = null; explanation = null;
  $('rationale').value = ''; $('finding').replaceChildren(); $('evidence-select').textContent = '生成辅助研判后载入相关日志。';
  $('download-brief').disabled = true;
  $('detail').textContent = '尚无运行。';
  renderState(data); renderSignals();
  $('log-intro').textContent = '来自认证、API 网关与授权审计的片段，先看它们各自记录了什么。';
  $('log-count').textContent = '等待汇总';
  progress('D 演示已重置：运行、简报和审计已清空；旧运行立即失效。', '汇总本次日志线索');
  controls();
}

async function perform(action) {
  if (busy) return;
  busy = true; setError(); controls();
  try { await action(); }
  catch (error) { setError(`这一步未完成：${error.message}。可检查本地服务，或重置后重试。`); }
  finally { busy = false; controls(); }
}

$('finding').addEventListener('change', renderEvidenceOptions);
$('rationale').addEventListener('input', controls);
$('start').addEventListener('click', () => perform(start));
$('analyze').addEventListener('click', () => perform(analyze));
$('explain').addEventListener('click', () => perform(explain));
$('review').addEventListener('click', () => perform(review));
$('brief-button').addEventListener('click', () => perform(brief));
$('reset').addEventListener('click', () => perform(resetDemo));
$('replay').addEventListener('click', () => perform(async () => { await resetDemo(); await start(); await analyze(); await explain(); }));
$('download-brief').addEventListener('click', () => perform(async () => {
  const data = await api('/api/v1/d/state');
  const report = currentRun && data.runs[currentRun.id]?.brief;
  if (!report) throw new Error('当前运行尚无简报。');
  const url = URL.createObjectURL(new Blob([JSON.stringify(report, null, 2)], {type: 'application/json;charset=utf-8'}));
  const link = document.createElement('a'); link.href = url; link.download = `${report.id}.json`; link.click(); URL.revokeObjectURL(url);
}));

async function initialize() {
  try {
    const health = await api('/api/v1/health');
    $('health').textContent = `本地服务正常 · ${health.model} · 外部服务：${health.external_services ? '已连接' : '未连接'}`;
    const data = await api('/api/v1/d/logs');
    logs = data.items;
    $('time-basis').textContent = data.time_basis;
    renderSignals();
    await refresh();
  } catch (error) { $('health').textContent = `本地服务不可用：${error.message}`; }
  controls();
}

initialize();
