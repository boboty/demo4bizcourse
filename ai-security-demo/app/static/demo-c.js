'use strict';
const el = id => document.getElementById(id);
let cases = [];
let run = null;
let busy = false;
const pause = () => new Promise(resolve => setTimeout(resolve, 250));

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

function progress(message, next) {
  el('progress').textContent = message;
  el('next-step').textContent = next ? `下一步：${next}` : '流程已完成；可重置后再次演示';
}

function currentCase() { return cases.find(item => item.id === el('case-select').value) || cases[0]; }

function renderCase(item) {
  if (!item) return;
  const log = item.log;
  el('case-title').textContent = item.title;
  el('case-summary').textContent = `${log.system} · ${log.time} · ${log.id}`;
  el('record-id').textContent = log.id;
  el('record-date').textContent = log.time;
  const fields = [
    ['模型与去向', `${log.model} · ${log.provider}`], ['资料类别', log.data_class],
    ['接入方式', log.access_method === 'approved_gateway' ? '批准网关' : '直接调用'],
    ['审批与留存', `${log.approval_id || '未登记审批'} · ${log.retention_days == null ? '期限未采集' : `${log.retention_days} 天`}`]
  ];
  const facts = el('record-facts'); facts.replaceChildren();
  for (const [label, value] of fields) {
    const block = document.createElement('div'); block.className = 'c-fact';
    const name = document.createElement('span'); name.textContent = label;
    const content = document.createElement('strong'); content.textContent = value;
    block.append(name, content); facts.append(block);
  }
  el('log').textContent = JSON.stringify(log, null, 2);
  el('policy').textContent = `${item.policy.id}\n${item.policy.text}`;
  el('case-mark').textContent = run ? '本次审计对象' : '待开始';
}

function renderAudits(audits) {
  const body = el('audits'); body.replaceChildren();
  if (!audits.length) { const row = body.insertRow(); const cell = row.insertCell(); cell.colSpan = 4; cell.textContent = '尚无审计记录'; return; }
  for (const item of [...audits].reverse()) {
    const row = body.insertRow();
    [`${item.time}\n${item.request_id}`, `${item.run_id}\n${item.actor_id} / ${item.role}`,
      `${item.object_id}\n${item.action}`, `${item.result}\n${item.reason}`].forEach(value => row.insertCell().textContent = value);
  }
}

function renderEvidence() {
  const root = el('evidence-list'); root.replaceChildren();
  const summaries = {
    'EVC-C-101-LOG': ['平台调用日志与脱敏元数据', '内网模型 · 一般业务信息 · 已脱敏 · 已审批 · 留存 7 天。'],
    'EVC-C-101-APP': ['审批登记摘录', '客服摘要场景已登记使用集团内网模型。'],
    'EVC-C-102-LOG': ['平台调用日志与脱敏元数据', '外部云模型 · 商业敏感信息 · 脱敏未执行 · 无审批 · 留存 90 天。'],
    'EVC-C-102-POL': ['制度条文 POL-AI-02', '商业敏感信息须经批准后使用；外部留存不超过 30 天。'],
    'EVC-C-WHITELIST-01': ['AI 工具准入白名单', '仅准入客服摘要与研发检索工具；browser-shell 不在白名单。'],
    'EVC-C-103-LOG': ['不完整平台调用日志', '内网网关调用；资料类别、用途、脱敏和留存字段缺失。'],
    'EVC-C-103-POL': ['制度条文 POL-AI-03', '关键字段缺失时先补证，不推定违规或合规。']
  };
  for (const item of run.case.evidence) {
    const article = document.createElement('article'); article.className = 'c-evidence';
    const label = document.createElement('label');
    const checkbox = document.createElement('input'); checkbox.type = 'checkbox'; checkbox.className = 'evidence-check'; checkbox.value = item.id;
    const [shortTitle, textSummary] = summaries[item.id] || [item.title, item.text];
    const title = document.createElement('strong'); title.textContent = shortTitle;
    label.append(checkbox, title);
    const summary = document.createElement('p'); summary.className = 'c-evidence-summary';
    summary.textContent = textSummary || item.text;
    const source = document.createElement('details'); source.className = 'c-evidence-source';
    const sourceTitle = document.createElement('summary'); sourceTitle.textContent = '阅读完整证据原文';
    const text = document.createElement('p'); text.textContent = item.text;
    const sourceId = document.createElement('small'); sourceId.textContent = item.id;
    source.append(sourceTitle, text, sourceId);
    source.addEventListener('toggle', () => {
      if (source.open) {
        source.dataset.read = 'true';
        root.querySelectorAll('.c-evidence-source').forEach(other => { if (other !== source) other.open = false; });
      }
      updateEvidenceStatus(); controls();
    });
    article.append(label, summary, source); root.append(article);
  }
  updateEvidenceStatus();
}

