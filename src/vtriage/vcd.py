from __future__ import annotations
import hashlib
import re
from collections import deque
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Iterator, Optional
@dataclass(frozen=True)
class VcdReadMeta:
    size_bytes: int
    used_tail_bytes: int
    truncated: bool
    reason: str | None  # "size>max_bytes" | "events>max_events" | None

@dataclass(frozen=True)
class VcdStats:
    total_events: int
    tail_events: int
    signals_defined: int

# Simple heuristics to ignore obvious noise (you can tune later)
_DEFAULT_IGNORE = re.compile(r"(?i)\b(clk|clock|rst|reset)\b")

def iter_vcd_lines_guarded(
    path: Path,
    *,
    max_bytes: int,
    tail_bytes: int,
) -> tuple[Iterator[str], VcdReadMeta]:
    st = path.stat()
    size = int(st.st_size)

    # default: read full file
    if size <= max_bytes:
        f = path.open("r", encoding="utf-8", errors="replace", newline="")
        meta = VcdReadMeta(size_bytes=size, used_tail_bytes=0, truncated=False, reason=None)
        return iter(f), meta

    # truncated: read only tail_bytes
    used = min(tail_bytes, size)
    bf = path.open("rb")
    bf.seek(max(0, size - used))
    data = bf.read()
    bf.close()

    # discard partial first line
    nl = data.find(b"\n")
    if nl != -1:
        data = data[nl + 1 :]

    text = data.decode("utf-8", errors="replace")
    meta = VcdReadMeta(size_bytes=size, used_tail_bytes=used, truncated=True, reason="size>max_bytes")
    return iter(text.splitlines()), meta

# --- add near the top ---
def _normalize_prefixes(prefixes: list[str] | None) -> list[str]:
    if not prefixes:
        return []
    out = []
    for p in prefixes:
        p = p.strip()
        if not p:
            continue
        out.append(p)
    return out


def _matches_scope(name: str, prefixes: list[str]) -> bool:
    if not prefixes:
        return True
    for p in prefixes:
        # strict-ish
        if name.startswith(p + ".") or name.startswith(p + "/") or name == p:
            return True
        # permissive fallback
        if ("/" in p or "." in p) and len(p) >= 6 and (p in name):
            return True
    return False


def _clean_name(name: str) -> str:
    # keep hierarchy as-is, but normalize separators a bit
    return name.strip()


def parse_vcd_vars(path: Path | None) -> dict[str, str]:
    """
    Parses $var lines and returns: {id_code -> signal_name}
    Example: $var wire 1 ! tb.u_dut.u_core.a $end  =>  "!" -> "tb.u_dut.u_core.a"
    """
    id_to_name: dict[str, str] = {}
    if path is None or (not path.exists()):
        return id_to_name

    # Leitura normal (header)
    with path.open("r", encoding="utf-8", errors="replace", newline="") as f:
        for line in f:
            if "$enddefinitions" in line:
                break
            line = line.strip()
            if not line.startswith("$var"):
                continue

            parts = line.split()
            if len(parts) < 5:
                continue

            _id = parts[3]

            # ref pode ser composto; pega tudo entre ref e $end
            ref_parts: list[str] = []
            for tok in parts[4:]:
                if tok == "$end":
                    break
                ref_parts.append(tok)

            ref = " ".join(ref_parts) if ref_parts else parts[4]
            id_to_name[_id] = _clean_name(ref)

    return id_to_name

