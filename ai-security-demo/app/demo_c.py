"""Demo C：企业 AI 调用合规审计与人工认定。"""

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
ACTOR = {"id": "audit-024", "role": "ai_compliance_reviewer", "name": "合规审计员（固定演示身份）"}
TOOL_WHITELIST = {
    "id": "LIST-AI-TOOL-01",
    "version": "1.0",
    "tools": {"customer-summary": "集团客服摘要工具", "research-search": "集团研发检索工具"},
    "text": "某产业集团 AI 工具准入白名单 LIST-AI-TOOL-01 · 版本 1.0\n本示例仅准入 customer-summary（集团客服摘要工具）和 research-search（集团研发检索工具）。未列入本清单的工具不得用于集团业务数据；新增工具须完成安全评估与审批后更新清单。",
}
WHITELIST_EVIDENCE = {
    "id": "EVC-C-WHITELIST-01",
    "title": "AI 工具准入白名单 · LIST-AI-TOOL-01 v1.0",
    "text": TOOL_WHITELIST["text"],
}
CASES = {
    "C-CASE-101": {
        "title": "客服摘要 · 常规合规",
        "log": {"id": "LOG-C-101", "time": "2026-09-18 09:10", "system": "集团客服助手", "model": "集团内网摘要模型", "provider": "集团内网", "tool": "customer-summary", "access_method": "approved_gateway", "caller": "svc-customer-01", "data_class": "一般业务信息", "purpose": "生成服务摘要", "approval_id": "APP-C-101", "retention_days": 7, "masking": {"id": "MASK-C-101", "mode": "字段脱敏", "fields": ["联系方式"]}, "payload": "虚构工单：设备安装时间调整为周五。"},
        "policy": {"id": "POL-AI-01", "text": "一般业务信息可在集团批准的内网模型中用于明确业务目的；仅保留必要期限并登记审批。"},
        "evidence": [
            {"id": "EVC-C-101-LOG", "title": "平台调用日志与脱敏元数据", "text": "LOG-C-101：集团内网摘要模型；工具 customer-summary；approved_gateway；一般业务信息；脱敏元数据 MASK-C-101：已遮盖联系方式；用途为生成服务摘要；审批 APP-C-101；保留 7 天。"},
            {"id": "EVC-C-101-APP", "title": "审批登记摘录", "text": "APP-C-101：客服摘要场景获准使用集团内网模型。"},
        ],
    },
    "C-CASE-102": {
        "title": "采购纪要 · 违规线索",
        "log": {"id": "LOG-C-102", "time": "2026-09-18 10:42", "system": "采购助手试验环境", "model": "CloudText-4", "provider": "外部云服务商", "tool": "browser-shell", "access_method": "direct_api", "caller": "user-demo-102", "data_class": "商业敏感信息", "purpose": "整理供应商谈判纪要", "approval_id": "", "retention_days": 90, "masking": {"id": "MASK-C-102", "mode": "未执行", "fields": []}, "payload": "虚构纪要：恒川设备报价 3200 元/台，返利条件为 8%。"},
        "policy": {"id": "POL-AI-02", "text": "商业敏感信息不得发送至未经批准的外部模型；调用须有专项审批，外部留存不得超过 30 天。"},
        "evidence": [
            {"id": "EVC-C-102-LOG", "title": "平台调用日志与脱敏元数据", "text": "LOG-C-102：CloudText-4；工具 browser-shell；direct_api；外部云服务商；商业敏感信息；脱敏元数据 MASK-C-102：未执行；未登记审批；保留 90 天。"},
            {"id": "EVC-C-102-POL", "title": "制度条文 POL-AI-02", "text": "商业敏感信息不得发送至未经批准的外部模型，须有专项审批，外部留存不超过 30 天。"},
        ],
    },
    "C-CASE-103": {
        "title": "研发问答 · 证据不足",
        "log": {"id": "LOG-C-103", "time": "2026-09-18 11:05", "system": "研发知识助手", "model": "集团内网问答模型", "provider": "集团内网", "tool": "research-search", "access_method": "approved_gateway", "caller": "svc-research-03", "data_class": "内部资料（细分未知）", "purpose": "", "approval_id": "APP-C-103", "retention_days": None, "masking": None, "payload": "虚构记录：问答内容与保留期限字段未完整采集。"},
        "policy": {"id": "POL-AI-03", "text": "调用必须能够核验资料类别、业务目的、审批依据和留存期限；关键字段缺失时先补证，不得推定违规或合规。"},
        "evidence": [
            {"id": "EVC-C-103-LOG", "title": "不完整平台调用日志与脱敏元数据", "text": "LOG-C-103：集团内网问答模型；工具 research-search；approved_gateway；资料细分类别、用途、脱敏元数据和留存期限字段缺失。"},
            {"id": "EVC-C-103-POL", "title": "制度条文 POL-AI-03", "text": "关键字段缺失时先补证，不得推定违规或合规。"},
        ],
    },
}
RULES = [
    {"id": "RULE-C-TOOL-ALLOWLIST", "text": "调用工具不在集团准入白名单", "when": lambda log: log["tool"] not in TOOL_WHITELIST["tools"]},
    {"id": "RULE-C-SENSITIVE-INPUT", "text": "输入资料为敏感或类别尚未核清，需检查脱敏调用元数据", "when": lambda log: log["data_class"] != "一般业务信息"},
    {"id": "RULE-C-MASKING-METADATA", "text": "敏感输入缺少已执行的脱敏元数据", "when": lambda log: log["data_class"] != "一般业务信息" and (not log["masking"] or log["masking"]["mode"] != "字段脱敏")},
    {"id": "RULE-C-ACCESS-METHOD", "text": "访问方式绕过批准的 AI 网关", "when": lambda log: log["access_method"] != "approved_gateway"},
    {"id": "RULE-C-EXT-SENSITIVE", "text": "敏感信息流向未批准的外部模型", "when": lambda log: log["data_class"] == "商业敏感信息" and log["provider"] != "集团内网"},
    {"id": "RULE-C-APPROVAL", "text": "调用日志未关联审批编号", "when": lambda log: not log["approval_id"]},
    {"id": "RULE-C-RETENTION", "text": "留存期限超过制度上限 30 天", "when": lambda log: isinstance(log["retention_days"], int) and log["retention_days"] > 30},
]
state: dict = {}