function updateEvidenceStatus() {
  const sources = [...document.querySelectorAll('.c-evidence-source')];
  if (!sources.length || stage() !== 'explained') return;
  const read = sources.filter(item => item.dataset.read === 'true').length;
  const checked = document.querySelectorAll('.evidence-check:checked').length;
  el('evidence-status').textContent = `已阅读 ${read}/${sources.length} 项原文 · 已勾选 ${checked} 项`;
}

function stage() { return run?.phase || 'initial'; }

function renderStage() {
  const phase = stage();
  const panelByPhase = {initial: 'panel-start', started: 'panel-start', analyzed: 'panel-analyzed', explained: 'panel-explained', evidence_checked: 'panel-review', reviewed: 'panel-review'};
  const chosen = panelByPhase[phase];
  document.querySelectorAll('.c-panel').forEach(panel => { panel.hidden = panel.id !== chosen; });
  const map = {
    initial: ['课堂步骤 01', '发现异常记录', '等待开始'], started: ['课堂步骤 02', '查看规则线索', '等待分析'],
    analyzed: ['课堂步骤 02', '规则命中', '规则线索可追溯'], explained: ['课堂步骤 03', 'AI 辅助解释', '仅供参考'],
    evidence_checked: ['课堂步骤 05', '人工作出认定', '等待人工提交'], reviewed: ['认定已记录', '人工结论', '后端校验完成']
  };
  const [kicker, title, mark] = map[phase];
  el('focus-kicker').textContent = kicker; el('focus-title').textContent = title; el('focus-mark').textContent = mark;
  const stepByPhase = {initial: 0, started: 1, analyzed: 2, explained: 3, evidence_checked: 4, reviewed: 4};
  document.querySelectorAll('.steps span').forEach((item, index) => {
    const active = index === stepByPhase[phase]; const done = index < stepByPhase[phase];
    item.classList.toggle('active', active); item.classList.toggle('done', done);
    item.dataset.status = active ? 'current' : done ? 'done' : 'upcoming';
  });
  for (const id of ['start', 'analyze', 'explain', 'check', 'review']) el(id).hidden = true;
  const actionForPhase = {initial: 'start', started: 'analyze', analyzed: 'explain', explained: 'check', evidence_checked: 'review'};
  const activeButton = actionForPhase[phase]; if (activeButton) el(activeButton).hidden = false;

  const current = currentCase();
  if (current) {
    const risk = current.id === 'C-CASE-102' ? '存在外部敏感信息、未批准工具与超期留存等异常线索。' : current.id === 'C-CASE-103' ? '日志关键字段缺失，需先补充证据。' : '作为常规调用对照，检查记录是否能支持合规判断。';
    el('panel-start').querySelector('.c-lead').textContent = run ? `已为 ${current.title} 建立本次独立运行。${risk}` : `当前聚焦 ${current.title}。${risk}`;
  }
  if (run) {
    renderCase(run.case);
    if (run.analysis) {
      const hits = run.analysis.hits || [];
      el('rule-result').replaceChildren();
      const headline = document.createElement('strong');
      headline.className = 'c-rule-count';
      headline.textContent = run.analysis.status === 'evidence_needed' ? `需补证 · ${hits.length} 条规则线索` : hits.length ? `发现 ${hits.length} 条待核查线索` : '未命中规则 · 仍需人工核对';
      const list = document.createElement('ul');
      for (const hit of hits) { const item = document.createElement('li'); item.textContent = hit.text; list.append(item); }
      if (!hits.length) { const item = document.createElement('li'); item.textContent = '规则未发现异常；请依据原始记录和制度作出人工判断。'; list.append(item); }
      el('rule-result').append(headline, list);
      el('analysis-detail').textContent = JSON.stringify(run.analysis, null, 2);
    }
    if (run.explanation) {
      const needsEvidence = run.case_id === 'C-CASE-103';
      el('explanation-text').textContent = needsEvidence
        ? '关键调用字段不完整，先补证再判断。'
        : run.analysis.hits.length ? '规则对照发现待核查风险线索。' : '当前规则未发现异常线索。';
      const list = el('pending-list'); list.replaceChildren();
      const pendingText = needsEvidence ? '核实资料类别、用途、脱敏和留存记录。' : '核对平台日志、审批与制度原文。';
      const item = document.createElement('li'); item.textContent = pendingText; list.append(item);
      const uncertainty = document.createElement('li'); uncertainty.className = 'c-uncertainty';
      uncertainty.textContent = needsEvidence ? '字段缺失，无法判断合规或违规。' : run.analysis.hits.length ? '风险线索仅供筛查，不是违规结论。' : '规则未命中，不等于可以认定合规。';
      list.append(uncertainty);
    }
    if (run.evidence_check) {
      const verified = run.evidence_check.complete ? `已核对全部 ${run.evidence_check.checked.length} 项原始证据` : `已核对 ${run.evidence_check.checked.length} 项，材料不完整`;
      el('evidence-status').textContent = verified;
      el('review-evidence-status').textContent = verified;
    }
    if (run.review) {
      el('review-result').textContent = `${run.review.reviewer.name}认定：${run.review.decision}。理由：${run.review.rationale}`;
      el('conclusion').textContent = `人工最终认定为“${run.review.decision}”。结论关联已核对的原始证据、理由与固定人工身份。`;
      el('review-result').classList.add('is-final');
    } else {
      el('review-result').classList.remove('is-final');
      if (phase === 'initial' || phase === 'started') el('conclusion').textContent = '运行已建立；当前没有合规结论。下一步由确定性规则筛查线索。';
      else if (phase === 'analyzed') el('conclusion').textContent = `${run.analysis.hits.length ? `发现 ${run.analysis.hits.length} 条待核查线索` : '规则未命中'}；均不构成违规认定。`;
      else if (phase === 'explained') el('conclusion').textContent = '辅助解释仅供参考；请查看原始记录和制度，人工核对后再认定。';
      else if (phase === 'evidence_checked') el('conclusion').textContent = '证据核对已记录；结论仍待人工提交并由后端校验。';
    }
  } else {
    el('conclusion').textContent = '尚无运行，尚无结论。规则命中和 AI 解释都不等于违规认定。';
    el('review-result').textContent = '结论由后端校验已核对证据和理由后记录。';
    el('review-result').classList.remove('is-final');
    el('evidence-status').textContent = '尚未记录证据核对。';
    el('review-evidence-status').textContent = '—';
  }
  updateEvidenceStatus();
  const steps = {initial: ['尚未开始', '建立审计案例'], started: [`已建立 ${run?.case_id} · 运行 ${run?.id}`, '查看确定性规则线索'], analyzed: [`规则分析完成 · ${run?.analysis?.hits.length} 条线索`, '阅读离线辅助解释'], explained: ['辅助解释已生成 · 不代表违规认定', '阅读原始材料并核对证据'], evidence_checked: ['原始证据核对已记录', '填写人工结论与理由'], reviewed: [`人工认定完成 · ${run?.review?.decision}`, null]};
  progress(...steps[phase]);
  el('export').disabled = busy || !run?.analysis;
}

