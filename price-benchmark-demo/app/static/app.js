const $ = (id) => document.getElementById(id);
const steps = ['正在取得市场数据', '正在识别商品口径', '正在统一计量单位', '正在检查数据是否可比较', '正在生成价格判断', '正在验证结果'];
let normalData = null;
let anomalyData = null;
let timer = null;
let runId = 0;

async function loadData() {
  const [normal, anomaly] = await Promise.all([fetch('/api/normal'), fetch('/api/anomaly')]);
  if (!normal.ok || !anomaly.ok) throw new Error('本地演示数据加载失败');
  normalData = await normal.json();
  anomalyData = await anomaly.json();
}

function showScene(id, badge) {
  ['intro', 'progress', 'normalResult', 'anomalyResult'].forEach((name) => $(name).classList.toggle('hidden', name !== id));
  $('sceneBadge').textContent = badge;
  $('controlMenu').classList.add('hidden');
  $('controlButton').setAttribute('aria-expanded', 'false');
}

function cancelRun() { runId += 1; if (timer) clearTimeout(timer); timer = null; }
function reset() { cancelRun(); showScene('intro', '等待执行'); }

function element(tag, className, textValue) {
  const el = document.createElement(tag);
  if (className) el.className = className;
  if (textValue !== undefined) el.textContent = textValue;
  return el;
}

function evidenceButton(item, isA = false) {
  const button = element('button', '', '查看依据 ↗');
  button.addEventListener('click', () => showEvidence(item, isA));
  return button;
}

function makeCard(item) {
  const card = element('article', 'item-card ' + item.status);
  const top = element('div', 'item-top');
  top.append(element('strong', '', item.name), element('span', '', item.source.replace('公开市场来源 ', '来源 ')));
  const detail = item.summary;
  const bottom = element('div', 'item-bottom');
  bottom.append(element('span', 'tag', item.tag), evidenceButton(item));
  card.append(top, element('div', 'judgment', item.judgment), element('div', 'item-detail', detail), bottom);
  return card;
}

function renderNormal() {
  const targets = { comparable: $('comparableList'), blocked: $('blockedList'), manual: $('manualList') };
  Object.values(targets).forEach((target) => target.replaceChildren());
  normalData.items.forEach((item) => targets[item.status].append(makeCard(item)));
}

function appendEvidenceLine(parent, label, value) {
  const line = element('div', 'evidence-line');
  line.append(element('label', '', label), element('p', '', value));
  parent.append(line);
}

function showEvidence(item, isA = false) {
  const body = $('evidenceBody');
  body.replaceChildren();
  const content = element('div', 'evidence-content');
  const title = element('h3', '', item.name);
  title.append(element('span', isA ? 'status-risk' : 'status-' + item.status, isA ? '看似完成' : item.judgment));
  content.append(title);
  if (isA) {
    appendEvidenceLine(content, '报告结论', item.judgment);
    appendEvidenceLine(content, '依据检查', item.evidence);
    appendEvidenceLine(content, '当前状态', '报告 A 已标记完成，但依据存在缺口。');
    content.append(element('div', 'evidence-warning', '演示中的“不受控执行”结果，仅用于说明风险。'));
  } else {
    appendEvidenceLine(content, '市场原始数据', item.market);
    appendEvidenceLine(content, '采购原始数据', item.purchase);
    appendEvidenceLine(content, '单位换算', item.conversion);
    appendEvidenceLine(content, '口径与条件', item.conditions);
    appendEvidenceLine(content, '数据日期', item.date);
    appendEvidenceLine(content, '当前状态', item.state);
    appendEvidenceLine(content, '来源', item.source);
  }
  body.append(content);
  $('evidenceDialog').showModal();
}

function renderAnomaly() {
  const metrics = anomalyData.metrics;
  $('aPercent').textContent = metrics.a_percent + '%';
  $('bCompleted').textContent = metrics.completed;
  $('bStopped').textContent = metrics.stopped + ' 项已停止';
  $('compareAPercent').textContent = metrics.a_percent + '%';
  $('compareBPercent').textContent = metrics.b_percent + '%';
  $('anomalyEvents').replaceChildren(...anomalyData.events.map((text) => element('span', '', text)));
  $('reportAList').replaceChildren(...anomalyData.report_a.map((item) => {
    const row = element('div', 'report-row danger');
    row.append(element('div', 'row-name', item.name), element('div', 'row-judgment', item.judgment),
      element('div', 'a-ready', '✓ 结论已生成'), element('div', 'a-rule'),
      element('p', '', '已完成价格对标'), evidenceButton(item, true));
    return row;
  }));
  $('reportBList').replaceChildren(...anomalyData.report_b.map((item) => {
    const row = element('div', 'report-row ' + (item.status === 'stopped' ? 'stopped' : ''));
    row.append(element('div', 'row-name', item.name), element('div', 'row-judgment', item.judgment));
    if (item.source_notice) row.append(element('div', 'source-notice', item.source_notice));
    row.append(element('p', '', item.status === 'stopped' ? item.conditions : item.state));
    if (item.escalation) row.append(element('div', 'escalation', '等待：' + item.escalation));
    row.append(evidenceButton(item));
    return row;
  }));
}

