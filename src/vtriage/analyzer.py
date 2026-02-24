from __future__ import annotations
import json
import re
import os
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Iterable
from vtriage.vcd import vcd_top_suspects, vcd_wave_sketch_hash
from rich.console import Console
from datetime import datetime


console = Console()


@dataclass(frozen=True)
class Pattern:
    name: str
    kind: str
    regex: str

    def compiled(self) -> re.Pattern[str]:
        return re.compile(self.regex)


DEFAULT_PATTERNS = [
    Pattern("verilator_error", "ERROR", r"(?i)%Error:|Assertion failed|\$fatal|\$error"),
    Pattern("timeout", "TIMEOUT", r"(?i)timeout|watchdog|deadlock"),
    Pattern("mismatch", "MISMATCH", r"(?i)mismatch|expected .* got .*|differs"),
]

_RE_LOC = [
    # "... at tb/u_dut/u_core: ..."  OR "... at tb.u_dut.u_core: ..."
    re.compile(r"\bat\s+([A-Za-z_]\w*(?:[\/\.][A-Za-z_]\w*)+)\b"),
    # "... in tb/u_dut/u_core ..."
    re.compile(r"\bin\s+([A-Za-z_]\w*(?:[\/\.][A-Za-z_]\w*)+)\b"),
    # "... @ tb/u_dut/u_core ..."
    re.compile(r"\b@\s*([A-Za-z_]\w*(?:[\/\.][A-Za-z_]\w*)+)\b"),
]

_RE_HEX = re.compile(r"\b0x[0-9a-fA-F]+\b")
_RE_FLOAT = re.compile(r"\b\d+\.\d+\b")
_RE_INT = re.compile(r"(?<![A-Za-z_])\d+(?![A-Za-z_])")
_RE_PATH = re.compile(
    r"(?i)(?:"
    r"[A-Z]:[\\/][^\s]+"          # C:\... or C:/...
    r"|(?<![A-Za-z0-9_])/[^ \t\r\n:]+"  # /home/... (mas não tb/u_dut/u_core)
    r"|(?<![A-Za-z0-9_])\\\\[^ \t\r\n:]+"  # \\server\share...
    r"|(?<![A-Za-z0-9_])\./[^ \t\r\n:]+"   # ./relative/path
    r")"
)
_RE_WS = re.compile(r"\s+")

def subcluster_by_wave_hash(items: list[CaseResult]) -> dict[str, list[CaseResult]]:
    out: dict[str, list[CaseResult]] = {}
    for r in items:
        wh = r.wave_hash or "no_wave_hash"
        out.setdefault(wh, []).append(r)
    # ordena por tamanho desc
    return dict(sorted(out.items(), key=lambda kv: len(kv[1]), reverse=True))

def extract_location(s: str) -> str | None:
    for rx in _RE_LOC:
        m = rx.search(s)
        if m:
            loc = m.group(1).replace(".", "/")
            # avoid matching filesystem paths like C:/...
            if re.match(r"^[A-Za-z_]\w*(?:/[A-Za-z_]\w*)+$", loc):
                return loc
    return None


def normalize_message(s: str) -> str:
    s = s.strip()
    s = _RE_PATH.sub("<path>", s)
    s = _RE_HEX.sub("<hex>", s)
    s = _RE_FLOAT.sub("<num>", s)
    s = _RE_INT.sub("<num>", s)
    s = _RE_WS.sub(" ", s)
    return s

@dataclass
class Hit:
    pattern: Pattern
    line_no: int
    line: str


@dataclass
class CaseResult:
    seed: int
    case_dir: Path
    passed: bool
    hit: Hit | None
    signature: str
    wave_path: Path | None = None
    top_tail: list[tuple[str, int]] = field(default_factory=list)
    top_total: list[tuple[str, int]] = field(default_factory=list)
    prefixes: list[str] = field(default_factory=list)
    wave_hash: str | None = None

DEBUG = os.environ.get("VTRIAGE_DEBUG", "").strip() not in ("", "0", "false", "False", "no", "NO")

