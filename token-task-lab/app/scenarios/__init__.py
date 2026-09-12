"""Scenario registry.

Registering a new business scenario is a one-line addition here plus one module
next to `tianjin_freight.py`. No engine, store, log-field or UI change is
required — that is the acceptance criterion this package exists to satisfy.
"""

from __future__ import annotations

from .base import Material, Scenario, ToolSpec
from .tianjin_freight import TIANJIN_FREIGHT

SCENARIOS: dict[str, Scenario] = {
    TIANJIN_FREIGHT.key: TIANJIN_FREIGHT,
}


def get_scenario(key: str) -> Scenario | None:
    return SCENARIOS.get(key)


def scenario_catalog() -> dict[str, dict]:
    """Public shape of every registered scenario, for the browser."""
    return {
        key: {
            "key": scenario.key,
            "name": scenario.name,
            "request_text": scenario.request_text,
            "task": scenario.task,
            "known": list(scenario.known),
            "missing": list(scenario.missing),
            "next_actions": list(scenario.next_actions),
            "human_gates": list(scenario.human_gates),
            "dependencies": scenario.dependency_list(),
            "tools": [
                {
                    "name": tool.name,
                    "title": tool.title,
                    "description": tool.description,
                    "available": tool.available,
                    "verified": tool.verified,
                    "provenance": tool.provenance,
                }
                for tool in scenario.tools
            ],
        }
        for key, scenario in SCENARIOS.items()
    }


__all__ = [
    "Material",
    "Scenario",
    "ToolSpec",
    "SCENARIOS",
    "get_scenario",
    "scenario_catalog",
]
