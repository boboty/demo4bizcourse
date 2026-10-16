"""Demo D：合成登录/API 日志的规则筛查与人工核查。"""

import copy
import threading
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

from fastapi import APIRouter, Request
from fastapi.responses import FileResponse
from pydantic import BaseModel, ConfigDict, Field

from .errors import ApiError

router = APIRouter()
LOCK = threading.RLock()
STATIC = Path(__file__).parent / "static"
ACTOR = {"id": "sec-reviewer-008", "role": "security_log_reviewer", "name": "安全日志核查员（固定演示身份）"}
TIME_BASIS = "以下时间为合成数据中的 Asia/Shanghai 本地墙钟时间（UTC+08:00）；不代表真实采集时间。"
LOGS = [
    {"id": "LOG-D-001", "time": "2026-09-18 08:10:04", "account": "svc-report-02", "source_ip": "198.51.100.18", "event": "login_success", "detail": "报表服务例行登录", "source": "合成身份认证日志"},
    {"id": "LOG-D-002", "time": "2026-09-18 08:10:11", "account": "svc-report-02", "source_ip": "198.51.100.18", "event": "api_read", "detail": "读取报表摘要接口", "source": "合成 API 网关日志"},
    {"id": "LOG-D-003", "time": "2026-09-18 08:11:02", "account": "svc-report-02", "source_ip": "198.51.100.18", "event": "login_success", "detail": "自动重试后登录成功", "source": "合成身份认证日志"},
    {"id": "LOG-D-004", "time": "2026-09-18 09:01:20", "account": "user-demo-14", "source_ip": "203.0.113.24", "event": "login_success", "detail": "正常工作时段登录", "source": "合成身份认证日志"},
    {"id": "LOG-D-005", "time": "2026-09-18 09:02:04", "account": "user-demo-14", "source_ip": "203.0.113.24", "event": "api_read", "detail": "读取个人工作台", "source": "合成 API 网关日志"},
    {"id": "LOG-D-006", "time": "2026-09-18 23:47:10", "account": "user-demo-22", "source_ip": "203.0.113.77", "event": "login_success", "detail": "非工作时段登录", "source": "合成身份认证日志"},
    {"id": "LOG-D-007", "time": "2026-09-18 23:48:01", "account": "user-demo-22", "source_ip": "203.0.113.77", "event": "api_read", "detail": "读取资料目录接口", "source": "合成 API 网关日志"},
    {"id": "LOG-D-008", "time": "2026-09-18 10:22:11", "account": "user-demo-31", "source_ip": "192.0.2.45", "event": "permission_denied", "detail": "尝试读取无权访问的目录", "source": "合成授权审计日志"},
    {"id": "LOG-D-009", "time": "2026-09-18 10:22:19", "account": "user-demo-31", "source_ip": "192.0.2.45", "event": "permission_denied", "detail": "同一会话再次访问受限目录", "source": "合成授权审计日志"},
    {"id": "LOG-D-010", "time": "2026-09-18 10:22:27", "account": "user-demo-31", "source_ip": "192.0.2.45", "event": "permission_denied", "detail": "重复请求仍被拒绝", "source": "合成授权审计日志"},
]
RULES = [
    {"id": "RULE-D-AUTH-RATE", "label": "5 分钟内同账号 2 次及以上成功登录", "kind": "login_success", "threshold": 2},
    {"id": "RULE-D-OFF-HOURS", "label": "非工作时段成功登录", "kind": "off_hours", "threshold": 1},
    {"id": "RULE-D-REPEATED-DENY", "label": "连续权限拒绝", "kind": "permission_denied", "threshold": 3},
]
state: dict = {}


def reset_state() -> None:
    state.clear()
    state.update(epoch=uuid.uuid4().hex[:10], runs={}, audits=[])


reset_state()


class ReviewInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    finding_id: str = Field(min_length=1, max_length=80)
    decision: Literal["确认", "排除", "待补证"]
    rationale: str = Field(max_length=1000)
    evidence_ids: list[str] = Field(min_length=1)


class RunInput(BaseModel):
    model_config = ConfigDict(extra="forbid")


def add_audit(request: Request, run: dict, action: str, result: str, object_id: str, reason: str) -> dict:
    item = {"id": uuid.uuid4().hex[:12], "time": datetime.now(UTC).isoformat(), "run_id": run["id"],
            "request_id": request.state.request_id, "actor_id": ACTOR["id"], "role": ACTOR["role"],
            "action": action, "result": result, "object_id": object_id, "reason": reason}
    state["audits"].append(item)
    run["audit_ids"].append(item["id"])
    return item


def get_run(run_id: str) -> dict:
    run = state["runs"].get(run_id)
    if run is None or run["epoch"] != state["epoch"]:
        raise ApiError(404, "RUN_NOT_FOUND", "运行不存在或已重置，请重新开始本课。")
    return run