def _dbg(msg: str) -> None:
    if DEBUG:
        print(f"[debug] {msg}")

def _waves_fingerprint(wave_path: Path) -> dict:
    st = wave_path.stat()
    return {"waves_mtime_ns": st.st_mtime_ns, "waves_size": st.st_size}

def _knobs_dict(*, tail_event_window: int, top_n: int, sketch_top_n: int, prefix_levels: int) -> dict:
    return {
        "tail_event_window": int(tail_event_window),
        "top_n": int(top_n),
        "sketch_top_n": int(sketch_top_n),
        "prefix_levels": int(prefix_levels),
    }

def _cache_path(case_dir: Path) -> Path:
    return case_dir / "wave_cache.json"

def _load_wave_cache(case_dir: Path) -> dict | None:
    cache_file = _cache_path(case_dir)
    if not cache_file.exists():
        return None
    try:
        return json.loads(cache_file.read_text(encoding="utf-8"))
    except Exception:
        return None

def _save_wave_cache(case_dir: Path, payload: dict) -> None:
    cache_file = _cache_path(case_dir)  # <- CHAMA a função
    _dbg(f"cache_file={cache_file}, type={type(cache_file)}")
    cache_file.write_text(
        json.dumps(payload, indent=2, sort_keys=True),
        encoding="utf-8",
    )


def _extract_seed(case_dir: Path) -> int:
    # case_dir name: seed_0001
    s = case_dir.name.split("_", 1)[-1]
    return int(s)


def _read_lines(path: Path, limit: int = 2000) -> list[str]:
    if not path.exists():
        return []
    # ignore decode errors so logs never break the tool
    txt = path.read_text(encoding="utf-8", errors="replace")
    lines = txt.splitlines()
    return lines[:limit]


def find_first_hit(lines: list[str], patterns: list[Pattern]) -> Hit | None:
    compiled = [(p, p.compiled()) for p in patterns]
    for i, line in enumerate(lines, start=1):
        for p, cre in compiled:
            if cre.search(line):
                return Hit(pattern=p, line_no=i, line=line.strip())
    return None


def signature_from(hit: Hit | None, lines: list[str]) -> str:
    if hit is None:
        tail = ""
        for l in reversed(lines[-50:]):
            if l.strip():
                tail = l.strip()
                break

        if not lines:
            return "PASS"

        loc = extract_location(tail) or "-"
        msg = normalize_message(tail)[:200] if tail else "UNCLASSIFIED"
        return f"UNCLASSIFIED::unmatched::{loc}::{msg}"

    loc = extract_location(hit.line) or "-"
    msg = normalize_message(hit.line)[:200]
    return f"{hit.pattern.kind}::{hit.pattern.name}::{loc}::{msg}"

def scope_prefixes_from_signature(sig: str) -> list[str]:
    parts = sig.split("::", 3)
    if len(parts) != 4:
        return []

    _kind, _pat, loc, _msg = parts
    loc = (loc or "").strip()
    if not loc or loc == "-":
        return []

    # normalize a bit
    loc = loc.strip().strip(" .:/")

    dot = loc.replace("/", ".")
    slash = loc.replace(".", "/")

    # priority: dot first (common in VCD refs), then slash
    out = []
    for p in (dot, slash, loc):
        if p and p not in out:
            out.append(p)
    return out

def collect_cases(run_dir: Path) -> list[Path]:
    tests_dir = run_dir / "tests"
    if not tests_dir.exists():
        return []
    return sorted([p for p in tests_dir.iterdir() if p.is_dir() and p.name.startswith("seed_")])

