"""Round 4 Suite serial executor。"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

from runner.retry_policy import run_business_retry
from scripts.run_pay_order_ios import lan_ip, read_case, run_once


SUPPORTED_EXECUTORS = {"workflow", "business_retry"}
CONFIGURATION_KEYS = {"ui_version", "payment_mode", "product_bug_mode"}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_suite(path: Path) -> Dict[str, Any]:
    suite = yaml.safe_load(path.read_text(encoding="utf-8"))
    if suite.get("version") != 1:
        raise ValueError("Suite 只支持 version: 1。")
    if suite.get("execution_mode") != "serial":
        raise ValueError("Round 4 Suite 只支持 execution_mode: serial。")
    scenarios = suite.get("scenarios")
    if not isinstance(scenarios, list) or not scenarios:
        raise ValueError("Suite 至少需要一个 scenario。")
    seen = set()
    required = {"scenario_id", "task", "configuration_override", "execution_purpose", "expected_behavior", "executor"}
    for scenario in scenarios:
        if not required.issubset(scenario):
            raise ValueError("Suite scenario 缺少必填字段：{0}".format(sorted(required - set(scenario))))
        scenario_id = scenario["scenario_id"]
        if scenario_id in seen:
            raise ValueError("Suite scenario_id 重复：{0}".format(scenario_id))
        seen.add(scenario_id)
        if scenario["executor"] not in SUPPORTED_EXECUTORS:
            raise ValueError("不支持的 scenario executor：{0}".format(scenario["executor"]))
        override = scenario["configuration_override"]
        if set(override) != CONFIGURATION_KEYS or not all(isinstance(value, str) for value in override.values()):
            raise ValueError("configuration_override 必须是三个字符串配置项。")
        if override["ui_version"] not in {"v1", "v2"}:
            raise ValueError("configuration_override.ui_version 不受支持。")
        if override["payment_mode"] not in {"normal", "timeout_before_commit", "timeout_after_commit"}:
            raise ValueError("configuration_override.payment_mode 不受支持。")
        if override["product_bug_mode"] not in {"off", "on"}:
            raise ValueError("configuration_override.product_bug_mode 不受支持。")
    return suite


def _write_json(path: Path, value: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _artifact_files(path: Path) -> List[str]:
    return sorted(str(item.relative_to(path)) for item in path.rglob("*") if item.is_file())


def _write_scenario_result(scenario_dir: Path, result: Dict[str, Any], scenario: Dict[str, Any], task: Path) -> Dict[str, Any]:
    result = dict(result)
    result.update(
        {
            "scenario_id": scenario["scenario_id"],
            "task": str(task),
            "execution_purpose": scenario["execution_purpose"],
            "expected_behavior": scenario["expected_behavior"],
            "configuration_override": scenario["configuration_override"],
        }
    )
    if result.get("api_facts") is not None and not (scenario_dir / "api-facts.json").is_file():
        _write_json(scenario_dir / "api-facts.json", result["api_facts"])
    _write_json(scenario_dir / "result.json", result)
    result["evidence_files"] = _artifact_files(scenario_dir)
    _write_json(scenario_dir / "result.json", result)
    return result


def run_suite(
    suite_path: Path,
    run_dir: Path,
    base_url: Optional[str] = None,
) -> Dict[str, Any]:
    """按 YAML 声明顺序串行执行 Suite，不生成或修改 UI steps。"""
    suite = load_suite(suite_path)
    project_root = suite_path.parent.parent
    base_url = (base_url or "http://{0}:8000".format(lan_ip())).rstrip("/")
    run_dir.mkdir(parents=True, exist_ok=False)
    started_at = utc_now()
    scenario_results: List[Dict[str, Any]] = []

    for scenario in suite["scenarios"]:
        scenario_dir = run_dir / "cases" / scenario["scenario_id"]
        task_path = (project_root / scenario["task"]).resolve()
        record: Dict[str, Any]
        try:
            case = read_case(task_path)
            if scenario["executor"] == "workflow":
                record = run_once(
                    case,
                    base_url,
                    scenario_dir,
                    configuration_override=scenario["configuration_override"],
                    round_name="Round 4 Suite",
                )
            else:
                record = run_business_retry(
                    case,
                    base_url,
                    scenario["configuration_override"],
                    scenario_dir,
                )
        except Exception as error:
            scenario_dir.mkdir(parents=True, exist_ok=True)
            record = {
                "started_at": utc_now(),
                "finished_at": utc_now(),
                "result": "FAIL",
                "error": str(error),
                "retry_count": 0,
            }
        scenario_results.append(_write_scenario_result(scenario_dir, record, scenario, task_path))

    finished_at = utc_now()
    run_record = {
        "run_id": run_dir.name,
        "suite": suite["suite_id"],
        "suite_path": str(suite_path),
        "execution_mode": suite["execution_mode"],
        "started_at": started_at,
        "finished_at": finished_at,
        "result": "PASS" if all(item.get("result") == "PASS" for item in scenario_results) else "FAIL",
        "scenarios": [
            {
                "scenario_id": item["scenario_id"],
                "result": item.get("result", "FAIL"),
                "started_at": item.get("started_at"),
                "finished_at": item.get("finished_at"),
            }
            for item in scenario_results
        ],
    }
    _write_json(run_dir / "suite.json", {"suite": suite["suite_id"], "execution_mode": suite["execution_mode"], "scenarios": suite["scenarios"]})
    _write_json(run_dir / "run.json", run_record)
    return run_record
