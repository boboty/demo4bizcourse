'use strict';
const el = id => document.getElementById(id);
let run = null;
let busy = false;
let assistantFinding = null;
let reviewed = false;
let previewed = false;
let completedBoundary = false;
const fieldCategories = {ordinary: '一般业务', personal: '个人信息', commercial: '商业敏感'};

async function api(path, body) {
  const requestId = crypto.randomUUID();
  let response;
  try {
    response = await fetch(`/api/v1/${path}`, body === undefined ? {headers: {'X-Request-ID': requestId}} : {
      method: 'POST', headers: {'Content-Type': 'application/json', 'X-Request-ID': requestId}, body: JSON.stringify(body)
    });
  } catch (error) {
    throw new Error(`${error.message}；请求标识 ${requestId}`);
  }
  return {response, data: await response.json()};
}
function controls() {
  ['reset', 'identify', 'assistant', 'correct', 'preview', 'process', 'boundary-check', 'unauthorized-check']
    .forEach(id => { el(id).disabled = busy; });
  el('identify').disabled = busy || completedBoundary;
  el('assistant').disabled = busy || !run || !!assistantFinding;
  el('correct').disabled = busy || !assistantFinding || reviewed;
  el('preview').disabled = busy || !reviewed || previewed;
  el('process').disabled = busy || !previewed;
}
async function task(fn) {
  if (busy) return;
  busy = true; controls(); el('error').hidden = true;
  try { await fn(); }
  catch (error) {
    el('error').textContent = `操作未完成：${error.message}。可重置 A 后重试。`;
    el('error').hidden = false;
    el('conclusion').textContent = '本次操作未完成；后端没有把错误显示为成功结果。';
  } finally { busy = false; controls(); }
}
function progress(message, step) {
  el('progress').textContent = message;
  for (let index = 1; index <= 4; index++) {
    const item = el(`step${index}`);
    item.classList.toggle('active', index === step);
    item.classList.toggle('done', index < step);
  }
}
function setStage(title, copy) {
  el('stage-title').textContent = title;
  el('stage-copy').textContent = copy;
}
function setChip(id, text, kind = '') {
  const chip = el(id); chip.textContent = text; chip.className = `state-chip ${kind}`.trim();
}
function clearDocumentResults() {
  run = null; assistantFinding = null; reviewed = false; previewed = false; completedBoundary = false;
  el('source').replaceChildren(document.createTextNode('某产业集团采购合同 HT-DEMO-017：供应商恒川设备（虚构）；签订日期 2026-10-01；采购设备 40 台，总金额 128000 元。经办人林岚，身份证号 110101199001010016（虚构无效示例），联系电话 19900000000（占位号码）。商业条款：单价 3200 元/台，年度采购上限 200 台，达到 100 台后返利 8%。当前状态：待归档。'));
  el('field-chips').innerHTML = '<span class="empty">运行识别后，字段证据会在原文和此处同步出现。</span>';
  el('fields').replaceChildren(); const row = el('fields').insertRow(); const cell = row.insertCell(); cell.colSpan = 3; cell.textContent = '尚未识别';
  el('review-box').hidden = true;
  setChip('doc-state', '等待识别'); setChip('authorization', '尚未申请');
  el('before-summary').textContent = '合同原文保留在本地沙箱。';
  el('redacted').textContent = '等待后端授权与脱敏。';
  el('full-before').textContent = '等待后端预览。'; el('full-after').textContent = '等待后端授权与脱敏。';
  el('redaction-notice').textContent = '需要先完成人工核查。脱敏结果不会自动提交或扩大权限。';
  el('audit-detail').textContent = '尚无详情';
}
function updateComparison(before, after) {
  const fields = [
    ['身份证号', '110101199001010016'], ['联系电话', '19900000000'],
    ['合同金额', '128000 元'], ['采购单价', '3200 元/台'], ['返利条件', '100 台后返利 8%']
  ];
  el('before-summary').textContent = fields.map(([label, value]) => `${label}：${before.includes(value) ? value : '—'}`).join('\n');
  el('redacted').textContent = fields.map(([label, value]) => `${label}：${after.includes(value) ? value : (before.includes(value) ? '[已脱敏]' : '—')}`).join('\n');
  el('full-before').textContent = before;
  el('full-after').textContent = after;
}
function renderFields(fields) {
  const source = el('source');
  const text = run.source_text;
  const ordered = [...fields].sort((a, b) => a.start - b.start);
  source.replaceChildren();
  let cursor = 0;
  for (const field of ordered) {
    if (field.start < cursor) continue;
    source.append(document.createTextNode(text.slice(cursor, field.start)));
    const mark = document.createElement('mark'); mark.dataset.category = field.category;
    mark.dataset.fieldKey = field.key; mark.textContent = text.slice(field.start, field.end);
    source.append(mark); cursor = field.end;
  }
  source.append(document.createTextNode(text.slice(cursor)));
  const chips = el('field-chips'); chips.replaceChildren();
  for (const field of fields) {
    const chip = document.createElement('span'); chip.className = `field-chip ${field.category}`;
    chip.textContent = `${field.label} · ${fieldCategories[field.category]}`; chips.append(chip);
  }
  const rows = el('fields'); rows.replaceChildren();
  for (const field of fields) {
    const tr = rows.insertRow();
    [field.label, fieldCategories[field.category], field.rule].forEach(value => tr.insertCell().textContent = value);
  }
}
async function renderAudits() {
  const {data, response} = await api('a/state');
  if (!response.ok) throw new Error(data.error?.message || '无法读取审计状态');
  const rows = el('audits'); rows.replaceChildren();
  if (!data.audits.length) { const row = rows.insertRow(); const cell = row.insertCell(); cell.colSpan = 3; cell.textContent = '尚无记录'; }
  for (const item of [...data.audits].reverse()) {
    const row = rows.insertRow();
    [`${item.time}\n请求 ${item.request_id}`, `${item.document_id} · ${item.action}`, `${item.authorization} · ${item.reason}`]
      .forEach(value => row.insertCell().textContent = value);
  }
  const latest = data.audits.at(-1);
  el('audit-detail').textContent = latest ? JSON.stringify(latest, null, 2) : '尚无详情';
  return data;
}
async function reset() {
  const {data, response} = await api('a/reset', {});
  if (!response.ok) throw new Error(data.error?.message || 'A 重置失败');
  clearDocumentResults();
  el('conclusion').textContent = '尚未识别。原文中的金额、个人信息和商业条款会被分别处理。';
  await renderAudits(); setStage('先看清合同中的字段', '固定合同会由后端规则识别。识别只说明“是什么”，不会改变“能不能处理”。');
  progress('当前：查看合同原文　·　下一步：运行后端规则识别', 1); controls();
}
async function identify(documentId = 'PO-A-017') {
  clearDocumentResults(); controls();
  setStage('合同原文 → 规则识别', '后端按固定规则标出业务字段、个人信息和商业敏感值；分类结果不会修改授权。');
  progress('当前：后端识别字段　·　下一步：查看辅助识别是否出现误报', 1);
  const {response, data} = await api(`a/documents/${documentId}/identify`, {});
  if (!response.ok) {
    if (data.error?.code === 'CONFIDENTIAL_BOUNDARY') return showConfidentialBlock(documentId, data.error);
    throw new Error(`${data.error?.message || '规则识别失败'}；请求标识 ${data.error?.request_id || response.headers.get('X-Request-ID')}`);
  }
  run = data; renderFields(data.fields); setChip('doc-state', '已识别 · 尚未处理');
  el('before-summary').textContent = '规则已定位字段；尚未执行脱敏。';
  el('conclusion').textContent = '后端规则已识别合同字段。识别结果没有改变资料授权，也没有执行处理。';
  el('audit-detail').textContent = JSON.stringify(data.audit, null, 2);
  await renderAudits(); setStage('规则识别完成', '原文高亮与字段分类来自真实后端规则。下一步看离线辅助识别能否被原文证据核实。');
  progress('已完成：原文规则识别　·　当前：查看辅助识别　·　下一步：人工核查误报', 2); controls();
}
async function assistantReview() {
  const {response, data} = await api(`a/runs/${run.id}/assistant-review`, {});
  if (!response.ok) throw new Error(data.error?.message || '辅助识别失败');
  assistantFinding = data.finding;
  const mark = el('source').querySelector('[data-field-key="amount"]');
  if (mark) { mark.dataset.category = 'false-positive'; mark.title = '离线辅助识别提出误报，等待人工核查'; }
  el('review-box').hidden = false;
  el('conclusion').textContent = `辅助识别把“${data.finding.evidence}”误报为个人信息。请对照合同原文核查，再由人确认修正。`;
  setStage('辅助识别提出一处误报', '“128000 元”是合同金额。辅助结论只是线索，不能替代人工证据判断。');
  await renderAudits(); progress('已完成：规则识别、辅助识别　·　当前：人工核查　·　下一步：确认金额属于一般业务资料', 3); controls();
}
async function correctFinding() {
  const payload = {evidence: assistantFinding.evidence, suggested_category: assistantFinding.suggested_category,
    corrected_category: el('correction-category').value, reason: el('correction-reason').value};
  const {response, data} = await api(`a/runs/${run.id}/correction`, payload);
  if (!response.ok) throw new Error(data.error?.message || '人工修正未通过证据核对');
  reviewed = data.status === 'human_corrected';
  const mark = el('source').querySelector('[data-field-key="amount"]');
  if (mark) { mark.dataset.category = 'ordinary'; mark.title = '人工根据合同原文纠正辅助识别误报'; }
  el('conclusion').textContent = `人工已核对原文：${data.evidence} 从“个人信息”改为“一般业务资料”。下一步由后端检查授权。`;
  setStage('人工核查已留痕', '后端记录了证据、修正类别和理由。继续申请脱敏预览时，由服务端独立检查资料授权。');
  await renderAudits(); progress('已完成：规则识别、辅助识别、人工修正　·　当前：申请后端授权预览', 4); controls();
}
async function preview() {
  const {response, data} = await api(`a/runs/${run.id}/preview`, {});
  if (!response.ok) throw new Error(data.error?.message || '预览请求失败');
  if (data.authorization === 'DENY') {
    setChip('authorization', '后端拒绝 · 未授权', 'deny');
    el('redacted').textContent = '未生成预览；后端没有调用脱敏逻辑。';
    el('redaction-notice').textContent = data.message;
    el('conclusion').textContent = '已经识别、也已人工核查，仍不代表可以处理。后端授权拒绝，没有生成脱敏结果。';
    setStage('授权检查拒绝处理', '未授权分支由真实后端策略拒绝。可直接重置，或切换到已授权合同继续主流程。');
    await renderAudits(); progress('已完成：人工核查　·　结果：授权拒绝　·　脱敏预览未生成', 4); controls(); return;
  }
  previewed = true; setChip('authorization', '后端允许本地预览', 'allow');
  updateComparison(data.before, data.after);
  el('redaction-notice').textContent = `${data.message} 原文中的个人信息与商业敏感值遮盖，一般业务信息保留。`;
  el('conclusion').textContent = '后端授权允许生成本地脱敏预览。还没有进入下一步，须由人明确确认。';
  setStage('授权允许本地预览', '对照字段变化：个人与商业敏感信息被遮盖，一般业务字段保留。确认动作仍由人发起。');
  await renderAudits(); progress('已完成：规则识别、辅助识别、人工核查　·　当前：检查脱敏前后　·　下一步：人工确认', 4); controls();
}
async function processRun() {
  const {response, data} = await api(`a/documents/${run.document_id}/process/${run.id}`, {confirmation: 'CONFIRM_NEXT_STEP'});
  if (response.status === 403 && data.authorization === 'DENY') {
    setChip('authorization', '后端拒绝 · 未授权', 'deny');
    el('redacted').textContent = '未调用脱敏逻辑；字段保持原样。';
    el('redaction-notice').textContent = '后端拒绝发生在脱敏函数之前，未生成处理结果。';
    el('conclusion').textContent = '后端授权拒绝，未执行脱敏。';
  } else if (response.ok) {
    setChip('authorization', '授权通过 · 已完成脱敏', 'allow');
    updateComparison(data.before, data.after);
    el('redaction-notice').textContent = `${data.notice} 已遮盖：${data.redacted_fields.join('、')}；保留一般业务字段：${data.retained.join('、')}。`;
    el('conclusion').textContent = '人工确认后，后端完成了真实字符脱敏并记录审计。脱敏不会改变涉密分类或扩展权限。';
  } else throw new Error(`${data.error?.message || '处理失败'}；请求标识 ${data.error?.request_id || response.headers.get('X-Request-ID')}`);
  await renderAudits(); setStage(response.ok ? '人工确认完成' : '后端拒绝处理', response.ok ? '业务结果、授权决定与审计记录均来自后端。可重置后再次演示。' : '后端未授权，脱敏没有执行。');
  progress(response.ok ? '已完成：识别、人工核查、授权、脱敏和审计　·　可重置复演' : '授权拒绝　·　未执行脱敏', 4); controls();
}
async function unauthorizedCheck() {
  clearDocumentResults();
  setStage('未授权对照：真实后端拒绝', '使用固定未授权合同调用识别和处理接口。页面不预设拒绝结果，响应直接来自后端。');
  progress('当前：请求未授权合同　·　后端将核对处理权限', 1);
  const identified = await api('a/documents/PO-A-018/identify', {});
  if (!identified.response.ok) throw new Error(identified.data.error?.message || '无法建立未授权合同运行');
  run = identified.data; renderFields(run.fields); setChip('doc-state', '未授权合同 · 已识别');
  const denied = await api(`a/documents/PO-A-018/process/${run.id}`, {confirmation: 'CONFIRM_NEXT_STEP'});
  if (denied.response.status !== 403 || denied.data.authorization !== 'DENY') throw new Error('后端未返回预期拒绝');
  setChip('authorization', '后端拒绝 · 未授权', 'deny');
  el('full-before').textContent = run.source_text;
  el('before-summary').textContent = '合同字段已识别。\n授权状态：未授予';
  el('redacted').textContent = '无脱敏结果'; el('full-after').textContent = '后端未授权；没有执行脱敏。';
  el('redaction-notice').textContent = '后端在脱敏函数之前拒绝，处理计数不增加。';
  el('conclusion').textContent = '对照结果：识别可以成功，未授权处理仍被真实后端拒绝。';
  el('audit-detail').textContent = JSON.stringify(denied.data.audit, null, 2);
  completedBoundary = true;
  await renderAudits(); setStage('未授权处理被拒绝', '拒绝决定来自后端固定授权规则；业务数据没有生成脱敏结果。');
  progress('已完成：未授权合同识别　·　结果：后端拒绝处理　·　无脱敏结果', 4); controls();
}
async function showConfidentialBlock(documentId, error) {
  run = null; el('review-box').hidden = true; setChip('doc-state', '涉密 · 前置阻断'); setChip('authorization', '禁止进入普通处理链', 'deny');
  el('source').textContent = `资料标识：${documentId}　·　分类：涉密\n正文未读取、未存储、未展示。`;
  el('field-chips').innerHTML = '<span class="empty">没有普通识别字段；涉密正文未进入处理链。</span>';
  el('before-summary').textContent = '涉密正文未读取。'; el('redacted').textContent = '未调用脱敏逻辑'; el('full-before').textContent = '涉密正文未读取。'; el('full-after').textContent = '未调用脱敏逻辑。';
  el('redaction-notice').textContent = '涉密分类在普通识别、脱敏和上传入口前阻断。';
  el('conclusion').textContent = '涉密不是靠脱敏解决的问题。后端在读取正文和普通处理之前拒绝请求。';
  el('audit-detail').textContent = JSON.stringify(error, null, 2);
  completedBoundary = true;
  await renderAudits(); setStage('涉密边界在入口前阻断', '该支路只显示分类标记。后端拒绝请求，不读取、不记录涉密正文。');
  progress('结果：涉密请求已被后端前置拒绝　·　正文未读取', 4); controls();
}
async function boundaryCheck() {
  clearDocumentResults();
  setStage('涉密资料：验证三个入口均被阻断', '每个请求只传固定资料 ID，不传正文；识别、脱敏、上传均由后端先行拒绝。');
  const calls = [
    ['识别', 'a/documents/DOC-CLASSIFIED-009/identify'],
    ['脱敏', 'a/documents/DOC-CLASSIFIED-009/process/boundary-probe'],
    ['上传', 'a/documents/DOC-CLASSIFIED-009/upload']
  ];
  const results = [];
  for (const [label, path] of calls) {
    const result = await api(path, {});
    if (result.response.status !== 403 || result.data.error?.code !== 'CONFIDENTIAL_BOUNDARY') throw new Error(`${label}入口没有按涉密策略拒绝`);
    results.push(`${label}：已拒绝`);
  }
  run = null; setChip('doc-state', '涉密 · 前置阻断'); setChip('authorization', '三个入口均拒绝', 'deny');
  el('source').textContent = '资料标识：DOC-CLASSIFIED-009　·　分类：涉密\n正文未读取、未存储、未展示。';
  el('field-chips').innerHTML = '<span class="empty">三个入口均未建立普通处理运行。</span>';
  el('before-summary').textContent = '涉密正文未读取。'; el('redacted').textContent = '未生成脱敏结果'; el('full-before').textContent = '涉密正文未读取。'; el('full-after').textContent = '未生成脱敏结果。';
  el('redaction-notice').textContent = `${results.join('；')}。涉密正文未进入审计记录。`;
  el('conclusion').textContent = '识别、脱敏和上传都在普通处理逻辑之前被阻断。';
  const state = await renderAudits();
  el('redaction-notice').textContent += ` 处理计数：识别 ${state.counters.identification}、脱敏 ${state.counters.deidentification}、上传 ${state.counters.upload}。`;
  setStage('涉密边界已验证', '后端拒绝三个处理入口；普通处理计数未因涉密请求增加。');
  completedBoundary = true;
  progress('结果：涉密识别、脱敏、上传均被前置阻断　·　正文未进入普通链路', 4); controls();
}
el('reset').onclick = () => task(reset);
el('assistant').onclick = () => task(assistantReview);
el('correct').onclick = () => task(correctFinding);
el('preview').onclick = () => task(preview);
el('process').onclick = () => task(processRun);
el('unauthorized-check').onclick = () => task(unauthorizedCheck);
el('boundary-check').onclick = () => task(boundaryCheck);
el('identify').onclick = () => task(() => identify('PO-A-017'));
task(async () => {
  const {response, data} = await api('health');
  if (!response.ok) throw new Error(data.error?.message || '本地服务不可用');
  el('health').textContent = '本地服务正常 · 离线'; await renderAudits(); controls();
}).then(() => { if (!el('error').hidden) el('health').textContent = '本地服务不可用'; });