def analyze_run(
    run_dir: Path,
    patterns: list[Pattern] | None = None,
    *,
    tail_event_window: int = 50_000,
    top_n: int = 20,
    sketch_top_n: int = 12,
    prefix_levels: int = 2,
) -> tuple[list[CaseResult], dict[str, list[CaseResult]]]:
    _dbg(f"analyzer.py loaded from: {__file__}")
    patterns = patterns or DEFAULT_PATTERNS
    results: list[CaseResult] = []

    for case_dir in collect_cases(run_dir):
        seed = _extract_seed(case_dir)
        log_path = case_dir / "log.txt"
        fail_path = case_dir / "fail.json"
        passed = not fail_path.exists()

        lines = _read_lines(log_path)

        # defaults sempre definidos (evita NameError / tipos inconsistentes)
        wave_path: Path | None = None
        wave_hash: str | None = None
        top_tail: list[tuple[str, int]] = []
        top_total: list[tuple[str, int]] = []
        prefixes: list[str] = []

        hit = None
        sig = "PASS"

        if not passed:
            hit = find_first_hit(lines, patterns)
            sig = signature_from(hit, lines)

            candidate = case_dir / "waves.vcd"
            if candidate.exists():
                wave_path = candidate

                # knobs que afetam a análise do VCD (mudou -> invalida cache)
                knobs = _knobs_dict(
                    tail_event_window=tail_event_window,
                    top_n=top_n,
                    sketch_top_n=sketch_top_n,
                    prefix_levels=prefix_levels,
                )

                # -----------------------
                # 1) tenta reaproveitar cache
                # -----------------------
                used_cache = False
                cached = _load_wave_cache(case_dir)

                if cached and cached.get("schema") == "v1":
                    fp = _waves_fingerprint(wave_path)
                    same_vcd = (
                        cached.get("waves_mtime_ns") == fp["waves_mtime_ns"]
                        and cached.get("waves_size") == fp["waves_size"]
                    )
                    same_knobs = (cached.get("knobs") == knobs)

                    if same_vcd and same_knobs:
                        prefixes = cached.get("prefixes") or []
                        wave_hash = cached.get("wave_hash")
                        top_tail = cached.get("top_tail") or []
                        top_total = cached.get("top_total") or []
                        used_cache = True
                if used_cache:
                    _dbg(f"[cache] HIT  seed={seed:04d}")
                else:
                    _dbg(f"[cache] MISS seed={seed:04d}")

                if not used_cache:
                    # 1) tenta location direto da linha do hit
                    loc = extract_location(hit.line) if hit else None

                    # 2) fallback: tenta location embutida na signature
                    if not loc and sig.count("::") >= 3:
                        _k, _p, sig_loc, _m = sig.split("::", 3)
                        if sig_loc and sig_loc != "-":
                            loc = sig_loc

                    # 3) prefixes a partir do loc
                    prefixes = expand_location_prefixes(loc, levels=prefix_levels)

                    # 4) fallback final: extrai do log inteiro
                    if not prefixes:
                        loc2 = extract_location_from_lines(lines)
                        if loc2:
                            prefixes = expand_location_prefixes(loc2, levels=prefix_levels)

                    # wave hash (mesmo scope_prefixes)
                    try:
                        wave_hash = vcd_wave_sketch_hash(
                            wave_path,
                            scope_prefixes=prefixes if prefixes else None,
                            tail_event_window=tail_event_window,
                            top_n=sketch_top_n,
                        )
                    except Exception:
                        wave_hash = None

                    # suspects: filtrado -> fallback global
                    def _suspects(scope: list[str] | None):
                        return vcd_top_suspects(
                            wave_path,
                            tail_event_window=tail_event_window,
                            top_n=top_n,
                            scope_prefixes=scope,
                        )

                    if prefixes:
                        try:
                            top_tail, top_total, _stats = _suspects(prefixes)
                        except Exception:
                            top_tail, top_total = [], []

                        if not top_tail:
                            try:
                                top_tail, top_total, _stats = _suspects(None)
                            except Exception:
                                top_tail, top_total = [], []
                    else:
                        try:
                            top_tail, top_total, _stats = _suspects(None)
                        except Exception:
                            top_tail, top_total = [], []

                    # salva cache
                    try:
                        fp = _waves_fingerprint(wave_path)
                        _save_wave_cache(
                            case_dir,
                            {
                                "schema": "v1",
                                **fp,
                                "knobs": knobs,
                                "prefixes": prefixes,
                                "wave_hash": wave_hash,
                                "top_tail": top_tail,
                                "top_total": top_total,
                            },
                        )
                    except Exception as e:
                        _dbg(f"[yellow]warn[/yellow]: failed to save wave cache: {e}")

        results.append(
            CaseResult(
                seed=seed,
                case_dir=case_dir,
                passed=passed,
                hit=hit,
                signature=sig,
                wave_path=wave_path,
                top_tail=top_tail,
                top_total=top_total,
                prefixes=prefixes,
                wave_hash=wave_hash,
            )
        )

    clusters: dict[str, list[CaseResult]] = {}
    for r in results:
        if r.passed:
            continue
        clusters.setdefault(r.signature, []).append(r)

    clusters = dict(sorted(clusters.items(), key=lambda kv: len(kv[1]), reverse=True))
    knobs_used = _knobs_dict(
        tail_event_window=tail_event_window,
        top_n=top_n,
        sketch_top_n=sketch_top_n,
        prefix_levels=prefix_levels,
    )

    try:
        idx = write_run_index(run_dir, results=results, clusters=clusters, knobs=knobs_used)
    except Exception:
        pass
    return results, clusters

