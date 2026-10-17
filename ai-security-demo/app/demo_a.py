"""Demo A：固定虚构合同上的分类、服务端授权与脱敏。"""

import copy
import re
import threading
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Request
from fastapi.responses import FileResponse

from .errors import ApiError

router = APIRouter()
LOCK = threading.RLock()
ACTOR = {"id": "buyer-017", "role": "procurement_reader", "name": "采购观察员（固定演示身份）"}
CONTRACT_TEXT = (
    "某产业集团采购合同 HT-DEMO-017：供应商恒川设备（虚构）；签订日期 2026-10-01；"
    "采购设备 40 台，总金额 128000 元。经办人林岚，身份证号 110101199001010016（虚构无效示例），"
    "联系电话 19900000000（明显占位号码，不对应真实个人）。商业条款：单价 3200 元/台，年度采购上限 200 台，"
    "达到 100 台后返利 8%。当前状态：待归档。"
)
RULES = {
    "ordinary": "RULE-BIZ-01：合同编号、供应商、日期、数量、金额、状态属于本示例的一般业务资料。",
    "personal": "RULE-PII-01：经办人姓名、身份证号、联系电话可识别个人，按个人信息处理。",
    "commercial": "RULE-COM-01：单价、采购上限、返利条件属于虚构商业敏感信息。",
}
FIELDS = (
    ("contract_id", "合同编号", "ordinary", "HT-DEMO-017"),
    ("supplier", "供应商", "ordinary", "恒川设备（虚构）"),
    ("signed_date", "签订日期", "ordinary", "2026-10-01"),
    ("quantity", "采购数量", "ordinary", "40 台"),
    ("amount", "合同金额", "ordinary", "128000 元"),
    ("owner_name", "经办人姓名", "personal", "林岚"),
    ("owner_id", "身份证号", "personal", "110101199001010016"),
    ("owner_contact", "联系电话", "personal", "19900000000"),
    ("unit_price", "采购单价", "commercial", "3200 元/台"),
    ("annual_limit", "年度采购上限", "commercial", "200 台"),
    ("rebate", "返利条件", "commercial", "100 台后返利 8%"),
    ("status", "合同状态", "ordinary", "待归档"),
)
DOCUMENTS = {
    "PO-A-017": {"id": "PO-A-017", "classification": "普通采购合同", "granted": True},
    "PO-A-018": {"id": "PO-A-018", "classification": "普通采购合同", "granted": False},
    "DOC-CLASSIFIED-009": {"id": "DOC-CLASSIFIED-009", "classification": "涉密文件", "granted": False},
}
CONFIDENTIAL_ID = "DOC-CLASSIFIED-009"
STATIC = Path(__file__).parent / "static"
state: dict[str, Any] = {}


def reset_state() -> None:
    state.clear()
    state.update(
        epoch=uuid.uuid4().hex[:8],
        runs={},
        audits=[],
        counters={"identification": 0, "deidentification": 0, "upload": 0},
    )


reset_state()


def document_for(document_id: str) -> dict[str, Any]:
    document = DOCUMENTS.get(document_id)
    if document is None:
        raise ApiError(404, "DOCUMENT_NOT_FOUND", "演示资料不存在。")
    return document


def deny_confidential_before_processing(document_id: str, request: Request, action: str) -> dict[str, Any]:
    document = document_for(document_id)
    if document_id == CONFIDENTIAL_ID:
        audit(
            request, None, document_id, action, "DENY",
            "涉密分类策略在普通处理入口前拒绝；未读取或记录资料正文。",
            ["POLICY-A-CLASSIFIED-01"],
        )
        raise ApiError(403, "CONFIDENTIAL_BOUNDARY", "涉密资料禁止进入普通识别、脱敏或上传链。")
    return document


def identify_fields() -> list[dict[str, Any]]:
    found = []
    for key, label, category, value in FIELDS:
        match = re.search(re.escape(value), CONTRACT_TEXT)
        if match:
            found.append(
                {
                    "key": key,
                    "label": label,
                    "category": category,
                    "value": value,
                    "start": match.start(),
                    "end": match.end(),
                    "evidence": CONTRACT_TEXT[match.start() : match.end()],
                    "rule": RULES[category],
                }
            )
    return found


def redact_fields(source_text: str, fields: list[dict[str, Any]]) -> str:
    redacted = source_text
    for field in sorted(fields, key=lambda item: item["start"], reverse=True):
        redacted = redacted[: field["start"]] + "[已脱敏]" + redacted[field["end"] :]
    return redacted


async def require_empty_body(request: Request) -> None:
    body = await request.body()
    if body.strip() not in {b"", b"{}"}:
        raise ApiError(422, "INVALID_INPUT", "此接口不接受客户端正文、分类、身份或授权字段。")