function switchView(view) {
  ['reportA', 'reportB', 'comparison'].forEach((id) => $(id).classList.toggle('hidden', id !== ({ a: 'reportA', b: 'reportB', compare: 'comparison' })[view]));
  document.querySelectorAll('[data-view]').forEach((button) => button.classList.toggle('active', button.dataset.view === view));
  $('sceneBadge').textContent = { a: '报告 A · 看似完成', b: '报告 B · 受控执行', compare: 'A/B 对比' }[view];
}

function toNormalResult() { cancelRun(); renderNormal(); showScene('normalResult', '任务完成'); }
function toComparison() { cancelRun(); renderAnomaly(); showScene('anomalyResult', '异常已处理'); switchView('compare'); }

function startRun(mode) {
  cancelRun();
  const thisRun = runId;
  showScene('progress', mode === 'normal' ? '正在执行' : '异常场景执行中');
  $('eventBox').classList.toggle('hidden', mode === 'normal');
  $('events').replaceChildren();
  $('steps').replaceChildren(...steps.map((step, index) => element('div', 'step', String(index + 1).padStart(2, '0') + '  ' + step)));
  let position = 0;
  function advance() {
    if (thisRun !== runId) return;
    if (position >= steps.length) {
      if (mode === 'normal') toNormalResult();
      else { renderAnomaly(); showScene('anomalyResult', '异常已处理'); switchView('a'); }
      return;
    }
    $('progressTitle').textContent = steps[position];
    $('progressCount').innerHTML = String(position + 1).padStart(2, '0') + ' <small>/ 06</small>';
    $('progressFill').style.width = ((position + 1) / steps.length * 100) + '%';
    document.querySelectorAll('.step').forEach((node, index) => node.className = 'step ' + (index < position ? 'done' : index === position ? 'active' : ''));
    if (mode === 'anomaly' && position >= 1) {
      const visible = Math.min(position, anomalyData.events.length);
      $('events').replaceChildren(...anomalyData.events.slice(0, visible).map((event) => element('div', '', event)));
    }
    position += 1;
    timer = setTimeout(advance, 1150);
  }
  advance();
}

function action(name) {
  if (name === 'reset') reset();
  if (name === 'normal') startRun('normal');
  if (name === 'anomaly') startRun('anomaly');
  if (name === 'normal-result') toNormalResult();
  if (name === 'compare') toComparison();
}

$('controlButton').addEventListener('click', () => {
  const open = $('controlMenu').classList.toggle('hidden') === false;
  $('controlButton').setAttribute('aria-expanded', String(open));
});
document.addEventListener('click', (event) => {
  if ($('controlMenu').contains(event.target) || $('controlButton').contains(event.target)) return;
  $('controlMenu').classList.add('hidden');
  $('controlButton').setAttribute('aria-expanded', 'false');
});
document.querySelectorAll('[data-action]').forEach((button) => button.addEventListener('click', () => action(button.dataset.action)));
document.querySelectorAll('[data-view]').forEach((button) => button.addEventListener('click', () => switchView(button.dataset.view)));
$('startButton').addEventListener('click', () => startRun('normal'));
$('closeDialog').addEventListener('click', () => $('evidenceDialog').close());
document.addEventListener('keydown', (event) => {
  if (event.metaKey || event.ctrlKey || event.altKey || event.shiftKey) return;
  if (event.target instanceof HTMLElement && ['INPUT', 'TEXTAREA', 'SELECT'].includes(event.target.tagName)) return;
  if ($('evidenceDialog').open) return;
  if (event.key.toLowerCase() === 'r') reset();
  if (event.key === '1') startRun('normal');
  if (event.key === '2') startRun('anomaly');
});
loadData().catch((error) => { $('intro').innerHTML = '<div class="load-error">' + error.message + '。请检查本地服务后刷新页面。</div>'; });
