"""FastAPI surface for the lab.

Demo 1 (business front) and Demo 2 (run back) are two views of one `RunRecord`,
addressed by the same `run_id`. An experiment is one A/B/C/D batch over the same
task and input, so the four records can be compared as one experiment rather
than four unrelated log files.
"""

from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from . import __version__
from .config import load_provider_config, runs_dir, save_runs_enabled
from .engine import MODE_LABELS, MODES, RunEngine
from .models import RunRecord
from .provider import OpenAICompatibleProvider
from .scenarios import get_scenario, scenario_catalog
from .store import RunStore
from .views import back_view, front_view

app = FastAPI(title="Token Task Lab", version=__version__)
ROOT = Path(__file__).resolve().parents[1]
STATIC = ROOT / "static" / "index.html"
RUNBOOK = ROOT / "static" / "runbook.html"

DEFAULT_SCENARIO = "tianjin-freight"


class RunRequest(BaseModel):
    scenario: str = DEFAULT_SCENARIO
    mode: str = "C"
    request_text: str = Field(
        default="", description="留空则使用该 scenario 的默认客户原话"
    )
    save: bool = True


class ExperimentRequest(BaseModel):
    scenario: str = DEFAULT_SCENARIO
    modes: list[str] = Field(default_factory=lambda: ["A", "B", "C", "D"])
    request_text: str = ""
    save: bool = True


def _engine() -> RunEngine:
    config = load_provider_config()
    return RunEngine(provider=OpenAICompatibleProvider(config), config=config)


def _store() -> RunStore:
    return RunStore(runs_dir())


def _resolve(payload: RunRequest | ExperimentRequest):
    scenario = get_scenario(payload.scenario)
    if scenario is None:
        raise HTTPException(status_code=404, detail="scenario not found")
    return scenario


def _record_payload(record: RunRecord, saved_path: str | None = None) -> dict:
    return {
        "front": front_view(record),
        "back": back_view(record),
        "saved_path": saved_path,
    }


def _persist(record: RunRecord, save: bool, store: RunStore) -> str | None:
    if not (save and save_runs_enabled()):
        return None
    return str(store.save(record))


@app.get("/")
def home():
    return FileResponse(STATIC)


@app.get("/runbook")
def runbook():
    """Single-page instructor cockpit: prep, validation, teaching flow and embedded demo."""
    return FileResponse(RUNBOOK)


@app.get("/api/health")
def health():
    config = load_provider_config()
    summaries = _store().list_summaries(limit=1000)
    live = [item for item in summaries if item.evidence_level == "live"]
    ready = [item for item in live if item.classroom_ready]
    unmeasured = [item for item in live if not item.classroom_ready]
    # 三个数字分开报：真实调用 / Token 计量完整 / 输出完整且可冻结。
    freeze = [item for item in live if item.freeze_ready]
    truncated = [item for item in live if item.output_evidence == "truncated"]
    unverified_output = [
        item for item in live if item.output_evidence == "unknown"
    ]

    notes = []
    if unmeasured:
        notes.append(
            f"有 {len(unmeasured)} 份记录是真实模型调用但缺少 Token 读数，"
            "不能作为 Token 实验记录。"
        )
    if truncated:
        notes.append(
            f"有 {len(truncated)} 份记录存在输出截断（finish_reason=length）："
            "Token 读数完整，但输出不完整，这组数字不适合课堂冻结。"
        )
    if unverified_output:
        notes.append(
            f"有 {len(unverified_output)} 份记录 provider 未上报 finish_reason，"
            "无法确认输出是否完整，暂不计入可冻结记录。"
        )
    if live and not ready:
        notes.append("还没有可用于 Token 对比的课堂记录，课前请先跑一次 scripts/record_runs.py。")

    return {
        "version": __version__,
        "provider": config.public(),
        "provider_ready": config.configured,
        "runs_dir": str(runs_dir()),
        "saved_runs": len(summaries),
        # 真实运行 ≠ Token 证据齐备，这两个数字必须分开报。
        "saved_live_runs": len(live),
        "classroom_ready_runs": len(ready),
        "unmeasured_live_runs": len(unmeasured),
        # 计量完整 ≠ 输出完整：可冻结要求两者同时成立。
        "freeze_ready_runs": len(freeze),
        "truncated_live_runs": len(truncated),
        "modes": MODE_LABELS,
        "notes": notes,
    }