def snippet(lines: list[str], line_no: int, radius: int = 6) -> list[str]:
    if line_no <= 0:
        return lines[-20:]
    start = max(0, line_no - 1 - radius)
    end = min(len(lines), line_no - 1 + radius + 1)
    out = []
    for idx in range(start, end):
        prefix = ">> " if (idx + 1) == line_no else "   "
        out.append(f"{prefix}{idx+1:04d}: {lines[idx]}")
    return out

_LOC_RE = re.compile(r"(?i)\bat\s+([A-Za-z0-9_./$-]+)\s*:")

def extract_location_from_lines(lines: list[str]) -> str | None:
    for line in lines:
        m = _LOC_RE.search(line)
        if not m:
            continue
        loc = m.group(1).strip()
        loc = re.sub(r"[):,\s]+$", "", loc)   # tira lixo no fim
        loc = loc.strip().strip(" .:/")
        return loc or None
    return None

def location_to_scope_prefixes(location: str | None) -> list[str]:
    """
    Convert location text to likely scope prefixes to match VCD names.

    Examples:
        "tb/u_dut/u_core"   -> ["tb.u_dut.u_core", "tb/u_dut/u_core"]
        "tb.u_dut.u_core"   -> ["tb.u_dut.u_core", "tb/u_dut/u_core"]
        "tb/u_dut/u_core:"  -> ["tb.u_dut.u_core", "tb/u_dut/u_core"]
    """
    if not location:
        return []

    loc = location.strip()

    # remove common trailing punctuation around locations
    loc = re.sub(r"[):,\s]+$", "", loc)
    loc = loc.strip().strip(" .:/")

    if not loc:
        return []

    dot = loc.replace("/", ".")
    slash = loc.replace(".", "/")

    out = []
    for p in (dot, slash):
        if p and p not in out:
            out.append(p)

    # optional: also allow dropping leading "tb." if you ever see locations without tb
    if dot.startswith("tb."):
        short = dot[len("tb."):]
        if short and short not in out:
            out.append(short)

    return out

def expand_location_prefixes(loc: str | None, levels: int = 2) -> list[str] | None:
    """
    Expande prefixes por "drop à esquerda" (mais útil p/ VCD):
        "tb/u_dut/u_core" -> ["tb.u_dut.u_core", "u_dut.u_core", "u_core"]  (levels=2)
        "tb.u_dut.u_core" -> ["tb.u_dut.u_core", "u_dut.u_core", "u_core"]  (levels=2)

    levels = quantos drops do começo (left) você permite.
    Retorna None se não tiver nada útil.
    """
    if not loc:
        return None

    s = loc.strip().strip(" .:/")
    if not s:
        return None

    # normaliza separador para '.'
    s = s.replace("\\", "/").replace("/", ".")
    while ".." in s:
        s = s.replace("..", ".")
    s = s.strip(".")
    if not s:
        return None

    parts = [p for p in s.split(".") if p]
    if len(parts) == 0:
        return None

    max_drop = min(levels, max(0, len(parts) - 1))

    out: list[str] = []
    seen: set[str] = set()
    for drop in range(0, max_drop + 1):
        p = ".".join(parts[drop:])
        if p and p not in seen:
            out.append(p)
            seen.add(p)

    return out or None