def analyze_logs(logs: list[dict]) -> dict:
    grouped: dict[str, list[dict]] = {}
    for log in logs:
        grouped.setdefault(log["account"], []).append(log)
    findings = []
    for account, entries in grouped.items():
        login_entries = [row for row in entries if row["event"] == "login_success"]
        frequent_logins = []
        for row in login_entries:
            event_time = datetime.strptime(row["time"], "%Y-%m-%d %H:%M:%S")
            window = [item for item in login_entries if 0 <= (event_time - datetime.strptime(item["time"], "%Y-%m-%d %H:%M:%S")).total_seconds() <= 300]
            if len(window) >= 2:
                frequent_logins = window
                break
        if frequent_logins:
            findings.append({"id": "FIND-D-RATE-" + account, "rule_id": RULES[0]["id"], "title": RULES[0]["label"], "account": account,
                             "log_ids": [row["id"] for row in frequent_logins], "evidence_text": f"该账号在 5 分钟内出现 {len(frequent_logins)} 次成功登录。", "severity": "需核查"})
        off_hours = [row for row in login_entries if int(row["time"][11:13]) < 7 or int(row["time"][11:13]) >= 22]
        if off_hours:
            findings.append({"id": "FIND-D-HOURS-" + account, "rule_id": RULES[1]["id"], "title": RULES[1]["label"], "account": account,
                             "log_ids": [row["id"] for row in off_hours], "evidence_text": "日志时间落在 07:00–21:59 之外。", "severity": "需核查"})
        denied = [row for row in entries if row["event"] == "permission_denied"]
        if len(denied) >= 3:
            findings.append({"id": "FIND-D-DENY-" + account, "rule_id": RULES[2]["id"], "title": RULES[2]["label"], "account": account,
                             "log_ids": [row["id"] for row in denied], "evidence_text": f"同账号出现 {len(denied)} 条权限拒绝记录。", "severity": "需核查"})
    return {"ruleset": "D-RULESET-1", "findings": findings, "normal_log_ids": [row["id"] for row in logs if not any(row["id"] in item["log_ids"] for item in findings)],
            "scope": "仅统计当前固定合成样本内可观察到的事件；未命中日志可作正常或潜在误报参照，不判断账号归属、入侵来源或数据是否外传。", "time_basis": TIME_BASIS}


@router.get("/api/v1/d/state")
def d_state():
    with LOCK:
        return {"actor": copy.deepcopy(ACTOR), "epoch": state["epoch"], "runs": copy.deepcopy(state["runs"]), "audits": copy.deepcopy(state["audits"])}


@router.get("/api/v1/d/logs")
def d_logs():
    return {"items": copy.deepcopy(LOGS), "time_basis": TIME_BASIS,
            "notice": "小规模合成课堂样本；只展示本地日志字段，未连接真实账号、平台或敏感数据。"}


@router.post("/api/v1/d/reset")
def d_reset():
    with LOCK:
        reset_state()
        return d_state()


@router.post("/api/v1/d/runs", status_code=201)
def d_create_run(data: RunInput, request: Request):
    with LOCK:
        run = {"id": uuid.uuid4().hex[:12], "epoch": state["epoch"], "actor": copy.deepcopy(ACTOR), "phase": "started",
               "logs": copy.deepcopy(LOGS), "analysis": None, "explanation": None, "review": None, "brief": None, "audit_ids": []}
        state["runs"][run["id"]] = run
        add_audit(request, run, "create_run", "CREATED", "synthetic_log_batch", "创建 D 独立合成日志分析运行。")
        return copy.deepcopy(run)


@router.post("/api/v1/d/runs/{run_id}/analyze")
def d_analyze(run_id: str, request: Request):
    with LOCK:
        run = get_run(run_id)
        if run["phase"] != "started":
            raise ApiError(409, "INVALID_STEP", "请从原始日志开始；此阶段已完成。")
        run["analysis"] = analyze_logs(run["logs"])
        run["phase"] = "analyzed"
        add_audit(request, run, "deterministic_rule_analysis", "COMPLETE", "rule_findings", f"命中 {len(run['analysis']['findings'])} 个候选线索；需人工核对。")
        return copy.deepcopy(run["analysis"])


@router.post("/api/v1/d/runs/{run_id}/explain")
def d_explain(run_id: str, request: Request):
    with LOCK:
        run = get_run(run_id)
        if run["phase"] != "analyzed":
            raise ApiError(409, "INVALID_STEP", "请先运行确定性规则分析。")
        lead = next((item for item in run["analysis"]["findings"] if item["account"] == "user-demo-22"), None)
        run["explanation"] = {"model": "离线确定性模拟分析器（非真实大模型）", "label": "AI 辅助分析 · 不能代替事实核查",
            "candidate_events": [{"id": item["id"], "source_finding_id": item["id"], "summary": item["title"], "evidence_ids": item["log_ids"]} for item in run["analysis"]["findings"]],
            "risk_explanation": "短时重复登录、非工作时段登录或连续权限拒绝值得结合业务背景复核。", "inference_id": "INFER-D-CREDENTIAL-EXFIL-01",
            "inference": f"看似合理但尚未被证实：{lead['account'] if lead else '某账号'} 可能凭据泄露，并已通过 API 外传数据。", "inference_evidence_ids": lead["log_ids"] if lead else [],
            "uncertainty": "这些记录没有提供凭据来源、响应字节数或网络出口数据；不能据此认定账号已失陷或数据已泄露。请在人工作业中修正或标记待补证。", "final_decision": None}
        run["phase"] = "explained"
        add_audit(request, run, "offline_assistant_analysis", "COMPLETE", "candidate_events", "生成离线风险解释；推测仍待人工核对。")
        return copy.deepcopy(run["explanation"])