@app.get("/api/scenarios")
def scenarios():
    return scenario_catalog()


@app.get("/api/runs")
def list_runs(limit: int = 200):
    summaries = _store().list_summaries(limit=limit)
    return {"records": [item.model_dump() for item in summaries]}


@app.get("/api/runs/{run_id}")
def get_run(run_id: str):
    """Replay: hand back a stored record, split into its front and back halves."""
    record = _store().get(run_id)
    if record is None:
        raise HTTPException(status_code=404, detail="run record not found")
    return _record_payload(record)


@app.post("/api/runs")
def create_run(payload: RunRequest):
    scenario = _resolve(payload)
    if payload.mode not in MODES:
        raise HTTPException(status_code=400, detail="mode must be A/B/C/D")

    request_text = payload.request_text.strip() or scenario.request_text
    record = _engine().execute(
        scenario=scenario, mode=payload.mode, request_text=request_text
    )
    return _record_payload(record, _persist(record, payload.save, _store()))


@app.get("/api/experiments")
def list_experiments(limit: int = 60):
    """Group saved runs into experiments, newest first."""
    grouped: dict[str, list[dict]] = {}
    order: list[str] = []
    for summary in _store().list_summaries(limit=1000):
        key = summary.experiment_id or ""
        if key not in grouped:
            grouped[key] = []
            order.append(key)
        grouped[key].append(summary.model_dump())

    experiments = []
    for key in order[:limit]:
        rows = sorted(grouped[key], key=lambda row: row["mode"])
        if key == "":
            experiments.append(
                {
                    "experiment_id": None,
                    "label": "单次运行（不属于任何对照实验）",
                    "scenario": rows[0]["scenario"],
                    "created_at": max(row["created_at"] for row in rows),
                    "modes": [row["mode"] for row in rows],
                    "records": rows,
                }
            )
            continue
        experiments.append(
            {
                "experiment_id": key,
                "label": "对照实验",
                "scenario": rows[0]["scenario"],
                "request_text": rows[0]["request_text"],
                "created_at": max(row["created_at"] for row in rows),
                "modes": [row["mode"] for row in rows],
                "records": rows,
            }
        )
    return {"experiments": experiments}


@app.get("/api/experiments/{experiment_id}")
def get_experiment(experiment_id: str):
    records = []
    for summary in _store().list_summaries(limit=1000):
        if summary.experiment_id != experiment_id:
            continue
        record = _store().get(summary.run_id)
        if record is not None:
            records.append(_record_payload(record))
    if not records:
        raise HTTPException(status_code=404, detail="experiment not found")
    records.sort(key=lambda item: item["front"]["mode"])
    return {"experiment_id": experiment_id, "records": records}


@app.post("/api/experiments")
def create_experiment(payload: ExperimentRequest):
    """Run the same task through several modes under one experiment_id."""
    scenario = _resolve(payload)
    modes = [mode.upper() for mode in payload.modes]
    unknown = [mode for mode in modes if mode not in MODES]
    if unknown:
        raise HTTPException(
            status_code=400, detail=f"unknown modes: {', '.join(unknown)}"
        )
    if not modes:
        raise HTTPException(status_code=400, detail="at least one mode is required")

    experiment_id = str(uuid4())
    request_text = payload.request_text.strip() or scenario.request_text
    engine = _engine()
    store = _store()

    results = []
    for mode in modes:
        record = engine.execute(
            scenario=scenario,
            mode=mode,
            request_text=request_text,
            experiment_id=experiment_id,
        )
        results.append(_record_payload(record, _persist(record, payload.save, store)))

    return {"experiment_id": experiment_id, "records": results}