def subcluster_by_wave_hash(items: list[CaseResult]) -> dict[str, list[CaseResult]]:
    """
    Dentro de um cluster (mesma signature), divide por wave_hash.
    - Se wave_hash None, cai em bucket "no_wave_hash".
    """
    sub: dict[str, list[CaseResult]] = {}
    for r in items:
        key = r.wave_hash or "no_wave_hash"
        sub.setdefault(key, []).append(r)
    # ordena por tamanho desc
    return dict(sorted(sub.items(), key=lambda kv: len(kv[1]), reverse=True))

def _run_index_path(run_dir: Path) -> Path:
    return run_dir / "run_index.json"

def write_run_index(
    run_dir: Path,
    *,
    results: list["CaseResult"],
    clusters: dict[str, list["CaseResult"]],
    knobs: dict,
) -> Path:
    total = len(results)
    fails = sum(1 for r in results if not r.passed)
    passes = total - fails

    # seeds list
    seeds = []
    for r in results:
        seeds.append(
            {
                "seed": r.seed,
                "passed": r.passed,
                "signature": r.signature,
                "wave_hash": r.wave_hash,
                "prefixes": r.prefixes or [],
                "case_dir": str(r.case_dir),
                "log": str(r.case_dir / "log.txt"),
                "waves": str(r.case_dir / "waves.vcd"),
            }
        )

    # clusters summary + subclusters by wave_hash
    clusters_out = []
    for sig, items in clusters.items():
        wh_map: dict[str, list[int]] = {}
        for it in items:
            wh = it.wave_hash or "-"
            wh_map.setdefault(wh, []).append(it.seed)
        subclusters = [
            {"wave_hash": wh, "count": len(seeds_), "seeds": seeds_}
            for wh, seeds_ in sorted(wh_map.items(), key=lambda kv: len(kv[1]), reverse=True)
        ]

        clusters_out.append(
            {
                "signature": sig,
                "count": len(items),
                "seeds": [it.seed for it in items],
                "subclusters": subclusters,
            }
        )

    payload = {
        "schema": "run_index_v1",
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "run_dir": str(run_dir),
        "knobs": knobs,
        "fingerprint": run_fingerprint(run_dir),
        "summary": {"total": total, "passes": passes, "fails": fails},
        "seeds": seeds,
        "clusters": clusters_out,
    }

    out_path = _run_index_path(run_dir)
    out_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    return out_path

def _file_fp(p: Path) -> dict | None:
    if not p.exists():
        return None
    st = p.stat()
    return {"path": str(p), "mtime_ns": st.st_mtime_ns, "size": st.st_size}

def run_fingerprint(run_dir: Path) -> dict:
    """
    Fingerprint barato e seguro:
    - para cada seed: log.txt e fail.json
    - para FAIL: waves.vcd também
    """
    fp = {"tests": []}
    tests_dir = run_dir / "tests"
    if not tests_dir.exists():
        return fp

    for case_dir in sorted([d for d in tests_dir.iterdir() if d.is_dir() and d.name.startswith("seed_")]):
        logp = case_dir / "log.txt"
        failp = case_dir / "fail.json"
        wavesp = case_dir / "waves.vcd"

        passed = not failp.exists()
        item = {
            "seed_dir": str(case_dir),
            "log": _file_fp(logp),
            "fail": _file_fp(failp),
            "waves": _file_fp(wavesp) if (not passed) else None,
        }
        fp["tests"].append(item)

    return fp

def load_run_index(run_dir: Path) -> dict | None:
    p = _run_index_path(run_dir)
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return None
