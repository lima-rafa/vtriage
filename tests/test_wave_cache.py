from __future__ import annotations

import json
from pathlib import Path

from vtriage.analyzer import _load_wave_cache, _save_wave_cache


def test_wave_cache_roundtrip(tmp_path: Path):
    case_dir = tmp_path / "seed_0001"
    case_dir.mkdir(parents=True)

    payload = {
        "schema": "v1",
        "waves_mtime_ns": 123,
        "waves_size": 456,
        "knobs": {"tail_event_window": 50000, "top_n": 12},
        "wave_hash": "abc123",
        "prefixes": ["tb.u_dut.u_core"],
        "top_tail": [["tb.u_dut.u_core.a", 3]],
        "top_total": [["tb.u_dut.u_core.a", 3]],
    }

    _save_wave_cache(case_dir, payload)
    loaded = _load_wave_cache(case_dir)

    assert loaded is not None
    assert loaded["schema"] == "v1"
    assert loaded["wave_hash"] == "abc123"


def test_wave_cache_invalid_json_returns_none(tmp_path: Path):
    case_dir = tmp_path / "seed_0002"
    case_dir.mkdir(parents=True)

    (case_dir / "wave_cache.json").write_text("{not json", encoding="utf-8")
    assert _load_wave_cache(case_dir) is None
