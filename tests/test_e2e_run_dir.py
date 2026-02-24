from __future__ import annotations

import json
from pathlib import Path

from vtriage.analyzer import analyze_run, subcluster_by_wave_hash


def _write_seed(
    seed_dir: Path,
    *,
    fail: bool,
    log_lines: list[str],
    vcd_var_name: str = "tb.u_dut.u_core.a",
) -> None:
    seed_dir.mkdir(parents=True, exist_ok=True)
    (seed_dir / "log.txt").write_text("\n".join(log_lines) + "\n", encoding="utf-8")

    if fail:
        (seed_dir / "fail.json").write_text(json.dumps({"seed": seed_dir.name}), encoding="utf-8")

        # VCD pequeno com 3 toggles
        vcd = "\n".join(
            [
                "$date today $end",
                "$version fake $end",
                "$timescale 1ns $end",
                "$scope module tb $end",
                f"$var wire 1 ! {vcd_var_name} $end",
                "$upscope $end",
                "$enddefinitions $end",
                "#0",
                "0!",
                "#10",
                "1!",
                "#20",
                "0!",
                "",
            ]
        )
        (seed_dir / "waves.vcd").write_text(vcd, encoding="utf-8")


def test_e2e_analyze_run_builds_cluster_and_wave_hash(tmp_path: Path):
    run_dir = tmp_path / "run_001"
    tests_dir = run_dir / "tests"
    tests_dir.mkdir(parents=True)

    # FAIL seed (com log + waves)
    _write_seed(
        tests_dir / "seed_0001",
        fail=True,
        log_lines=[
            "%Error: Assertion failed at tb/u_dut/u_core: mismatch expected got",
            "opening /home/user/proj/build/out.log",
        ],
        vcd_var_name="tb.u_dut.u_core.a",
    )

    # PASS seed (só log)
    _write_seed(
        tests_dir / "seed_0002",
        fail=False,
        log_lines=["PASS"],
    )

    results, clusters = analyze_run(
        run_dir,
        tail_event_window=50_000,
        top_n=20,
        sketch_top_n=12,
        prefix_levels=2,
    )

    assert len(results) == 2
    assert len(clusters) == 1

    (sig, items), = list(clusters.items())
    assert "ERROR" in sig
    assert "verilator_error" in sig
    assert "tb/u_dut/u_core" in sig

    ex = items[0]
    assert ex.wave_hash is not None
    assert len(ex.wave_hash) >= 8
    assert ex.prefixes is not None
    assert any("tb.u_dut.u_core" in p for p in ex.prefixes)

    subs = subcluster_by_wave_hash(items)
    assert len(subs) == 1
    wh, subitems = next(iter(subs.items()))
    assert wh == ex.wave_hash
    assert len(subitems) == 1
