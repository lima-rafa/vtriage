from __future__ import annotations

from pathlib import Path

from vtriage.vcd import vcd_wave_sketch_hash


def _write_vcd(path: Path, toggles: list[str]) -> None:
    header = """$date today $end
$version fake $end
$timescale 1ns $end
$scope module tb $end
$var wire 1 ! tb.u_dut.u_core.a $end
$upscope $end
$enddefinitions $end
"""
    body = "\n".join(toggles) + "\n"
    path.write_text(header + body, encoding="utf-8")


def test_vcd_wave_sketch_hash_is_stable_for_same_content(tmp_path: Path):
    vcd = tmp_path / "waves.vcd"
    _write_vcd(vcd, ["#0", "0!", "#10", "1!", "#20", "0!"])

    h1 = vcd_wave_sketch_hash(vcd, scope_prefixes=["tb.u_dut.u_core"], tail_event_window=50_000, top_n=12)
    h2 = vcd_wave_sketch_hash(vcd, scope_prefixes=["tb.u_dut.u_core"], tail_event_window=50_000, top_n=12)

    assert isinstance(h1, str) and len(h1) > 0
    assert h1 == h2


def test_vcd_wave_sketch_hash_changes_when_wave_changes(tmp_path: Path):
    vcd = tmp_path / "waves.vcd"
    _write_vcd(vcd, ["#0", "0!", "#10", "1!", "#20", "0!"])
    h1 = vcd_wave_sketch_hash(vcd, scope_prefixes=["tb.u_dut.u_core"], tail_event_window=50_000, top_n=12)

    # muda o padrão com mais eventos
    _write_vcd(vcd, ["#0", "0!", "#10", "1!", "#20", "0!", "#30", "1!"])
    h2 = vcd_wave_sketch_hash(vcd, scope_prefixes=["tb.u_dut.u_core"], tail_event_window=50_000, top_n=12)

    assert h1 != h2
