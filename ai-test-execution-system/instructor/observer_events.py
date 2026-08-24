"""Fail-open 的课堂观察事件发布器。

Observer 是旁路展示层。正式执行代码可以发布事件，但任何写入失败都必须
被吞掉，不能改变测试结果、Retry、Failure Cause 或 Self-Heal 判断。
"""

from __future__ import annotations

import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock
from typing import Any, Dict, Iterable, Optional


PROJECT_ROOT = Path(__file__).resolve().parents[1]
OBSERVER_ROOT = Path(os.environ.get("OBSERVER_RUNTIME_ROOT", PROJECT_ROOT / "artifacts" / "observer"))
CURRENT_PATH = OBSERVER_ROOT / "current.json"
EVENTS_PATH = OBSERVER_ROOT / "events.jsonl"
_WRITE_LOCK = Lock()


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _optional_fields(**fields: Any) -> Dict[str, Any]:
    return {key: value for key, value in fields.items() if value is not None}


def _atomic_write(path: Path, value: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temp_name = tempfile.mkstemp(prefix=".observer-current-", suffix=".json", dir=str(path.parent))
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as output:
            json.dump(value, output, ensure_ascii=False, indent=2)
            output.write("\n")
            output.flush()
            os.fsync(output.fileno())
        os.replace(temp_name, path)
    except Exception:
        try:
            os.unlink(temp_name)
        except OSError:
            pass
        raise


def _append_event(path: Path, event: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    line = json.dumps(event, ensure_ascii=False, separators=(",", ":")) + "\n"
    with path.open("a", encoding="utf-8") as output:
        output.write(line)
        output.flush()


def publish_event(
    *,
    source: str,
    stage: str,
    event: str,
    status: str = "INFO",
    title: Optional[str] = None,
    demo: Optional[str] = None,
    run_id: Optional[str] = None,
    scenario_id: Optional[str] = None,
    scenario_index: Optional[int] = None,
    scenario_total: Optional[int] = None,
    facts: Optional[Dict[str, Any]] = None,
    expected: Optional[Dict[str, Any]] = None,
    actual: Optional[Dict[str, Any]] = None,
    fact_results: Optional[Dict[str, str]] = None,
    decision: Optional[str] = None,
    evidence: Optional[Iterable[str]] = None,
) -> None:
    """发布一个展示事件；所有异常都 fail-open。"""

    try:
        payload: Dict[str, Any] = {
            "timestamp": utc_now(),
            "source": source,
            "stage": stage,
            "event": event,
            "status": status,
            **_optional_fields(
                title=title or event,
                demo=demo,
                run_id=run_id,
                scenario_id=scenario_id,
                scenario_index=scenario_index,
                scenario_total=scenario_total,
                facts=facts,
                expected=expected,
                actual=actual,
                fact_results=fact_results,
                decision=decision,
                evidence=list(evidence) if evidence is not None else None,
            ),
        }
        with _WRITE_LOCK:
            _append_event(EVENTS_PATH, payload)
            _atomic_write(CURRENT_PATH, payload)
    except Exception:
        return


def publish_context_event(
    context: Any,
    *,
    source: str,
    stage: str,
    event: str,
    status: str = "INFO",
    title: Optional[str] = None,
    facts: Optional[Dict[str, Any]] = None,
    expected: Optional[Dict[str, Any]] = None,
    actual: Optional[Dict[str, Any]] = None,
    fact_results: Optional[Dict[str, str]] = None,
    decision: Optional[str] = None,
    evidence: Optional[Iterable[str]] = None,
) -> None:
    metadata = getattr(context, "observer", {}) or {}
    publish_event(
        source=source,
        stage=stage,
        event=event,
        status=status,
        title=title,
        facts=facts,
        expected=expected,
        actual=actual,
        fact_results=fact_results,
        decision=decision,
        evidence=evidence,
        **{key: metadata.get(key) for key in (
            "demo", "run_id", "scenario_id", "scenario_index", "scenario_total"
        )},
    )


def read_json(path: Path) -> Dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
        return value if isinstance(value, dict) else {}
    except (OSError, ValueError, TypeError):
        return {}


def read_events(limit: int = 30) -> list[Dict[str, Any]]:
    try:
        lines = EVENTS_PATH.read_text(encoding="utf-8").splitlines()
    except OSError:
        return []
    events = []
    for line in lines[-max(1, min(limit, 100)):]:
        try:
            value = json.loads(line)
        except ValueError:
            continue
        if isinstance(value, dict):
            events.append(value)
    return events


def read_current() -> Dict[str, Any]:
    return read_json(CURRENT_PATH)


def reset_observer() -> None:
    """只删除 Observer 自己的 runtime 目录。"""
    import shutil

    try:
        if OBSERVER_ROOT.exists():
            shutil.rmtree(OBSERVER_ROOT)
    except OSError:
        raise
