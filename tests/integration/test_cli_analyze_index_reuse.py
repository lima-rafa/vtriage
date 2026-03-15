import json
from pathlib import Path

import pytest
import click  # <- ADD

from vtriage.cli import analyze

import time




def _write(p: Path, text: str) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")


def test_analyze_rebuild_writes_index_then_reuse_works(tmp_path: Path):
    run_dir = tmp_path / "artifacts" / "run_fake_001"
    seed_dir = run_dir / "tests" / "seed_0001"
    _write(seed_dir / "log.txt", "ERROR: something broke at tb/u_dut\n")
    _write(seed_dir / "fail.json", json.dumps({"seed": 1, "exit_code": 1}, indent=2))

    out_dir = tmp_path / "report"

    # 1) rebuild-index: deve gerar run_index.json + report
    with pytest.raises(click.exceptions.Exit) as ex1:
        analyze(
            artifact_dir=run_dir,
            out=out_dir,
            lenient=True,
            strict_waves=False,
            latest=False,
            profile="",
            tail_event_window=100,
            top_n=5,
            sketch_top_n=3,
            prefix_levels=1,
            reuse_index=True,
            rebuild_index=True,
            debug=True,
            json_out=True,
            max_bytes=10_000_000,
            tail_bytes=1_000_000,
            max_events=200_000,
            open_report=False,
        )

    assert ex1.value.exit_code in (0, 1)
    assert (run_dir / "run_index.json").exists()
    assert (out_dir / "report.md").exists()
    assert (out_dir / "report.html").exists()
    assert (out_dir / "report.json").exists()

    idx1 = json.loads((run_dir / "run_index.json").read_text(encoding="utf-8"))
    assert idx1.get("schema") == "run_index_v1"
    assert "fingerprint" in idx1 and "knobs" in idx1 and "summary" in idx1

    # 2) reuse-index: NÃO deve rebuildar (mantém generated_at se nada mudou)
    with pytest.raises(click.exceptions.Exit) as ex2:
        analyze(
            artifact_dir=run_dir,
            out=out_dir,
            lenient=True,
            strict_waves=False,
            latest=False,
            profile="",
            tail_event_window=100,
            top_n=5,
            sketch_top_n=3,
            prefix_levels=1,
            reuse_index=True,
            rebuild_index=False,
            debug=True,
            json_out=True,
            max_bytes=10_000_000,
            tail_bytes=1_000_000,
            max_events=200_000,
            open_report=False,
        )

    assert ex2.value.exit_code in (0, 1)
    idx2 = json.loads((run_dir / "run_index.json").read_text(encoding="utf-8"))
    assert idx2.get("generated_at") == idx1.get("generated_at")

    # 3) mudar knob -> deve invalidar reuse (rebuild)
    time.sleep(1.1)
    with pytest.raises(click.exceptions.Exit) as ex3:
        analyze(
            artifact_dir=run_dir,
            out=out_dir,
            lenient=True,
            strict_waves=False,
            latest=False,
            profile="",
            tail_event_window=999,  # muda knob
            top_n=5,
            sketch_top_n=3,
            prefix_levels=1,
            reuse_index=True,
            rebuild_index=False,
            debug=True,
            json_out=False,
            max_bytes=10_000_000,
            tail_bytes=1_000_000,
            max_events=200_000,
            open_report=False,
        )

    assert ex3.value.exit_code in (0, 1)
    idx3 = json.loads((run_dir / "run_index.json").read_text(encoding="utf-8"))
    assert idx3.get("generated_at") != idx1.get("generated_at")
    assert idx3["knobs"]["tail_event_window"] == 999
    assert idx1["knobs"]["tail_event_window"] == 100
    assert idx3["knobs"] != idx1["knobs"]
    assert idx3.get("schema") == "run_index_v1"
