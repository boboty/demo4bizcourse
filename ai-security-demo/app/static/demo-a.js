'use strict';
const el = id => document.getElementById(id);
let run = null;
let busy = false;
let assistantFinding = null;
let reviewed = false;
let previewed = false;
const pause = () => new Promise(resolve => setTimeout(resolve, 350));
function progress(text, step) {
  el('progress').textContent = text;
  for (let n = 1; n <= 4; n++) el(`step${n}`).classList.toggle('active', n <= step);
}
async function api(path, body) {
  const requestId = crypto.randomUUID();
  let response;
  try {
    response = await fetch(`/api/v1/${path}`, body === undefined ? {headers: {'X-Request-ID': requestId}} : {
      method: 'POST', headers: {'Content-Type': 'application/json', 'X-Request-ID': requestId}, body: JSON.stringify(body)
    });
  } catch (error) {
    throw new Error(`${error.message} 请求标识：${requestId}`);
  }
  const data = await response.json();
  return {response, data};
}
function controls() {
  ['reset', 'identify', 'boundary-check', 'replay', 'document-select'].forEach(id => { el(id).disabled = busy; });
  el('assistant').disabled = busy || !run;
  el('correct').disabled = busy || !assistantFinding;
  el('preview').disabled = busy || !reviewed;
  el('process').disabled = busy || !previewed;
}
async function task(fn) {
  if (busy) return;
  busy = true; controls(); el('error').hidden = true;
  try { await fn(); }
  catch (error) {
    el('error').textContent = `执行未完成：${error.message}。检查本地服务后重置 A 并重试。`;
    el('error').hidden = false;
    progress('执行中断；重置 A 后可从初态复演。', 0);
  } finally { busy = false; controls(); }
}
function renderAudits(audits) {
  const rows = el('audits'); rows.replaceChildren();
  if (!audits.length) { const row = rows.insertRow(); const cell = row.insertCell(); cell.colSpan = 5; cell.textContent = '尚无审计记录'; }
  for (const item of [...audits].reverse()) {
    const row = rows.insertRow();
    [`${item.time}\n${item.request_id}`, `${item.run_id || '边界检查'}\n${item.actor_id} / ${item.role}`,
      `${item.document_id}\n${item.action}`, `${item.authorization}\n${item.rules.join(', ') || '边界策略'}`,
      item.reason].forEach(value => row.insertCell().textContent = value);
  }
}
async function refresh() {
  const {data, response} = await api('a/state');
  if (!response.ok) throw new Error(`${data.error?.message || '无法读取 A 状态'} 请求标识：${data.error?.request_id || response.headers.get('X-Request-ID')}`);
  renderAudits(data.audits);
}
function clearDocumentResults() {
  run = null;
  assistantFinding = null; reviewed = false; previewed = false;
  el('source').textContent = '选择资料后点击“识别字段”。涉密示例正文不会提供。';
  el('classification').textContent = '识别结果与处理授权分开判断。';
  el('fields').replaceChildren();
  const row = el('fields').insertRow(); const cell = row.insertCell(); cell.colSpan = 3; cell.textContent = '尚未识别';
  el('authorization').textContent = '等待后端核验。页面声明的角色、类别或授权不参与决定。';
  el('boundary-result').textContent = '涉密资料只显示标识和处理限制。';
  el('redacted').textContent = '等待授权后端结果。';
  el('redaction-notice').textContent = '未处理。普通业务字段应保留，个人信息与商业敏感值由后端遮盖。';
  el('audit-detail').textContent = '尚无详情';
  el('assistant-finding').textContent = '等待运行离线辅助识别。';
}
async function reset() {
  const {data, response} = await api('a/reset', {});
  if (!response.ok) throw new Error(data.error?.message || '重置失败');
  el('document-select').value = 'PO-A-017';
  clearDocumentResults();
  el('conclusion').textContent = '先识别，再由后端独立判断处理权限。点击“识别字段”开始。';
  renderAudits(data.audits);
  progress('A 已独立重置：运行与审计清空，旧运行标识失效。', 0);
}
async function assistantReview() {
  if (!run) return;
  progress('运行固定离线辅助识别示例…', 2);
  const {response, data} = await api(`a/runs/${run.id}/assistant-review`, {});
  if (!response.ok) throw new Error(data.error?.message || '辅助识别失败');
  assistantFinding = data.finding;
  el('assistant-finding').textContent = `${data.simulation}\n${data.finding.id}：证据“${data.finding.evidence}”被建议为“${data.finding.suggested_category}”。${data.finding.reason}`;
  el('conclusion').textContent = '辅助识别出现一处可核对误报；先由人回到原文证据修正，才能查看脱敏预览。';
  await refresh(); progress('辅助识别完成；停在人工核对。', 2); controls();
}
async function correctFinding() {
  if (!run || !assistantFinding) return;
  const {response, data} = await api(`a/runs/${run.id}/correction`, {
    evidence: el('correction-evidence').value,
    suggested_category: assistantFinding.suggested_category,
    corrected_category: el('correction-category').value,
    reason: el('correction-reason').value
  });
  if (!response.ok) throw new Error(data.error?.message || '人工修正未通过证据核对');
  reviewed = data.status === 'human_corrected';
  el('assistant-finding').textContent += `\n人工已核对：${data.evidence} 从“${data.suggested_category}”修正为“${data.corrected_category}”。`;
  progress('人工修正已记录；可请求后端授权并查看脱敏预览。', 3); await refresh(); controls();
}
async function preview() {
  if (!run || !reviewed) return;
  const {response, data} = await api(`a/runs/${run.id}/preview`, {});
  if (!response.ok) throw new Error(data.error?.message || '脱敏预览失败');
  if (data.authorization === 'DENY') {
    el('authorization').textContent = data.message;
    el('redacted').textContent = '后端未授权；没有生成脱敏预览。';
    previewed = false; progress('后端授权拒绝；不可进入下一步。', 4); controls(); return;
  }
  el('redacted').textContent = `脱敏前：\n${data.before}\n\n脱敏预览：\n${data.after}`;
  el('redaction-notice').textContent = `${data.message} 预览不是外部提交，也未自动确认。`;
  el('authorization').textContent = '固定后端策略允许查看本地预览；是否进入下一步仍由人决定。';
  previewed = true; progress('脱敏预览已生成；停在人工确认按钮前。', 4); await refresh(); controls();
}
async function identify(documentId = el('document-select').value) {
  clearDocumentResults(); controls();
  progress('正在请求固定身份的后端规则识别…', 1); await pause();
  const {response, data} = await api(`a/documents/${documentId}/identify`, {});
  if (!response.ok) {
    if (data.error?.code === 'CONFIDENTIAL_BOUNDARY') {
      el('source').textContent = `资料标识：${documentId}\n分类标记：涉密\n限制：禁止进入普通识别、脱敏或上传链。\n正文：未读取、未存储、未展示。`;
      el('classification').textContent = '涉密边界在普通处理入口前阻断。';
      el('authorization').textContent = `${data.error.message} 请求标识：${data.error.request_id}`;
      el('conclusion').textContent = '涉密资料只展示禁止边界；脱敏不能解除该资料的涉密限制。';
      el('boundary-result').textContent = data.error.message;
      await refresh(); progress('涉密资料识别请求已拒绝；未读取正文。', 4); return null;
    }
    throw new Error(`${data.error?.message || '识别失败'} 请求标识：${data.error?.request_id || response.headers.get('X-Request-ID')}`);
  }
  run = data;
  el('source').textContent = data.source_text;
  el('classification').textContent = `${data.classification} · ${data.simulation} · 运行 ${data.id}`;
  const fields = el('fields'); fields.replaceChildren();
  for (const item of data.fields) {
    const row = fields.insertRow();
    [`${item.label} · 字符 ${item.start}–${item.end}`, `${item.category} · ${item.rule}`, item.evidence]
      .forEach(value => row.insertCell().textContent = value);
  }
  el('authorization').textContent = '已识别。尚未处理；下一步由后端依据固定资料授权策略决定。';
  el('redacted').textContent = '等待后端授权与脱敏结果。';
  el('audit-detail').textContent = JSON.stringify(data.audit, null, 2);
  el('conclusion').textContent = '识别准确展示规则命中，但没有改变服务端授权状态。';
  await refresh(); progress('确定性规则识别完成；授权尚未申请。', 2); controls(); return data;
}
async function processRun() {
  if (!run) return;
  progress('后端正在核对固定身份、资料授权和规则…', 3); await pause();
  const {response, data} = await api(`a/documents/${run.document_id}/process/${run.id}`, {confirmation: 'CONFIRM_NEXT_STEP'});
  el('authorization').textContent = `${data.authorization} · ${data.audit.reason} · 运行 ${data.run_id}`;
  el('audit-detail').textContent = JSON.stringify(data.audit, null, 2);
  if (response.status === 403 && data.authorization === 'DENY') {
    el('redacted').textContent = '未调用脱敏逻辑；识别到的值保持原样。';
    el('redaction-notice').textContent = '拒绝无副作用：后端授权检查先于脱敏函数，计数不会增加。';
    el('conclusion').textContent = '已经识别不等于允许处理。固定身份对该合同没有授权，后端拒绝且不执行脱敏。';
  } else if (response.ok) {
    el('redacted').textContent = `脱敏前：\n${data.before}\n\n脱敏后：\n${data.after}`;
    el('redaction-notice').textContent = `${data.notice} 保留一般业务字段：${data.retained.join('、')}。已遮盖：${data.redacted_fields.join('、')}。`;
    el('conclusion').textContent = '后端授权后执行了真实字符遮盖；一般业务值保留。脱敏不会抹掉资料的涉密分类或新增使用权限。';
  } else throw new Error(`${data.error?.message || '处理失败'} 请求标识：${data.error?.request_id || response.headers.get('X-Request-ID')}`);
  await refresh(); progress(response.ok ? '授权通过并完成前后比较与审计。' : '授权拒绝；未进入脱敏函数。', 4);
}
async function boundaryCheck() {
  clearDocumentResults(); controls();
  el('source').textContent = '资料标识：DOC-CLASSIFIED-009\n分类标记：涉密\n限制：禁止普通识别、脱敏与上传。\n正文：未提供。';
  el('boundary-result').textContent = '正在分别调用识别、脱敏和上传入口；每个请求都只传固定资料 ID，不传正文。';
  const results = [];
  const calls = [
    ['识别', 'a/documents/DOC-CLASSIFIED-009/identify', {}],
    ['脱敏', 'a/documents/DOC-CLASSIFIED-009/process/boundary-probe', {}],
    ['上传', 'a/documents/DOC-CLASSIFIED-009/upload', {}],
  ];
  for (const [label, path, body] of calls) {
    const {response, data} = await api(path, body);
    results.push(`${label}：HTTP ${response.status} / ${data.error?.code || data.authorization}`);
    if (response.status !== 403 || data.error?.code !== 'CONFIDENTIAL_BOUNDARY') throw new Error(`${label} 边界响应不符合预期`);
  }
  await refresh();
  const {data: state, response} = await api('a/state');
  if (!response.ok) throw new Error('无法核对处理计数');
  el('boundary-result').textContent = `${results.join('；')}。普通处理调用计数：识别 ${state.counters.identification}、脱敏 ${state.counters.deidentification}、上传 ${state.counters.upload}。涉密正文未进入普通运行链或审计。`;
  el('audit-detail').textContent = '涉密拒绝只写入安全错误请求标识；涉密正文未写入审计。';
  el('conclusion').textContent = '涉密示例只证明禁止边界；识别、脱敏和上传三个入口均在普通逻辑之前拒绝。';
  progress('三个涉密入口均已阻断，普通处理计数未因这些请求变化。', 4);
}
el('reset').onclick = () => task(reset);
el('identify').onclick = () => task(() => identify());
el('assistant').onclick = () => task(assistantReview);
el('correct').onclick = () => task(correctFinding);
el('preview').onclick = () => task(preview);
el('process').onclick = () => task(processRun);
el('boundary-check').onclick = () => task(boundaryCheck);
el('document-select').onchange = () => { clearDocumentResults(); controls(); };
el('replay').onclick = () => task(async () => {
  await reset(); await identify('PO-A-017'); await assistantReview();
  progress('自动演示已停在人工核对；请检查误报证据并点击“人工修正误报”。', 2);
});
task(async () => {
  const {response, data} = await api('health');
  if (!response.ok) throw new Error(`${data.error?.message || '本地服务不可用'} 请求标识：${data.error?.request_id || response.headers.get('X-Request-ID')}`);
  el('health').textContent = `本地服务正常 · ${data.model} · 无外部服务`;
  await refresh();
}).then(() => { if (!el('error').hidden) el('health').textContent = '本地服务不可用，请检查启动终端'; });