def reset_state() -> None:
    state.clear()
    state.update(epoch=uuid.uuid4().hex[:10], runs={}, audits=[])


reset_state()


class RunInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    case_id: str


class EvidenceInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    evidence_ids: list[str] = Field(min_length=1)


class ReviewInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    decision: Literal["违规", "不违规", "证据不足"]
    rationale: str = Field(min_length=1, max_length=1000)
    evidence_ids: list[str] = Field(min_length=1)


def audit(request: Request, run: dict, action: str, result: str, reason: str, object_id: str) -> dict:
    entry = {"id": uuid.uuid4().hex[:12], "time": datetime.now(UTC).isoformat(), "run_id": run["id"],
             "request_id": request.state.request_id, "actor_id": ACTOR["id"], "role": ACTOR["role"],
             "object_id": object_id, "action": action, "result": result, "reason": reason}
    state["audits"].append(entry)
    run["audit_ids"].append(entry["id"])
    return entry


def get_run(run_id: str) -> dict:
    run = state["runs"].get(run_id)
    if run is None or run["epoch"] != state["epoch"]:
        raise ApiError(404, "RUN_NOT_FOUND", "运行不存在或已重置，请重新开始本课。")
    return run


def case_public(case_id: str, case: dict) -> dict:
    evidence = copy.deepcopy(case["evidence"])
    evidence.append(copy.deepcopy(WHITELIST_EVIDENCE))
    return {"id": case_id, "title": case["title"], "log": copy.deepcopy(case["log"]),
            "policy": copy.deepcopy(case["policy"]), "evidence": evidence}


@router.get("/api/v1/c/state")
def c_state():
    with LOCK:
        return {"actor": copy.deepcopy(ACTOR), "epoch": state["epoch"], "runs": copy.deepcopy(state["runs"]),
                "audits": copy.deepcopy(state["audits"])}


@router.get("/api/v1/c/cases")
def cases():
    return {"items": [case_public(key, value) for key, value in CASES.items()],
            "simulation": "固定虚构日志和制度摘录；不连接外部 AI 或业务系统。"}