def vcd_toggle_counts(
    path: Path,
    *,
    tail_event_window: int = 50_000,
    ignore_name_re: re.Pattern[str] | None = _DEFAULT_IGNORE,
    scope_prefixes: list[str] | None = None,
    max_bytes: int = 200_000_000,
    tail_bytes: int = 50_000_000,
    max_events: int = 5_000_000,
) -> tuple[dict[str, int], dict[str, int], VcdStats, VcdReadMeta]:
    """
    Single-pass VCD scanner:
        - total_counts[id] = toggles across whole file
        - tail_counts[id]  = toggles across last N value-change events

    "Event" here means: one value-change record for one id (scalar or vector).
    """
    id_to_name = parse_vcd_vars(path)
    total: dict[str, int] = {}
    tail: dict[str, int] = {}

    prefixes = _normalize_prefixes(scope_prefixes)

    tail_q: deque[str] = deque(maxlen=tail_event_window)
    total_events = 0

    def push_tail(_id: str) -> None:
        nonlocal total_events
        # manage tail counts with pop-left when deque is full
        if tail_q.maxlen is not None and len(tail_q) >= tail_q.maxlen:
            old = tail_q.popleft()
            tail[old] = tail.get(old, 0) - 1
            if tail.get(old, 0) <= 0:
                tail.pop(old, None)
        tail_q.append(_id)
        tail[_id] = tail.get(_id, 0) + 1
        total_events += 1

    if not path.exists():
        empty_meta = VcdReadMeta(size_bytes=0, used_tail_bytes=0, truncated=False, reason=None)
        return total, tail, VcdStats(0, 0, 0), empty_meta

    lines_iter, meta = iter_vcd_lines_guarded(path, max_bytes=max_bytes, tail_bytes=tail_bytes)

    in_header = True
    reason_events = None

    for raw in lines_iter:
        line = raw.strip()
        if not line:
            continue

        # Skip header until enddefinitions
        if in_header:
            if "$enddefinitions" in line:
                in_header = False
            continue

        # time markers like: #12345
        if line[0] == "#":
            continue

        # --- vector change ---
        if line[0] in ("b", "B"):
            parts = line.split()
            if len(parts) == 2:
                _id = parts[1]
                name = id_to_name.get(_id, _id)

                if ignore_name_re and ignore_name_re.search(name):
                    continue
                if not _matches_scope(name, prefixes):
                    continue

                total[_id] = total.get(_id, 0) + 1
                push_tail(_id)

                if total_events >= max_events:
                    reason_events = "events>max_events"
                    break
            continue

        # --- scalar change ---
        if line[0] in ("0", "1", "x", "X", "z", "Z"):
            _id = line[1:].strip()
            if not _id:
                continue
            name = id_to_name.get(_id, _id)

            if ignore_name_re and ignore_name_re.search(name):
                continue
            if not _matches_scope(name, prefixes):
                continue

            total[_id] = total.get(_id, 0) + 1
            push_tail(_id)

            if total_events >= max_events:
                reason_events = "events>max_events"
                break
            continue

        continue

    if reason_events is not None:
        meta = VcdReadMeta(
            size_bytes=meta.size_bytes,
            used_tail_bytes=meta.used_tail_bytes,
            truncated=True,
            reason=reason_events,
        )

    return total, tail, VcdStats(
        total_events=total_events,
        tail_events=len(tail_q),
        signals_defined=len(id_to_name),
    ), meta


def top_signals(
    counts: dict[str, int],
    id_to_name: dict[str, str],
    *,
    top_n: int = 20,
) -> list[tuple[str, int]]:
    items = sorted(counts.items(), key=lambda kv: kv[1], reverse=True)[:top_n]
    out: list[tuple[str, int]] = []
    for _id, c in items:
        out.append((id_to_name.get(_id, _id), c))
    return out


def vcd_top_suspects(
    path: Path,
    *,
    tail_event_window: int = 50_000,
    top_n: int = 20,
    scope_prefixes: list[str] | None = None,
    max_bytes: int = 200_000_000,
    tail_bytes: int = 50_000_000,
    max_events: int = 5_000_000,
) -> tuple[list[tuple[str, int]], list[tuple[str, int]], VcdStats, VcdReadMeta]:
    id_to_name = parse_vcd_vars(path)
    total, tail, stats, meta = vcd_toggle_counts(
        path,
        tail_event_window=tail_event_window,
        scope_prefixes=scope_prefixes,
        max_bytes=max_bytes,
        tail_bytes=tail_bytes,
        max_events=max_events,
    )

    return (
        top_signals(tail, id_to_name, top_n=top_n),
        top_signals(total, id_to_name, top_n=top_n),
        stats,
        meta,
    )

def vcd_wave_sketch_hash(
    waves_path: Path,
    *,
    scope_prefixes: list[str] | None,
    tail_event_window: int = 50_000,
    top_n: int = 12,
    max_bytes: int = 200_000_000,
    tail_bytes: int = 50_000_000,
    max_events: int = 5_000_000,
) -> tuple[str | None, VcdReadMeta | None]:
    """
    Hash determinístico mais forte:
        - usa tail_top + total_top
        - inclui o escopo escolhido
        - fallback global se escopo não retornar sinais
    """
    def _pack(tag: str, items: list[tuple[str, int]]) -> list[str]:
        out = []
        for name, c in items[:top_n]:
            out.append(f"{tag}:{name}:{int(c)}")
        return out

    try:
        # 1) tenta com escopo
        tail_top, total_top, _stats, meta = vcd_top_suspects(
            waves_path,
            tail_event_window=tail_event_window,
            top_n=max(top_n, 20),
            scope_prefixes=scope_prefixes,
            max_bytes=max_bytes,
            tail_bytes=tail_bytes,
            max_events=max_events,
        )

        # 2) fallback global se escopo não trouxe nada
        if scope_prefixes and (not tail_top and not total_top):
            tail_top, total_top, _stats, meta = vcd_top_suspects(
                waves_path,
                tail_event_window=tail_event_window,
                top_n=max(top_n, 20),
                scope_prefixes=None,
                max_bytes=max_bytes,
                tail_bytes=tail_bytes,
                max_events=max_events,
            )

        if not tail_top and not total_top:
            return None, meta

        payload_parts: list[str] = []
        payload_parts.append(f"scope={scope_prefixes[0] if scope_prefixes else 'ALL'}")
        payload_parts.append(f"tailwin={tail_event_window}")
        payload_parts += _pack("T", tail_top or [])
        payload_parts += _pack("A", total_top or [])

        payload = "|".join(payload_parts).encode("utf-8")
        return (hashlib.sha1(payload).hexdigest()[:12], meta)
    except Exception:
        return (None, None)