function controls() {
  const phase = stage();
  for (const id of ['reset', 'start', 'replay', 'decision', 'rationale', 'export']) el(id).disabled = busy;
  el('case-select').disabled = busy || Boolean(run);
  el('start').disabled = busy || phase !== 'initial';
  el('analyze').disabled = busy || phase !== 'started';
  el('explain').disabled = busy || phase !== 'analyzed';
  const selectedEvidence = [...document.querySelectorAll('.evidence-check:checked')];
  const evidenceSources = [...document.querySelectorAll('.c-evidence-source')];
  const allEvidenceRead = evidenceSources.length > 0 && evidenceSources.every(item => item.dataset.read === 'true');
  el('check').disabled = busy || phase !== 'explained' || selectedEvidence.length === 0 || !allEvidenceRead;
  el('review').disabled = busy || phase !== 'evidence_checked';
  el('export').disabled = busy || !run?.analysis;
  document.querySelectorAll('.evidence-check').forEach(item => { item.disabled = busy || phase !== 'explained'; });
  renderStage();
}

async function task(fn) {
  if (busy) return;
  busy = true;
  try { controls(); el('error').hidden = true; await fn(); }
  catch (error) { el('error').textContent = `这一步未完成：${error.message}。可检查本地服务，或重置 C 后重试。`; el('error').hidden = false; }
  finally { busy = false; controls(); }
}