@router.post("/api/v1/c/reset")
def c_reset():
    with LOCK:
        reset_state()
        return c_state()


@router.post("/api/v1/c/runs", status_code=201)
def create_run(data: RunInput, request: Request):
    with LOCK:
        case = CASES.get(data.case_id)
        if case is None:
            raise ApiError(404, "CASE_NOT_FOUND", "演示案例不存在。")
        run = {"id": uuid.uuid4().hex[:12], "epoch": state["epoch"], "case_id": data.case_id,
               "case": case_public(data.case_id, case), "actor": copy.deepcopy(ACTOR), "phase": "started",
               "analysis": None, "explanation": None, "evidence_check": None, "review": None, "audit_ids": []}
        state["runs"][run["id"]] = run
        audit(request, run, "start", "CREATED", "创建独立 C 课运行。", data.case_id)
        return copy.deepcopy(run)


@router.post("/api/v1/c/runs/{run_id}/analyze")
def analyze(run_id: str, request: Request):
    with LOCK:
        run = get_run(run_id)
        if run["phase"] != "started":
            raise ApiError(409, "INVALID_STEP", "该运行已完成规则分析；请按当前阶段继续。")
        log = run["case"]["log"]
        source_evidence_ids = [item["id"] for item in run["case"]["evidence"]]
        hits = [{"rule_id": rule["id"], "text": rule["text"], "source_evidence_ids": source_evidence_ids,
                 "evidence": {"log_id": log["id"], "data_class": log["data_class"], "tool": log["tool"],
                              "access_method": log["access_method"], "provider": log["provider"],
                              "masking": copy.deepcopy(log["masking"]), "approval_id": log["approval_id"],
                              "retention_days": log["retention_days"],
                              "whitelist_id": TOOL_WHITELIST["id"] if rule["id"] == "RULE-C-TOOL-ALLOWLIST" else None}}
                for rule in RULES if rule["when"](log)]
        missing = [key for key in ("purpose", "retention_days") if log[key] is None or log[key] == ""]
        run["analysis"] = {"ruleset": "C-RULESET-1", "hits": hits, "missing_fields": missing,
                           "status": "evidence_needed" if missing else "signal" if hits else "no_hit",
                           "source_log_id": log["id"], "policy_id": run["case"]["policy"]["id"]}
        run["phase"] = "analyzed"
        audit(request, run, "deterministic_rule_analysis", "COMPLETE", f"命中 {len(hits)} 条规则；待人工结合原文核查。", log["id"])
        return copy.deepcopy(run["analysis"])


@router.post("/api/v1/c/runs/{run_id}/explain")
def explain(run_id: str, request: Request):
    with LOCK:
        run = get_run(run_id)
        if run["phase"] != "analyzed":
            raise ApiError(409, "INVALID_STEP", "请先完成确定性规则分析。")
        analysis = run["analysis"]
        run["explanation"] = {"model": "离线确定性模拟解释器（非真实 AI）", "label": "模拟 AI 辅助解释 · 仅供参考",
                              "event_id": run["case"]["log"]["id"], "policy_clause": {"id": run["case"]["policy"]["id"], "text": run["case"]["policy"]["text"]},
                              "evidence_links": [item["id"] for item in run["case"]["evidence"]],
                              "facts": [hit["text"] for hit in analysis["hits"]],
                              "inference": "日志与制度字段的规则比对提示了需要人工关注的风险线索。" if analysis["hits"] else "当前规则未命中可确认的违规线索。",
                              "uncertainty": "潜在敏感输入和脱敏状态尚不能据此确认违规；请核对原始调用元数据。" if run["case_id"] == "C-CASE-103" else "关键日志字段缺失，无法据此判断合规或违规。" if analysis["missing_fields"] else "规则命中仅是筛查线索，需核对原始日志和制度原文。",
                              "pending_verification": ["核实资料细分类别与业务用途", "核实脱敏执行和留存元数据" ] if run["case_id"] == "C-CASE-103" else ["核对平台日志、审批和制度原文"],
                              "final_decision": None}
        run["phase"] = "explained"
        audit(request, run, "offline_assistant_explanation", "COMPLETE", "生成辅助解释；解释器无最终认定写入权限。", run["case_id"])
        return copy.deepcopy(run["explanation"])