def audit(request: Request, run: dict[str, Any] | None, document_id: str, action: str, result: str,
          reason: str, rules: list[str] | None = None) -> dict[str, Any]:
    entry = {
        "id": uuid.uuid4().hex[:12],
        "time": datetime.now(UTC).isoformat(),
        "run_id": run["id"] if run else None,
        "request_id": request.state.request_id,
        "actor_id": ACTOR["id"],
        "role": ACTOR["role"],
        "document_id": document_id,
        "action": action,
        "authorization": result,
        "rules": rules or [],
        "reason": reason,
    }
    state["audits"].append(entry)
    if run is not None:
        run["audit_ids"].append(entry["id"])
    return entry


@router.get("/api/v1/a/state")
def a_snapshot():
    with LOCK:
        return copy.deepcopy({"actor": ACTOR, **state})


@router.post("/api/v1/a/reset")
def a_reset():
    with LOCK:
        reset_state()
        return a_snapshot()


@router.get("/api/v1/a/documents")
def documents():
    return {
        "items": [
            {"id": "PO-A-017", "label": "虚构采购合同 · 已有处理授权"},
            {"id": "PO-A-018", "label": "虚构采购合同 · 已识别但未授权"},
            {"id": CONFIDENTIAL_ID, "label": "独立涉密示例 · 仅展示禁止边界", "body_available": False},
        ],
        "simulation": "本地虚构资料，确定性规则模拟；不是通用数据分类器。",
    }


@router.post("/api/v1/a/documents/{document_id}/identify", status_code=201)
async def identify(document_id: str, request: Request):
    with LOCK:
        document = deny_confidential_before_processing(document_id, request, "identify")
        await require_empty_body(request)
        state["counters"]["identification"] += 1
        run = {
            "id": uuid.uuid4().hex[:12],
            "epoch": state["epoch"],
            "document_id": document_id,
            "classification": document["classification"],
            "fields": identify_fields(),
            "source_text": CONTRACT_TEXT,
            "authorized": document["granted"],
            "audit_ids": [],
        }
        state["runs"][run["id"]] = run
        entry = audit(
            request, run, document_id, "identify", "ALLOW",
            "确定性字段规则完成识别；识别结果本身不授予后续处理权限。",
            ["RULE-BIZ-01", "RULE-PII-01", "RULE-COM-01"],
        )
        return {**copy.deepcopy(run), "audit": entry, "simulation": "规则命中为课堂模拟，不代表通用识别能力。"}


@router.post("/api/v1/a/documents/{document_id}/process/{run_id}")
async def deidentify(document_id: str, run_id: str, request: Request):
    with LOCK:
        document = deny_confidential_before_processing(document_id, request, "deidentify")
        try:
            confirmation = await request.json()
        except ValueError as exc:
            raise ApiError(422, "HUMAN_CONFIRMATION_REQUIRED", "请求必须明确包含人工下一步确认。") from exc
        run = state["runs"].get(run_id)
        if run is None or run["document_id"] != document_id or run["epoch"] != state["epoch"]:
            raise ApiError(404, "RUN_NOT_FOUND", "识别运行不存在或已重置，请重新识别。")
        if not document["granted"]:
            entry = audit(
                request, run, document_id, "deidentify", "DENY",
                "固定服务端策略未授予本资料脱敏处理权限；拒绝发生在脱敏函数调用之前。",
                ["POLICY-A-PROCESS-01"],
            )
            return_error = {"authorization": "DENY", "audit": entry, "run_id": run["id"]}
            from fastapi.responses import JSONResponse

            return JSONResponse(status_code=403, content=return_error)
        if confirmation != {"confirmation": "CONFIRM_NEXT_STEP"}:
            raise ApiError(422, "HUMAN_CONFIRMATION_REQUIRED", "请求必须明确包含人工下一步确认。")
        if not run.get("review") or not run.get("preview"):
            raise ApiError(409, "HUMAN_REVIEW_REQUIRED", "必须完成辅助识别、证据修正和脱敏预览后，才能人工确认下一步。")
        fields = [field for field in run["fields"] if field["category"] in {"personal", "commercial"}]
        redacted = redact_fields(run["source_text"], fields)
        state["counters"]["deidentification"] += 1
        entry = audit(
            request, run, document_id, "deidentify", "ALLOW",
            "固定服务端策略允许该虚构合同；只对识别出的个人信息与商业敏感字段执行遮盖。",
            ["POLICY-A-PROCESS-01", "RULE-PII-01", "RULE-COM-01"],
        )
        run["redacted_text"] = redacted
        return {
            "authorization": "ALLOW",
            "run_id": run["id"],
            "before": run["source_text"],
            "after": redacted,
            "retained": [field["value"] for field in run["fields"] if field["category"] == "ordinary"],
            "redacted_fields": [field["label"] for field in fields],
            "notice": "脱敏不保证匿名化，也不会自动授予其他处理或披露权限。",
            "audit": entry,
        }


