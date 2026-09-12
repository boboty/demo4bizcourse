from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel

app = FastAPI(title="Token Task Lab", version="0.1.0")
ROOT = Path(__file__).resolve().parents[1]
STATIC = ROOT / "static" / "index.html"


class RunRequest(BaseModel):
    scenario: str = "tianjin-freight"
    mode: str = "C"
    request_text: str = "天津新港到釜山，下周三货好，两个20GP，帮我看看船期和价格。"


SCENARIOS = {
    "tianjin-freight": {
        "name": "天津货代询价",
        "request_text": "天津新港到釜山，下周三货好，两个20GP，帮我看看船期和价格。",
        "known": ["起运港：天津新港", "目的港：釜山", "箱型箱量：20GP × 2"],
        "missing": ["可核验的实时/有效船期", "有效报价资料", "舱位确认"],
        "human_gates": ["最终报价确认", "舱位承诺"],
    }
}


def skeleton_run(payload: RunRequest) -> dict:
    scenario = SCENARIOS[payload.scenario]
    run_id = str(uuid4())
    steps = [
        {"step": 1, "action": "解析客户需求", "status": "ready", "model": None, "input_tokens": None, "output_tokens": None, "cached_tokens": None, "tool_calls": 0, "latency_ms": None},
        {"step": 2, "action": "识别已知条件与缺失条件", "status": "ready", "model": None, "input_tokens": None, "output_tokens": None, "cached_tokens": None, "tool_calls": 0, "latency_ms": None},
        {"step": 3, "action": "获取可核验业务事实", "status": "blocked", "model": None, "input_tokens": None, "output_tokens": None, "cached_tokens": None, "tool_calls": 1, "latency_ms": None},
        {"step": 4, "action": "业务判断与人工确认", "status": "waiting_human", "model": None, "input_tokens": None, "output_tokens": None, "cached_tokens": None, "tool_calls": 0, "latency_ms": None},
    ]
    return {
        "run_id": run_id,
        "scenario": payload.scenario,
        "mode": payload.mode,
        "request_text": payload.request_text,
        "task": "根据客户询价识别条件，获取可核验船期/报价事实，形成候选方案；事实不足时停止并标记待确认项。",
        "known": scenario["known"],
        "missing": scenario["missing"],
        "human_gates": scenario["human_gates"],
        "steps": steps,
        "usage": {"model_calls": 0, "tool_calls": 1, "input_tokens": None, "output_tokens": None, "cached_tokens": None},
        "evidence_level": "skeleton_only",
        "note": "当前版本只提供教学结构，不伪造 Token、船期或报价。真实 provider 接入后由运行日志填充 usage。",
    }


@app.get("/")
def home():
    return FileResponse(STATIC)


@app.get("/api/scenarios")
def scenarios():
    return SCENARIOS


@app.post("/api/runs")
def create_run(payload: RunRequest):
    if payload.scenario not in SCENARIOS:
        raise HTTPException(status_code=404, detail="scenario not found")
    if payload.mode not in {"A", "B", "C", "D"}:
        raise HTTPException(status_code=400, detail="mode must be A/B/C/D")
    return skeleton_run(payload)