@router.get("/api/v1/c/runs/{run_id}/candidate-questions")
def candidate_questions(run_id: str):
    with LOCK:
        run = get_run(run_id)
        if run["analysis"] is None:
            raise ApiError(409, "INVALID_STEP", "请先完成规则分析，再生成候选问题清单。")
        analysis = run["analysis"]
        questions = [{"question_id": f"Q-{hit['rule_id']}", "question": f"核实：{hit['text']}？",
                      "status": "待核实", "event_id": run["case"]["log"]["id"],
                      "policy_id": run["case"]["policy"]["id"], "evidence_links": hit["source_evidence_ids"]}
                     for hit in analysis["hits"]]
        questions.extend({"question_id": f"Q-MISSING-{field.upper()}", "question": f"补充原始日志字段：{field}。",
                          "status": "待补证", "event_id": run["case"]["log"]["id"],
                          "policy_id": run["case"]["policy"]["id"], "evidence_links": [item["id"] for item in run["case"]["evidence"]]}
                         for field in analysis["missing_fields"])
        return {"run_id": run["id"], "items": questions}


@router.post("/api/v1/c/runs/{run_id}/evidence-check")
def check_evidence(run_id: str, data: EvidenceInput, request: Request):
    with LOCK:
        run = get_run(run_id)
        if run["phase"] != "explained":
            raise ApiError(409, "INVALID_STEP", "请先查看离线辅助解释，再核对原始证据。")
        evidence = run["case"]["evidence"]
        known = {item["id"] for item in evidence}
        if len(set(data.evidence_ids)) != len(data.evidence_ids) or not set(data.evidence_ids) <= known:
            raise ApiError(422, "EVIDENCE_INVALID", "只能核对当前运行提供的原始证据标识，且不可重复。")
        checked = [item for item in evidence if item["id"] in data.evidence_ids]
        required = {item["id"] for item in evidence}
        run["evidence_check"] = {"checked_ids": list(data.evidence_ids), "checked": copy.deepcopy(checked),
                                  "complete": len(checked) == len(evidence), "required_sources": sorted(required),
                                  "checked_at": datetime.now(UTC).isoformat()}
        run["phase"] = "evidence_checked"
        audit(request, run, "verify_original_evidence", "COMPLETE", f"人工已打开并核对 {len(checked)} 项原始证据。", run["case_id"])
        return copy.deepcopy(run["evidence_check"])


@router.post("/api/v1/c/runs/{run_id}/review")
def review(run_id: str, data: ReviewInput, request: Request):
    with LOCK:
        run = get_run(run_id)
        if run["phase"] != "evidence_checked":
            raise ApiError(409, "INVALID_STEP", "必须先核对原始证据，再进行人工认定。")
        checked = run["evidence_check"]["checked_ids"]
        if not data.rationale.strip():
            raise ApiError(422, "RATIONALE_REQUIRED", "人工认定必须填写具体理由。")
        if set(data.evidence_ids) != set(checked) or len(data.evidence_ids) != len(checked):
            raise ApiError(422, "EVIDENCE_NOT_CHECKED", "认定只能引用本运行中已核对的证据，且至少引用一项。")
        if (not run["evidence_check"]["complete"] or run["analysis"]["missing_fields"]) and data.decision != "证据不足":
            raise ApiError(409, "EVIDENCE_INCOMPLETE", "原始证据不完整或日志关键字段缺失时只能认定为证据不足。")
        result = {"decision": data.decision, "rationale": data.rationale.strip(), "evidence_ids": list(data.evidence_ids),
                  "reviewer": copy.deepcopy(ACTOR), "time": datetime.now(UTC).isoformat(), "request_id": request.state.request_id}
        run["review"] = result
        run["phase"] = "reviewed"
        audit(request, run, "human_review", "RECORDED", f"固定演示人工身份认定：{data.decision}。", run["case_id"])
        return copy.deepcopy(result)


@router.get("/demo/c")
def c_page():
    return FileResponse(STATIC / "demo-c.html")
