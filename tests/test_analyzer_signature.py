from __future__ import annotations

from vtriage.analyzer import normalize_message, signature_from, Hit, Pattern


def test_normalize_message_masks_paths_and_numbers():
    s = "%Error: at tb/u_dut/u_core: opening /home/user/proj/build/out.log id=123 val=0xDEADBEEF"
    out = normalize_message(s)
    assert "<path>" in out
    assert "<num>" in out
    assert "<hex>" in out
    # continua contendo o essencial
    assert "tb/u_dut/u_core" in out


def test_signature_from_hit_contains_kind_pattern_location_and_msg():
    p = Pattern("verilator_error", "ERROR", r"(?i)%Error:")
    hit = Hit(pattern=p, line_no=1, line="%Error: Assertion failed at tb/u_dut/u_core: mismatch expected got")
    sig = signature_from(hit, [hit.line])
    parts = sig.split("::", 3)
    assert len(parts) == 4
    kind, pat, loc, msg = parts
    assert kind == "ERROR"
    assert pat == "verilator_error"
    assert loc == "tb/u_dut/u_core"
    assert "Assertion failed" in msg


def test_signature_from_none_unclassified_on_fail_lines():
    # quando não tem hit, mas houve fail (lines existe), deve cair em UNCLASSIFIED
    lines = ["", "some fail text at tb/u_dut/u_core: boom"]
    sig = signature_from(None, lines)
    assert sig.startswith("UNCLASSIFIED::")
