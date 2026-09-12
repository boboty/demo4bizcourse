"""FastAPI surface for the lab.

Demo 1 (business front) and Demo 2 (run back) are two views of one `RunRecord`,
addressed by the same `run_id`. The API never filters token numbers out of a
response — Demo 1's "no tokens on screen" rule is enforced by the page, which
only fills the back panel when the instructor opens it.
"""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from . import __version__
from .config import load_provider_config, runs_dir, save_runs_enabled
from .engine import MODE_LABELS, MODES, RunEngine
from .provider import OpenAICompatibleProvider
from .scenarios import get_scenario, scenario_catalog
from .store import RunStore
from .views import back_view, front_view

app = FastAPI(title="Token Task Lab", version=__version__)
ROOT = Path(__file__).resolve().parents[1]
STATIC = ROOT / "static" / "index.html"


class RunRequest(BaseModel):
    scenario: str = "tianjin-freight"
    mode: str = "C"
    request_text: str = Field(
        default="", description="留空则使用该 scenario 的默认客户原话"
    )
    save: bool = True


def _engine() -> RunEngine:
    config = load_provider_config()
    return RunEngine(provider=OpenAICompatibleProvider(config), config=config)


@app.get("/")
def home():
    return FileResponse(STATIC)


@app.get("/api/health")
def health():
    config = load_provider_config()
    store = RunStore(runs_dir())
    summaries = store.list_summaries(limit=1000)
    live = sum(1 for item in summaries if item.evidence_level == "live")
    return {
        "version": __version__,
        "provider": config.public(),
        "provider_ready": config.configured,
        "runs_dir": str(runs_dir()),
        "saved_runs": len(summaries),
        "saved_live_runs": live,
        "modes": MODE_LABELS,
    }


@app.get("/api/scenarios")
def scenarios():
    return scenario_catalog()


@app.get("/api/runs")
def list_runs(limit: int = 60):
    return {"records": [item.model_dump() for item in RunStore(runs_dir()).list_summaries(limit=limit)]}


@app.get("/api/runs/{run_id}")
def get_run(run_id: str):
    """Replay: hand back a stored record, split into its front and back halves."""
    record = RunStore(runs_dir()).get(run_id)
    if record is None:
        raise HTTPException(status_code=404, detail="run record not found")
    return {"front": front_view(record), "back": back_view(record)}


@app.post("/api/runs")
def create_run(payload: RunRequest):
    scenario = get_scenario(payload.scenario)
    if scenario is None:
        raise HTTPException(status_code=404, detail="scenario not found")
    if payload.mode not in MODES:
        raise HTTPException(status_code=400, detail="mode must be A/B/C/D")

    request_text = payload.request_text.strip() or scenario.request_text
    record = _engine().execute(
        scenario=scenario, mode=payload.mode, request_text=request_text
    )

    saved_path = None
    if payload.save and save_runs_enabled():
        saved_path = str(RunStore(runs_dir()).save(record))

    return {
        "front": front_view(record),
        "back": back_view(record),
        "saved_path": saved_path,
    }
