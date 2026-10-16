const $ = (id) => document.getElementById(id);
const esc = (value) => String(value).replace(/[&<>"']/g, (char) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[char]);
let currentRun = null;
let logs = [];
let analysis = null;
let explanation = null;
let busy = false;

async function api(path, options = {}) {
  const response = await fetch(path, { headers: { "content-type": "application/json" }, ...options });
  const body = await response.json();
  if (!response.ok) throw new Error(body.error?.message || `本地服务返回 HTTP ${response.status}`);
  return body;
}

function setError(message = "") {
  $("error").textContent = message;
  $("error").hidden = !message;
}

function markSteps(phase) {
  const order = { none: 0, started: 1, analyzed: 2, explained: 3, reviewed: 4, briefed: 5 };
  const n = order[phase] || 0;
  for (let index = 1; index <= 5; index += 1) $("step" + index).classList.toggle("done", index <= n);
}

function enableControls() {
  const phase = currentRun?.phase;
  $("start").disabled = busy || Boolean(currentRun);
  $("analyze").disabled = busy || phase !== "started";
  $("explain").disabled = busy || phase !== "analyzed";
  $("review").disabled = busy || phase !== "explained";
  $("brief-button").disabled = busy || phase !== "reviewed";
  $("replay").disabled = busy;
  $("reset").disabled = busy;
}

function logLink(id) {
  return `<button class="evidence-link" data-log-id="${esc(id)}">${esc(id)}</button>`;
}

function renderLogs() {
  $("logs").innerHTML = logs.map((row) => `<tr id="${esc(row.id)}"><td>${logLink(row.id)}</td><td>${esc(row.time)}</td><td>${esc(row.account)}</td><td>${esc(row.source_ip)}</td><td>${esc(row.event)}</td><td>${esc(row.detail)}</td></tr>`).join("");
  $("time-basis").textContent = "合成日志 · " + ($("time-basis").dataset.basis || "");
}

function bindLogLinks(root = document) {
  root.querySelectorAll("[data-log-id]").forEach((button) => button.addEventListener("click", () => {
    const target = $(button.dataset.logId);
    target?.scrollIntoView({ behavior: "smooth", block: "center" });
    target?.classList.add("evidence-highlight");
    window.setTimeout(() => target?.classList.remove("evidence-highlight"), 1300);
  }));
}

function renderAnalysis() {
  const findings = analysis?.findings || [];
  $("findings").innerHTML = findings.length ? findings.map((item) => `<article class="finding"><strong>${esc(item.title)} · ${esc(item.account)}</strong><p>${esc(item.evidence_text)}</p><p>规则：${esc(item.rule_id)}　线索：${item.log_ids.map(logLink).join("、")}</p><small>候选线索；不等于事件定性。</small></article>`).join("") : "本样本未命中异常规则。";
  $("normal").textContent = `正常/未命中线索（仍需结合场景判断误报）：${analysis?.normal_log_ids?.join(", ") || "无"}\n${analysis?.scope || ""}\n${analysis?.time_basis || ""}`;
  const inferenceOption = explanation ? `<option value="${esc(explanation.inference_id)}">AI 推测：凭据泄露并通过 API 外传数据</option>` : "";
  $("finding").innerHTML = inferenceOption + findings.map((item) => `<option value="${esc(item.id)}">${esc(item.title)} · ${esc(item.account)}</option>`).join("");
  if (explanation) $("finding").value = explanation.inference_id;
  $("finding").disabled = !findings.length || currentRun?.phase !== "explained";
  renderEvidenceOptions();
  bindLogLinks($("findings"));
}

function renderEvidenceOptions() {
  const target = $("finding").value === explanation?.inference_id
    ? { log_ids: explanation.inference_evidence_ids }
    : analysis?.findings?.find((item) => item.id === $("finding").value);
  if (!target) {
    $("evidence-select").textContent = "本次运行没有可核查的规则线索。";
    return;
  }
  $("evidence-select").innerHTML = target.log_ids.map((id) => `<label class="check-row"><input type="checkbox" name="evidence" value="${esc(id)}" checked> ${logLink(id)}</label>`).join("");
  bindLogLinks($("evidence-select"));
}

function renderExplanation() {
  if (!explanation) return;
  $("explanation").innerHTML = `<p>${esc(explanation.label)} · ${esc(explanation.model)}</p><p><strong>风险解释：</strong>${esc(explanation.risk_explanation)}</p><blockquote><strong>需人工修正的推测：</strong>${esc(explanation.inference)}<br><small>线索依据（仅是相关日志，并不证明推测）：${(explanation.inference_evidence_ids || []).map(logLink).join("、") || "无"}</small></blockquote><p class="warning">${esc(explanation.uncertainty)}</p>`;
  bindLogLinks($("explanation"));
}

function renderBrief(brief) {
  const columns = ["已证实事实", "AI 推测", "待核查", "建议动作"];
  $("brief").hidden = false;
  $("brief").innerHTML = `<div class="brief-grid">${columns.map((heading) => `<article class="brief-column"><h3>${heading}</h3>${(brief[heading] || []).map((row) => `<p>${esc(row.text)}${row.status ? ` <span class="tag danger">${esc(row.status)}</span>` : ""}<br><small>证据：${(row.evidence_ids || []).map((id) => id.startsWith("LOG-") ? logLink(id) : `<span class="evidence-id">${esc(id)}</span>`).join("、") || "无"}</small></p>`).join("") || "<p>暂无。</p>"}</article>`).join("")}</div><p class="caption">简报 ${esc(brief.id)} · 运行 ${esc(brief.run_id)} · ${esc(brief.generated_at)} · JSON 可通过本地 API 获取</p>`;
  bindLogLinks($("brief"));
  $("download-brief").disabled = false;
}

function renderState(data) {
  $("audit").innerHTML = data.audits.length ? data.audits.map((item) => `<li><time>${esc(item.time)}</time> · ${esc(item.action)} / ${esc(item.result)} · 对象 ${esc(item.object_id)} · ${esc(item.actor_id)}（${esc(item.role)}）· request ${esc(item.request_id)} · ${esc(item.reason)}</li>`).join("") : "<li>暂无审计记录。</li>";
}

function setRun(run, progress) {
  currentRun = run;
  $("progress").textContent = progress;
  markSteps(run?.phase || "none");
  enableControls();
}

async function doStart() {
  currentRun = await api("/api/v1/d/runs", { method: "POST", body: "{}" });
  logs = currentRun.logs;
  renderLogs();
  $("progress").textContent = `运行 ${currentRun.id}：已汇总 ${logs.length} 条合成日志，可查看原始字段。`;
  await refreshState();
  setRun(currentRun, $("progress").textContent);
}

async function doAnalyze() {
  analysis = await api(`/api/v1/d/runs/${currentRun.id}/analyze`, { method: "POST", body: "{}" });
  currentRun.phase = "analyzed";
  renderAnalysis();
  await refreshState();
  setRun(currentRun, `确定性规则分析完成：${analysis.findings.length} 条候选线索，${analysis.normal_log_ids.length} 条未命中记录；进入离线模拟 AI 分析。`);
}

async function doExplain() {
  explanation = await api(`/api/v1/d/runs/${currentRun.id}/explain`, { method: "POST", body: "{}" });
  currentRun.phase = "explained";
  renderExplanation();
  renderAnalysis();
  await refreshState();
  setRun(currentRun, "辅助分析完成。请核对原始日志，确认、排除或标记待补证；推测不会自动进入事实。" );
}

async function doReview() {
  const evidence_ids = [...document.querySelectorAll('input[name="evidence"]:checked')].map((node) => node.value);
  const decision = document.querySelector('input[name="decision"]:checked')?.value;
  const finding_id = $("finding").value;
  const rationale = $("rationale").value;
  const result = await api(`/api/v1/d/runs/${currentRun.id}/review`, { method: "POST", body: JSON.stringify({ finding_id, decision, rationale, evidence_ids }) });
  currentRun.phase = "reviewed";
  currentRun.review = result;
  $("review-result").innerHTML = `<p><strong>${esc(result.reviewer.name)} · ${esc(result.decision)}</strong> · ${esc(result.rationale)} · 核查 ID ${esc(result.id)} · ${result.evidence_ids.map(logLink).join("、")}</p>`;
  bindLogLinks($("review-result"));
  await refreshState();
  setRun(currentRun, "人工核查已记录。生成四栏简报时，原始日志事实、AI 推测、待核查事项和建议动作会分开呈现。" );
}

async function doBrief() {
  const brief = await api(`/api/v1/d/runs/${currentRun.id}/brief`, { method: "POST", body: "{}" });
  currentRun.phase = "briefed";
  currentRun.brief = brief;
  renderBrief(brief);
  await refreshState();
  setRun(currentRun, "四栏简报已生成；建议动作只作为文字说明，不会执行封禁或生产变更。" );
}

async function refreshState() {
  renderState(await api("/api/v1/d/state"));
}

async function perform(action) {
  if (busy) return;
  busy = true;
  setError();
  enableControls();
  try { await action(); } catch (error) { setError(error.message); } finally { busy = false; enableControls(); }
}

async function resetDemo() {
  await api("/api/v1/d/reset", { method: "POST", body: "{}" });
  currentRun = null;
  analysis = null;
  explanation = null;
  $("analysis");
  $("findings").textContent = "尚未分析。";
  $("normal").textContent = "规则尚未运行。";
  $("explanation").textContent = "尚未分析。";
  $("review-result").textContent = "等待人工核查。";
  $("brief").hidden = true;
  $("brief").replaceChildren();
  $("download-brief").disabled = true;
  $("rationale").value = "";
  $("finding").replaceChildren();
  $("finding").disabled = true;
  $("evidence-select").textContent = "完成分析后载入日志。";
  $("progress").textContent = "D 演示已重置：运行、核查、简报和审计已清空，旧运行已失效。";
  markSteps("none");
  await refreshState();
  enableControls();
}

$("finding").addEventListener("change", renderEvidenceOptions);
$("start").addEventListener("click", () => perform(doStart));
$("analyze").addEventListener("click", () => perform(doAnalyze));
$("explain").addEventListener("click", () => perform(doExplain));
$("review").addEventListener("click", () => perform(doReview));
$("brief-button").addEventListener("click", () => perform(doBrief));
$("download-brief").addEventListener("click", () => perform(async () => {
  const data = await api(`/api/v1/d/state`);
  const brief = currentRun && data.runs[currentRun.id]?.brief;
  if (!brief) throw new Error("当前运行尚无可导出的四栏简报。");
  const url = URL.createObjectURL(new Blob([JSON.stringify(brief, null, 2)], { type: "application/json;charset=utf-8" }));
  const link = document.createElement("a"); link.href = url; link.download = `${brief.id}.json`; link.click(); URL.revokeObjectURL(url);
}));
$("reset").addEventListener("click", () => perform(resetDemo));
$("replay").addEventListener("click", () => perform(async () => { await resetDemo(); await doStart(); await doAnalyze(); await doExplain(); }));

api("/api/v1/health").then((health) => { $("health").textContent = `本地服务正常 · ${health.model} · 外部服务：${health.external_services ? "已连接" : "未连接"}`; }).catch((error) => { $("health").textContent = "本地服务不可用：" + error.message; });
api("/api/v1/d/logs").then((data) => { logs = data.items; $("time-basis").dataset.basis = data.time_basis; renderLogs(); }).catch((error) => setError(error.message));
refreshState().then(enableControls).catch((error) => setError(error.message));
enableControls();
