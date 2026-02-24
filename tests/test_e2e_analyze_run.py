from __future__ import annotations
import os
import json
from pathlib import Path

from vtriage.analyzer import analyze_run


def _write_case(case_dir: Path, *, seed: int, fail: bool, msg: str, vcd_variant: str) -> None:
    case_dir.mkdir(parents=True, exist_ok=True)

    # log
    (case_dir / "log.txt").write_text(msg + "\n", encoding="utf-8")

    # fail marker
    if fail:
        (case_dir / "fail.json").write_text(json.dumps({"seed": seed, "exit_code": 1}), encoding="utf-8")

    # waves (2 variantes diferentes -> hashes diferentes)
    header = """$date today $end
$version fake $end
$timescale 1ns $end
$scope module tb $end
$var wire 1 ! tb.u_dut.u_core.a $end
$upscope $end
$enddefinitions $end
"""

    if vcd_variant == "A":
        body = "\n".join(["#0", "0!", "#10", "1!", "#20", "0!"]) + "\n"
    else:
        body = "\n".join(["#0", "0!", "#10", "1!", "#20", "0!", "#30", "1!"]) + "\n"

    (case_dir / "waves.vcd").write_text(header + body, encoding="utf-8")


def test_analyze_run_e2e_clusters_and_wave_hash(tmp_path: Path):
    run_dir = tmp_path / "artifacts" / "run_test"
    tests_dir = run_dir / "tests"

    # 3 FAIL no mesmo bug (mesma signature), mas 1 deles com waves diferente
    msg = "%Error: Assertion failed at tb/u_dut/u_core: mismatch expected got"

    _write_case(tests_dir / "seed_0001", seed=1, fail=True, msg=msg, vcd_variant="A")
    _write_case(tests_dir / "seed_0003", seed=3, fail=True, msg=msg, vcd_variant="A")
    _write_case(tests_dir / "seed_0004", seed=4, fail=True, msg=msg, vcd_variant="B")

    # 2 PASS
    _write_case(tests_dir / "seed_0002", seed=2, fail=False, msg="PASS", vcd_variant="A")
    _write_case(tests_dir / "seed_0005", seed=5, fail=False, msg="PASS", vcd_variant="A")

    results, clusters = analyze_run(run_dir)

    assert len(results) == 5
    fails = [r for r in results if not r.passed]
    assert len(fails) == 3

    # deve existir 1 cluster principal (mesma assinatura)
    assert len(clusters) == 1
    sig, items = next(iter(clusters.items()))
    assert len(items) == 3

    # wave_hash deve existir e deve haver pelo menos 2 valores (A vs B)
    hashes = sorted(set(r.wave_hash for r in items if r.wave_hash))
    assert len(hashes) >= 2
