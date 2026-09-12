from __future__ import annotations

import json

import pytest

from app.config import ProviderConfig
from app.engine import RunEngine
from app.scenarios import get_scenario
from app.store import RunStore
from tests.conftest import FakeProvider

SCENARIO = get_scenario("tianjin-freight")


def make_record(mode: str = "C"):
    config = ProviderConfig(
        base_url="https://example.invalid/v1", api_key="k", model="fake-base"
    )
    return RunEngine(FakeProvider(), config).execute(
        scenario=SCENARIO, mode=mode, request_text=SCENARIO.request_text
    )


def test_round_trip_preserves_every_field(tmp_path):
    store = RunStore(tmp_path / "runs")
    record = make_record("C")
    store.save(record)

    loaded = store.get(record.run_id)
    assert loaded is not None
    assert loaded.model_dump() == record.model_dump()


def test_saved_file_is_readable_json_on_disk(tmp_path):
    store = RunStore(tmp_path / "runs")
    record = make_record("A")
    path = store.save(record)

    assert path.name == f"{record.run_id}.json"
    on_disk = json.loads(path.read_text(encoding="utf-8"))
    assert on_disk["usage"]["model_calls"] == 1
    assert on_disk["steps"][0]["phase"] == "direct"


def test_saving_creates_the_directory(tmp_path):
    store = RunStore(tmp_path / "deep" / "runs")
    store.save(make_record("A"))
    assert (tmp_path / "deep" / "runs").is_dir()


def test_unknown_run_is_none(tmp_path):
    assert RunStore(tmp_path / "runs").get("nope") is None


def test_missing_directory_lists_empty(tmp_path):
    assert RunStore(tmp_path / "runs").list_summaries() == []


def test_a_corrupt_file_does_not_break_the_listing(tmp_path):
    store = RunStore(tmp_path / "runs")
    store.save(make_record("A"))
    (store.root / "broken.json").write_text("{ not json", encoding="utf-8")

    summaries = store.list_summaries()
    assert len(summaries) == 1


@pytest.mark.parametrize("bad", ["../escape", "..", "", ".", "a/b"])
def test_run_id_cannot_escape_the_runs_directory(tmp_path, bad):
    store = RunStore(tmp_path / "runs")
    with pytest.raises(ValueError):
        store.path_for(bad)


def test_get_with_a_traversal_id_returns_none_instead_of_reading(tmp_path):
    store = RunStore(tmp_path / "runs")
    assert store.get("../../etc/passwd") is None