@router.post("/api/v1/d/runs/{run_id}/review")
def d_review(run_id: str, data: ReviewInput, request: Request):
    with LOCK:
        run = get_run(run_id)
        if run["phase"] != "explained":
            raise ApiError(409, "INVALID_STEP", "必须先完成日志规则分析和离线辅助分析，再进行人工核查。")
        if not data.rationale.strip():
            raise ApiError(422, "RATIONALE_REQUIRED", "人工核查必须填写理由。")
        targets = {item["id"]: {"title": item["title"], "evidence_ids": item["log_ids"]} for item in run["analysis"]["findings"]}
        inference_id = run["explanation"]["inference_id"]
        targets[inference_id] = {"title": "AI 推测：账号凭据泄露并通过 API 外传数据", "evidence_ids": run["explanation"]["inference_evidence_ids"]}
        target = targets.get(data.finding_id)
        if target is None:
            raise ApiError(404, "FINDING_NOT_FOUND", "线索或 AI 推测不存在，或不属于当前运行。")
        known_ids = {row["id"] for row in run["logs"]}
        if len(set(data.evidence_ids)) != len(data.evidence_ids) or not set(data.evidence_ids) <= known_ids:
            raise ApiError(422, "EVIDENCE_INVALID", "只能引用当前运行中的原始日志 ID，且不可重复。")
        if not set(data.evidence_ids) & set(target["evidence_ids"]):
            raise ApiError(422, "EVIDENCE_NOT_RELEVANT", "至少引用一条直接支持本条线索的原始日志。")
        review = {"id": "REVIEW-D-" + uuid.uuid4().hex[:8], "finding_id": data.finding_id, "finding_title": target["title"], "decision": data.decision,
                  "rationale": data.rationale.strip(), "evidence_ids": list(data.evidence_ids), "reviewer": copy.deepcopy(ACTOR),
                  "time": datetime.now(UTC).isoformat(), "request_id": request.state.request_id}
        run["review"] = review
        run["phase"] = "reviewed"
        add_audit(request, run, "human_log_review", "RECORDED", data.finding_id, f"固定可信演示身份记录人工核查：{data.decision}。")
        return copy.deepcopy(review)


@router.post("/api/v1/d/runs/{run_id}/brief")
def d_brief(run_id: str, request: Request):
    with LOCK:
        run = get_run(run_id)
        if run["phase"] != "reviewed":
            raise ApiError(409, "INVALID_STEP", "请先提交人工核查结果，再生成四栏简报。")
        review = run["review"]
        item = next((x for x in run["analysis"]["findings"] if x["id"] == review["finding_id"]), None)
        brief = {"id": "BRIEF-D-" + uuid.uuid4().hex[:8], "run_id": run["id"], "generated_at": datetime.now(UTC).isoformat(),
            "已证实事实": ([{"text": item["evidence_text"], "evidence_ids": item["log_ids"]}] if item else []) +
                         [{"text": f"人工核查记录：对“{review['finding_title']}”标记为“{review['decision']}”。该处置标签不代表账号失陷或数据外传已经证实。理由：{review['rationale']}", "evidence_ids": [review["id"], *review["evidence_ids"]]}],
            "AI 推测": [{"text": run["explanation"]["inference"], "evidence_ids": run["explanation"]["inference_evidence_ids"], "status": "人工核查后排除" if review["finding_id"] == run["explanation"]["inference_id"] and review["decision"] == "排除" else "待补证" if review["finding_id"] == run["explanation"]["inference_id"] and review["decision"] == "待补证" else "仍未证实"}],
            "待核查": [{"text": "凭据来源、响应字节数及网络出口记录尚不在本示例数据内；原始样本不能证明账号失陷或数据外传。", "evidence_ids": [review["id"], *run["explanation"]["inference_evidence_ids"]]}],
            "建议动作": [{"text": "按组织流程核对原始认证、API 响应与网络出口日志；本课堂不执行封禁、隔离或生产变更。", "evidence_ids": [review["id"], *review["evidence_ids"]]}]}
        run["brief"] = brief
        run["phase"] = "briefed"
        add_audit(request, run, "generate_four_section_brief", "COMPLETE", brief["id"], "生成本地课堂四栏简报；建议内容为文本，不调用生产工具。")
        return copy.deepcopy(brief)


@router.get("/demo/d")
def d_page():
    return FileResponse(STATIC / "demo-d.html")