@router.post("/api/v1/a/runs/{run_id}/assistant-review")
async def assistant_review(run_id: str, request: Request):
    """固定离线模拟：故意把普通金额误报为个人信息，等待人工核对。"""
    with LOCK:
        await require_empty_body(request)
        run = state["runs"].get(run_id)
        if run is None or run["epoch"] != state["epoch"]:
            raise ApiError(404, "RUN_NOT_FOUND", "识别运行不存在或已重置，请重新识别。")
        if run["document_id"] == CONFIDENTIAL_ID:
            raise ApiError(403, "CONFIDENTIAL_BOUNDARY", "涉密资料不能进入辅助识别链。")
        finding = {
            "id": "AI-FP-AMOUNT-01",
            "evidence": "128000 元",
            "suggested_category": "personal",
            "reason": "离线确定性模拟把金额误认为可识别个人的线索；这是一处固定误报，不代表真实模型输出。",
        }
        run["assistant_finding"] = finding
        run.pop("review", None)
        run.pop("preview", None)
        audit(request, run, run["document_id"], "assistant_identify", "SIMULATED",
              "离线确定性模拟产生一处固定误报，等待人工核对；未调用外部模型。", [finding["id"]])
        return {"simulation": "离线确定性辅助识别示例，不连接或调用模型。", "finding": copy.deepcopy(finding)}


@router.post("/api/v1/a/runs/{run_id}/correction")
async def correct_assistant_finding(run_id: str, request: Request):
    with LOCK:
        try:
            payload = await request.json()
        except ValueError as exc:
            raise ApiError(422, "INVALID_INPUT", "请提供人工核对的证据、修正类别和理由。") from exc
        run = state["runs"].get(run_id)
        if run is None or run["epoch"] != state["epoch"]:
            raise ApiError(404, "RUN_NOT_FOUND", "识别运行不存在或已重置，请重新识别。")
        finding = run.get("assistant_finding")
        expected = {"evidence": "128000 元", "suggested_category": "personal", "corrected_category": "ordinary"}
        if (
            run["document_id"] == CONFIDENTIAL_ID or not finding or
            not isinstance(payload, dict) or set(payload) != set(expected) | {"reason"} or
            any(payload.get(key) != value for key, value in expected.items()) or
            not isinstance(payload.get("reason"), str) or len(payload["reason"].strip()) < 8
        ):
            raise ApiError(422, "CORRECTION_EVIDENCE_REQUIRED", "人工修正必须逐项匹配误报证据，并填写理由；涉密资料不进入此流程。")
        run["review"] = {**payload, "reviewed_by": ACTOR["id"], "status": "human_corrected"}
        run.pop("preview", None)
        audit(request, run, run["document_id"], "human_correction", "CORRECTED",
              "人工按固定证据核对后修正辅助识别误报。", [finding["id"]])
        return copy.deepcopy(run["review"])


@router.post("/api/v1/a/runs/{run_id}/preview")
async def preview_redaction(run_id: str, request: Request):
    with LOCK:
        await require_empty_body(request)
        run = state["runs"].get(run_id)
        if run is None or run["epoch"] != state["epoch"]:
            raise ApiError(404, "RUN_NOT_FOUND", "识别运行不存在或已重置，请重新识别。")
        if not run.get("review"):
            raise ApiError(409, "HUMAN_REVIEW_REQUIRED", "请先逐项核对并修正辅助识别证据。")
        document = DOCUMENTS[run["document_id"]]
        if not document["granted"]:
            return {"authorization": "DENY", "message": "后端固定授权策略拒绝；不生成脱敏预览。", "run_id": run_id}
        fields = [field for field in run["fields"] if field["category"] in {"personal", "commercial"}]
        after = redact_fields(run["source_text"], fields)
        run["preview"] = True
        entry = audit(request, run, run["document_id"], "redaction_preview", "PREVIEW",
                      "仅展示本地脱敏预览；尚未确认后续处理。", ["POLICY-A-PROCESS-01"])
        return {"authorization": "ALLOW", "before": run["source_text"], "after": after,
                "message": "仅预览；尚未进入下一步。必须由人明确确认。", "run_id": run_id, "audit": entry}


@router.post("/api/v1/a/documents/{document_id}/upload")
async def upload(document_id: str, request: Request):
    with LOCK:
        document = deny_confidential_before_processing(document_id, request, "upload")
        await require_empty_body(request)
        state["counters"]["upload"] += 1
        entry = audit(
            request, None, document_id, "upload", "ALLOW",
            "本地虚构演示资料进入课堂上传模拟链；未连接外部服务。",
            ["POLICY-A-INTAKE-01"],
        )
        return {"authorization": "ALLOW", "document_id": document["id"], "audit": entry}


@router.get("/demo/a")
def a_page():
    return FileResponse(Path(STATIC) / "demo-a.html")