async function refresh() {
  const {data} = await api('c/state');
  renderAudits(data.audits);
  if (run?.id && data.runs[run.id]) run = data.runs[run.id];
  el('detail').textContent = run ? JSON.stringify(run, null, 2) : '尚无运行。';
  renderStage();
}

async function loadCases() {
  const {data} = await api('c/cases'); cases = data.items;
  const select = el('case-select'); select.replaceChildren();
  for (const item of cases) { const option = document.createElement('option'); option.value = item.id; option.textContent = `${item.id} · ${item.title}`; select.append(option); }
  select.value = cases.find(item => item.id === 'C-CASE-102')?.id || cases[0]?.id;
  renderCase(currentCase()); renderStage();
}

async function start() {
  const {data} = await api('c/runs', {case_id: currentCase().id});
  run = data; renderCase(run.case); renderEvidence();
  el('analysis-detail').textContent = '尚未分析。';
  el('rationale').value = ''; el('review-result').textContent = '结论由后端校验已核对证据和理由后记录。';
  await refresh();
}

async function analyze() {
  progress('正在由本地后端比对调用字段与制度…', '查看规则线索'); await pause();
  await api(`c/runs/${run.id}/analyze`, {}); await refresh();
}

async function explain() {
  progress('离线辅助解释正在整理规则事实与不确定性…', '生成辅助解释'); await pause();
  await api(`c/runs/${run.id}/explain`, {}); await refresh();
}

async function checkEvidence() {
  const evidenceIds = [...document.querySelectorAll('.evidence-check:checked')].map(item => item.value);
  if (!evidenceIds.length) throw new Error('请先勾选已阅读的原始证据');
  progress('后端正在校验证据是否属于本次运行…', '记录证据核对'); await pause();
  await api(`c/runs/${run.id}/evidence-check`, {evidence_ids: evidenceIds}); await refresh();
}

async function review() {
  progress('后端正在核验已核对证据、人工理由与结论…', '提交人工认定'); await pause();
  const evidenceIds = run.evidence_check.checked_ids;
  await api(`c/runs/${run.id}/review`, {decision: el('decision').value, rationale: el('rationale').value, evidence_ids: evidenceIds});
  await refresh();
}

async function exportQuestions() {
  const {data} = await api(`c/runs/${run.id}/candidate-questions`);
  const blob = new Blob([JSON.stringify(data, null, 2)], {type: 'application/json;charset=utf-8'});
  const url = URL.createObjectURL(blob); const link = document.createElement('a');
  link.href = url; link.download = `demo-c-${run.id}-candidate-questions.json`; link.click(); URL.revokeObjectURL(url);
}

async function reset() {
  const {data} = await api('c/reset', {});
  run = null; renderAudits(data.audits); el('detail').textContent = '尚无运行。';
  el('analysis-detail').textContent = '尚未分析。';
  el('rationale').value = ''; el('review-result').textContent = '结论由后端校验已核对证据和理由后记录。';
  renderCase(currentCase()); await refresh();
}

el('case-select').addEventListener('change', () => { if (!run) { renderCase(currentCase()); renderStage(); } });
el('evidence-list').addEventListener('change', () => { updateEvidenceStatus(); controls(); });
el('reset').addEventListener('click', () => task(reset));
el('start').addEventListener('click', () => task(start));
el('analyze').addEventListener('click', () => task(analyze));
el('explain').addEventListener('click', () => task(explain));
el('check').addEventListener('click', () => task(checkEvidence));
el('review').addEventListener('click', () => task(review));
el('export').addEventListener('click', () => task(exportQuestions));
el('replay').addEventListener('click', () => task(async () => {
  await reset(); await start(); await pause(); await analyze(); await pause(); await explain(); await pause();
  document.querySelectorAll('.evidence-check').forEach(item => { item.checked = true; });
  controls();
  await checkEvidence();
  progress('复演已停在人工认定之前；请阅读证据、选择结论并填写理由。', '人工作出认定');
}));

task(async () => {
  const {data} = await api('health'); el('health').textContent = `本地服务正常 · ${data.model} · 无外部服务`;
  await loadCases(); await refresh();
}).catch(() => { el('health').textContent = '本地服务不可用，请检查启动终端'; });
