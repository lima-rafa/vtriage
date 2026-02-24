from __future__ import annotations

from vtriage.analyzer import extract_location, extract_location_from_lines


def test_extract_location_from_error_at_slash():
    s = "%Error: Assertion failed at tb/u_dut/u_core: mismatch expected got"
    assert extract_location(s) == "tb/u_dut/u_core"


def test_extract_location_from_error_at_dot():
    s = "%Error: Assertion failed at tb.u_dut.u_core: mismatch expected got"
    assert extract_location(s) == "tb/u_dut/u_core"


def test_extract_location_ignores_filesystem_paths():
    s = "opening /home/user/proj/build/out.log"
    assert extract_location(s) is None


def test_extract_location_from_lines_scans_all():
    lines = [
        "random stuff",
        "opening /home/user/proj/build/out.log",
        "%Error: Assertion failed at tb/u_dut/u_core: mismatch expected got",
    ]
    assert extract_location_from_lines(lines) == "tb/u_dut/u_core"
