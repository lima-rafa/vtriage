from __future__ import annotations
import re
import os
import subprocess
import json
import shutil
from vtriage.config import VtriageConfig
from datetime import datetime
from pathlib import Path
import sys, subprocess
import typer
from rich import print
from jinja2 import Environment, BaseLoader, select_autoescape
from typing import Optional


from vtriage.analyzer import (
    analyze_run,
    _read_lines,
    snippet,
    extract_location_from_lines,
    subcluster_by_wave_hash,
    load_run_index,
    run_fingerprint,
    CaseResult,
)

def _open_file(path: Path) -> None:
    """Open file with default app (Windows/Linux/macOS)."""
    p = str(path)
    if os.name == "nt":
        os.startfile(p)  # type: ignore[attr-defined]
        return
    if sys.platform == "darwin":
        subprocess.run(["open", p], check=False)
        return
    subprocess.run(["xdg-open", p], check=False)


def _list_runs(artifacts_root: Path) -> list[Path]:
    if not artifacts_root.exists():
        return []
    runs = [d for d in artifacts_root.iterdir() if d.is_dir() and d.name.startswith("run_")]
    runs.sort(key=lambda p: p.name, reverse=True)
    return runs


def _read_index_summary(run_dir: Path) -> tuple[int, int, int] | None:
    idxp = run_dir / "run_index.json"
    if not idxp.exists():
        return None
    try:
        data = json.loads(idxp.read_text(encoding="utf-8"))
        if data.get("schema") != "run_index_v1":
            return None
        s = data.get("summary") or {}
        return int(s.get("total", 0)), int(s.get("passes", 0)), int(s.get("fails", 0))
    except Exception:
        return None


def _resolve_run_arg(
    *,
    repo_root: Path,
    artifacts_root: Path,
    run: Optional[Path],
    latest: bool,
) -> Path | None:
    # accept: --latest, "latest", explicit path, or run name (run_...)
    if latest or (run is not None and str(run).strip().lower() == "latest"):
        lr = resolve_latest_run(repo_root, artifacts_root)
        return lr

    if run is None:
        return None

    # if user passed a run name like "run_2026-..."
    r = Path(run)
    if not r.is_absolute() and str(r).startswith("run_"):
        cand = artifacts_root / str(r)
        if cand.exists():
            return cand

    # otherwise treat as path (relative to cwd)
    rr = (Path.cwd() / r).resolve() if not r.is_absolute() else r
    return rr

def _is_placeholder_path(p: Path) -> bool:
    s = str(p)
    return "..." in s or s.strip().endswith("run_...")

def _seed_dirs(run_dir: Path) -> list[Path]:
    tests = run_dir / "tests"
    if not tests.exists():
        return []
    return sorted([d for d in tests.iterdir() if d.is_dir() and d.name.startswith("seed_")])

def _recent_runs(artifacts_root: Path, limit: int = 5) -> list[Path]:
    if not artifacts_root.exists():
        return []
    runs = [d for d in artifacts_root.iterdir() if d.is_dir() and d.name.startswith("run_")]
    runs.sort(key=lambda p: p.name, reverse=True)
    return runs[:limit]

def _print_suggestions(*, repo_root: Path, artifacts_root: Path) -> None:
    runs = _recent_runs(artifacts_root, limit=5)
    if not runs:
        print(f"[yellow]hint[/yellow]: nenhuma pasta run_* encontrada em: {artifacts_root}")
        print(f"[yellow]hint[/yellow]: rode o runner primeiro (scripts/ci_run.ps1) para gerar artifacts.")
        return

    print("[yellow]hint[/yellow]: runs recentes:")
    for r in runs:
        print(f"  - {r}")

    print("")
    print("[yellow]hint[/yellow]: exemplo:")
    print(f"  vtriage analyze \"{runs[0]}\" --out .\\report")

def _as_str(p: Optional[Path]) -> str:
    return "" if p is None else str(p)

def _wants_latest(p: Optional[Path], latest_flag: bool) -> bool:
    if latest_flag:
        return True
    s = _as_str(p).strip().lower()
    return s in ("latest", "@latest", "last")

def _validate_artifact_dir_or_die(
    artifact_dir: Optional[Path],
    *,
    repo_root: Path,
    artifacts_root: Path,
    lenient: bool,
    latest: bool = False,
) -> Path:
    # 0) latest mode (explicit)
    if _wants_latest(artifact_dir, latest):
        runs = _recent_runs(artifacts_root, limit=1)
        if not runs:
            print(f"[red]error[/red]: nenhuma pasta run_* encontrada em: {artifacts_root}")
            print("[yellow]hint[/yellow]: rode o runner primeiro (scripts/ci_run.ps1) para gerar artifacts.")
            raise typer.Exit(code=2)
        return runs[0]

    # 1) artifact_dir obrigatório se não for latest
    if artifact_dir is None:
        print("[red]error[/red]: missing ARTIFACT_DIR")
        _print_suggestions(repo_root=repo_root, artifacts_root=artifacts_root)
        raise typer.Exit(code=2)

    # 2) placeholder tipo run_...
    if _is_placeholder_path(artifact_dir):
        print(f"[red]error[/red]: artifact_dir parece um placeholder: {artifact_dir}")
        print("[yellow]hint[/yellow]: substitua por um run real, ex: artifacts\\run_YYYY-MM-DD_HH-mm-ss")
        _print_suggestions(repo_root=repo_root, artifacts_root=artifacts_root)
        raise typer.Exit(code=2)

    # 3) normaliza para absoluto (relativo ao cwd)
    ad = artifact_dir
    if not ad.is_absolute():
        ad = (Path.cwd() / ad).resolve()

    # 4) existe?
    if not ad.exists():
        print(f"[red]error[/red]: artifact_dir does not exist: {artifact_dir}")
        _print_suggestions(repo_root=repo_root, artifacts_root=artifacts_root)
        raise typer.Exit(code=2)

    # 5) parece run?
    seeds = _seed_dirs(ad)
    if not seeds:
        print(f"[red]error[/red]: artifact_dir não parece um run do vtriage (faltou tests/seed_*): {ad}")
        _print_suggestions(repo_root=repo_root, artifacts_root=artifacts_root)
        raise typer.Exit(code=2)

    return ad

def resolve_latest_run(repo_root: Path, artifacts_root: Path) -> Path | None:
    if not artifacts_root.exists():
        return None
    runs = [d for d in artifacts_root.iterdir() if d.is_dir() and d.name.startswith("run_")]
    if not runs:
        return None
    runs.sort(key=lambda p: p.name, reverse=True)  # usa nome run_YYYY-... que ordena bem
    return runs[0]

app = typer.Typer(no_args_is_help=True)

DEFAULT_TOML = """\
[project]
name = "my-rtl-project"
artifact_root = "artifacts"
report_dir = "report"
keep_waveforms = true

[runner]
simulator = "verilator"
cmd = "python scripts/sim_harness.py"
workdir = "."

[inputs]
log_glob = "artifacts/**/log.txt"
wave_glob = "artifacts/**/waves.vcd"
meta_glob = "artifacts/**/meta.json"

[failure_detection]
patterns = [
  { name="verilator_error", kind="ERROR", regex="(?i)%Error:|Assertion failed|\\$fatal|\\$error" },
  { name="timeout", kind="TIMEOUT", regex="(?i)timeout|watchdog|deadlock" },
  { name="mismatch", kind="MISMATCH", regex="(?i)mismatch|expected .* got .*|differs" }
]

[copilot]
enabled = false
"""

def _split_signature(sig: str) -> tuple[str, str, str, str]:
    """
    Accepts:
      A) KIND::pattern::location::message
      B) KIND::pattern::message   (legacy)
      C) anything else
    Also tries to infer location from message (e.g. "... at tb/u_dut/u_core: ...").
    """
    parts = sig.split("::")
    kind = pattern = location = msg = "-"

    if len(parts) >= 4:
        kind = parts[0] or "-"
        pattern = parts[1] or "-"
        location = parts[2] or "-"
        msg = "::".join(parts[3:]) or "-"
    elif len(parts) == 3:
        kind = parts[0] or "-"
        pattern = parts[1] or "-"
        location = "-"
        msg = parts[2] or "-"
    else:
        return "-", "-", "-", sig

    # try infer location from msg if missing
    if (not location or location == "-") and msg and msg != "-":
        m = re.search(r"(?i)\bat\s+([A-Za-z0-9_./$-]+)\s*:", msg)
        if m:
            location = m.group(1).strip().strip(" .:/") or "-"

    return kind, pattern, location, msg

def _knobs_now(params: dict) -> dict:
    return {
        "tail_event_window": int(params["tail_event_window"]),
        "top_n": int(params["top_n"]),
        "sketch_top_n": int(params["sketch_top_n"]),
        "prefix_levels": int(params["prefix_levels"]),
    }

HTML_TEMPLATE = """\
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width,initial-scale=1" />
  <title>vtriage report</title>
  <style>
    :root {
      --bg: #0b0d12;
      --panel: #111523;
      --muted: #aab2c0;
      --text: #e8ecf3;
      --border: rgba(255,255,255,.08);
      --ok: #3ddc97;
      --bad: #ff5c5c;
      --warn: #ffcc66;
      --mono: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace;
      --sans: ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, Helvetica, Arial, "Apple Color Emoji","Segoe UI Emoji";
    }
    body { margin: 0; background: var(--bg); color: var(--text); font-family: var(--sans); }
    a { color: #8ab4ff; text-decoration: none; }
    a:hover { text-decoration: underline; }
    .wrap { max-width: 1100px; margin: 0 auto; padding: 24px; }
    .top { display: flex; gap: 16px; align-items: flex-start; justify-content: space-between; flex-wrap: wrap; }
    .title { font-size: 22px; font-weight: 700; letter-spacing: .2px; }
    .sub { margin-top: 6px; color: var(--muted); font-family: var(--mono); font-size: 13px; }
    .cards { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 12px; margin-top: 16px; }
    .card { background: var(--panel); border: 1px solid var(--border); border-radius: 14px; padding: 14px; }
    .k { font-size: 12px; color: var(--muted); text-transform: uppercase; letter-spacing: .12em; }
    .v { margin-top: 6px; font-size: 22px; font-weight: 700; }
    .v.ok { color: var(--ok); }
    .v.bad { color: var(--bad); }
    .v.warn { color: var(--warn); }
    .section { margin-top: 22px; }
    .section h2 { font-size: 16px; margin: 0 0 10px 0; color: #d9def0; }
    .cluster { background: var(--panel); border: 1px solid var(--border); border-radius: 14px; padding: 14px; margin-bottom: 12px; }
    .cluster-head { display: flex; gap: 10px; align-items: baseline; justify-content: space-between; flex-wrap: wrap; }
    .cluster-title { font-size: 15px; font-weight: 700; }
    .pill { font-family: var(--mono); font-size: 12px; padding: 3px 8px; border-radius: 999px; border: 1px solid var(--border); color: var(--muted); }
    .grid { display: grid; grid-template-columns: 160px 1fr; gap: 8px 12px; margin-top: 10px; }
    .lbl { color: var(--muted); font-size: 12px; }
    .val { font-family: var(--mono); font-size: 12.5px; word-break: break-word; }
    details { margin-top: 10px; }
    summary { cursor: pointer; color: #cbd4ff; font-size: 13px; }
    pre { margin: 10px 0 0 0; padding: 12px; background: rgba(255,255,255,.03); border: 1px solid var(--border); border-radius: 12px; overflow: auto; font-family: var(--mono); font-size: 12px; line-height: 1.45; }
    .footer { margin-top: 18px; color: var(--muted); font-size: 12px; }
    @media (max-width: 900px) { .cards { grid-template-columns: 1fr; } .grid { grid-template-columns: 120px 1fr; } }
  </style>
</head>
<body>
  <div class="wrap">
    <div class="top">
      <div>
        <div class="title">vtriage report</div>
        <div class="sub">Artifact: {{ artifact }}</div>
      </div>
      <div class="sub">Generated: {{ generated_at }}</div>
    </div>

    <div class="cards">
      <div class="card">
        <div class="k">Total</div>
        <div class="v">{{ total }}</div>
      </div>
      <div class="card">
        <div class="k">PASS</div>
        <div class="v ok">{{ passes }}</div>
      </div>
      <div class="card">
        <div class="k">FAIL</div>
        <div class="v bad">{{ fails }}</div>
      </div>
    </div>

    <div class="section">
      <h2>Clusters</h2>

      {% if clusters|length == 0 %}
        <div class="cluster">
          <div class="cluster-title">No failures detected.</div>
          <div class="footer">Tip: confirm you pointed to an artifacts/run_... directory that contains tests/seed_*</div>
        </div>
      {% else %}
        {% for c in clusters %}
          <div class="cluster" id="c{{ loop.index }}">
            <div class="cluster-head">
              <div class="cluster-title">
                <a href="#c{{ loop.index }}">#{{ loop.index }}</a>
                &nbsp;{{ c.kind }} :: {{ c.pattern }}
              </div>
              <div class="pill">count: {{ c.count }}</div>
            </div>

            <div class="grid">
              <div class="lbl">location</div>
              <div class="val">{{ c.location }}</div>

              <div class="lbl">message</div>
              <div class="val">{{ c.message }}</div>

              <div class="lbl">seeds</div>
              <div class="val">{{ c.seeds }}</div>
            </div>

            {% if c.snippet %}
              <details>
                <summary>Show log snippet (example seed {{ c.example_seed }})</summary>
                <pre>{{ c.snippet }}</pre>
              </details>
            {% endif %}
            {% if c.subclusters and c.subclusters|length > 0 %}
              <details>
                <summary>Subclusters (by wave hash)</summary>
                <pre>
            {% for sc in c.subclusters %}
            {{ sc.wave_hash }}  ({{ sc.count }})  seeds: {{ sc.seeds }}
            {% endfor %}
                </pre>
              </details>
            {% endif %}
          </div>
          {% if c.top_tail and c.top_tail|length > 0 %}
            <details>
              <summary>Top suspect signals (tail window)</summary>
              <pre>
                {% for s in c.top_tail[:20] %}
                  {{ "%s  (%d)"|format(s[0], s[1]) }}
                {% endfor %}
              </pre>
            </details>
          {% endif %}

          {% if c.top_total and c.top_total|length > 0 %}
            <details>
              <summary>Top active signals (whole run)</summary>
              <pre>
                {% for s in c.top_total[:20] %}
                  {{ "%s  (%d)"|format(s[0], s[1]) }}
                {% endfor %}
              </pre>
            </details>
          {% endif %}
        {% endfor %}
      {% endif %}

    </div>

    <div class="footer">
      vtriage • local-first triage from logs + waveforms
    </div>
  </div>
</body>
</html>
"""


def render_html_report(
    *,
    artifact: str,
    generated_at: str,
    total: int,
    passes: int,
    fails: int,
    clusters: list[dict],
) -> str:
    env = Environment(
        loader=BaseLoader(),
        autoescape=select_autoescape(enabled_extensions=("html", "xml")),
    )
    tpl = env.from_string(HTML_TEMPLATE)
    return tpl.render(
        artifact=artifact,
        generated_at=generated_at,
        total=total,
        passes=passes,
        fails=fails,
        clusters=clusters,
    )

def _die(msg: str, code: int = 2) -> "typer.NoReturn":
    print(f"[red]error:[/red] {msg}")
    raise typer.Exit(code=code)


def _warn(msg: str) -> None:
    print(f"[yellow]warn:[/yellow] {msg}")


def validate_artifact_dir(
    artifact_dir: Path,
    *,
    strict: bool = True,
    strict_waves: bool = False,
) -> None:
    """
    Validates the artifact directory contract:

      artifact_dir/
        meta.json (optional)
        tests/
          seed_0001/
            log.txt
            fail.json (optional)
            waves.vcd (optional unless strict_waves)
    """

    raw = str(artifact_dir)

    if not artifact_dir:
        _die("artifact_dir is empty/None")

    if not artifact_dir.exists():
        # best-effort suggestion
        repo = Path(__file__).resolve().parents[2]
        art = repo / "artifacts"
        suggestion = ""
        if art.exists() and art.is_dir():
            runs = sorted([p for p in art.iterdir() if p.is_dir() and p.name.startswith("run_")], reverse=True)
            if runs:
                suggestion = "\n\nRecent runs:\n" + "\n".join(f"  - {p}" for p in runs[:3])

        _die(f"artifact_dir does not exist: {artifact_dir}{suggestion}")

    if not artifact_dir.is_dir():
        _die(f"artifact_dir is not a directory: {artifact_dir}")

    tests_dir = artifact_dir / "tests"
    if not tests_dir.exists() or not tests_dir.is_dir():
        _die(
            "invalid artifact_dir: missing tests/ directory.\n"
            f"expected: {tests_dir}\n"
            "tip: pass something like artifacts/run_YYYY-mm-dd_HH-MM-SS"
        )

    seed_dirs = sorted([p for p in tests_dir.iterdir() if p.is_dir() and p.name.startswith("seed_")])
    if not seed_dirs:
        _die(
            "invalid artifact_dir: tests/ exists but no seed_* directories found.\n"
            f"looked in: {tests_dir}"
        )

    # Check logs
    missing_logs = [p.name for p in seed_dirs if not (p / "log.txt").exists()]
    if missing_logs:
        msg = (
            f"missing log.txt in {len(missing_logs)} seed folders (showing up to 10): "
            + ", ".join(missing_logs[:10])
        )
        if strict:
            _die(msg)
        else:
            _warn(msg)
    if strict_waves:
        missing_waves = []
        for p in seed_dirs:
            # somente seeds FAIL devem ter waves (contrato mais realista)
            if (p / "fail.json").exists() and not (p / "waves.vcd").exists():
                missing_waves.append(p.name)

        if missing_waves:
            msg = (
                f"missing waves.vcd in {len(missing_waves)} FAIL seed folders (showing up to 10): "
                + ", ".join(missing_waves[:10])
            )
            _die(msg)

@app.command()
def init(path: Path = typer.Argument(Path("."), help="Diretório do projeto")):
    """Cria .vtriage.toml padrão."""
    cfg = path / ".vtriage.toml"
    if cfg.exists():
        print(f"[yellow]Já existe:[/yellow] {cfg}")
        raise typer.Exit(code=1)
    cfg.write_text(DEFAULT_TOML, encoding="utf-8")
    print(f"[green]Criado:[/green] {cfg}")


@app.command()
def analyze(
    artifact_dir: Optional[Path] = typer.Argument(
        None,
        help="Diretório artifacts/run_... ou 'latest' (ou use --latest)",
    ),
    out: Path = typer.Option(Path("report"), "--out", "-o", help="Pasta de saída do relatório"),
    lenient: bool = typer.Option(False, "--lenient", help="Mensagens mais amigáveis"),
    strict_waves: bool = typer.Option(False, "--strict-waves", help="Falha se seed FAIL não tiver waves.vcd"),
    latest: bool = typer.Option(False, "--latest", help="Usa o run_* mais recente de ./artifacts"),
    profile: str = typer.Option("", "--profile", "-p", help="Profile do .vtriage.toml (ex: quick, full)"),
    tail_event_window: Optional[int] = typer.Option(None, "--tail-event-window", help="Eventos do fim a considerar (ex: 50000)"),
    top_n: Optional[int] = typer.Option(None, "--top-n", help="Top N sinais (suspects)"),
    sketch_top_n: Optional[int] = typer.Option(None, "--sketch-top-n", help="Top N sinais para o hash/sketch"),
    prefix_levels: Optional[int] = typer.Option(None, "--prefix-levels", help="Níveis de expansão de prefix (ex: 2,3)"),
    reuse_index: bool = typer.Option(True, "--reuse-index/--no-reuse-index", help="Reusa run_index.json quando válido"),
    rebuild_index: bool = typer.Option(False, "--rebuild-index", help="Ignora run_index.json e recalcula"),
):
    out.mkdir(parents=True, exist_ok=True)

    repo_root = Path(__file__).resolve().parents[2]
    artifacts_root = repo_root / "artifacts"

    arg = (str(artifact_dir).strip().lower() if artifact_dir is not None else "")
    if latest or arg == "latest":
        lr = resolve_latest_run(repo_root, artifacts_root)
        if not lr:
            _die(f"nenhuma pasta run_* encontrada em: {artifacts_root}")
        artifact_dir = lr

    # Fonte única: resolve latest/alias + valida "cara de run"
    artifact_dir = _validate_artifact_dir_or_die(
        artifact_dir,
        repo_root=repo_root,
        artifacts_root=artifacts_root,
        lenient=lenient,
        latest=latest,
    )

    # Validação do contrato do artifact (logs + opcional waves)
    validate_artifact_dir(
        artifact_dir,
        strict=(not lenient),
        strict_waves=strict_waves,  # <- só se você implementar isso no validate_artifact_dir
    )

    cfg_path = repo_root / ".vtriage.toml"
    cfg = VtriageConfig.load(repo_root=repo_root, cfg_path=cfg_path)

    params = cfg.effective_analyze_params(profile=profile or None)

    if tail_event_window is not None:
        params["tail_event_window"] = int(tail_event_window)
    if top_n is not None:
        params["top_n"] = int(top_n)
    if sketch_top_n is not None:
        params["sketch_top_n"] = int(sketch_top_n)
    if prefix_levels is not None:
        params["prefix_levels"] = int(prefix_levels)

    print(
        f"analyze params: tail={params['tail_event_window']} "
        f"top_n={params['top_n']} sketch_top_n={params['sketch_top_n']} "
        f"prefix_levels={params['prefix_levels']}"
    )

    index = None
    if reuse_index and (not rebuild_index):
        idx = load_run_index(artifact_dir)
        if idx and idx.get("schema") == "run_index_v1":
            same_knobs = (idx.get("knobs") == _knobs_now(params))
            if same_knobs:
                current_fp = run_fingerprint(artifact_dir)
                if idx.get("fingerprint") == current_fp:
                    index = idx
                    print("[green]index[/green]: reuse run_index.json")
                else:
                    print("[yellow]index[/yellow]: fingerprint changed -> rebuild")
            else:
                print("[yellow]index[/yellow]: knobs changed -> rebuild")

    results = None
    clusters = None

    if index is not None:
        # ---------- REUSE INDEX ----------
        # constrói results/clusters mínimos a partir do index
        results = []
        clusters = {}

        # seeds -> results mínimos (só o que seu relatório usa)
        for s in index.get("seeds", []):
            # CaseResult mínimo: precisa seed, case_dir, passed, hit, signature, prefixes, wave_hash, top_tail/top_total (opcionais)
            # hit/snippet: a gente vai ler log do exemplar na hora do report, então hit pode ser None.
            case_dir = Path(s["case_dir"])
            results.append(
                CaseResult(
                    seed=int(s["seed"]),
                    case_dir=case_dir,
                    passed=bool(s["passed"]),
                    hit=None,
                    signature=str(s["signature"]),
                    wave_hash=s.get("wave_hash"),
                    prefixes=s.get("prefixes") or [],
                    # top_tail/top_total: se quiser, pode tentar carregar do wave_cache.json do exemplar depois
                    top_tail=[],
                    top_total=[],
                )
            )

        # clusters do index
        # index["clusters"] tem signature, seeds, subclusters
        seed_to_result = {r.seed: r for r in results}
        for c in index.get("clusters", []):
            sig = c["signature"]
            items = []
            for seed in c.get("seeds", []):
                r = seed_to_result.get(int(seed))
                if r:
                    items.append(r)
            clusters[sig] = items

        print("[green]index[/green]: report from run_index.json (no re-analyze)")

    else:
        # ---------- REBUILD ----------
        results, clusters = analyze_run(
            artifact_dir,
            tail_event_window=params["tail_event_window"],
            top_n=params["top_n"],
            sketch_top_n=params["sketch_top_n"],
            prefix_levels=params["prefix_levels"],
        )

    # Strict-waves extra (redundante se validate_artifact_dir já fizer certo, mas ok manter)
    if strict_waves:
        missing = [
            r.seed for r in results
            if (not r.passed) and not (r.case_dir / "waves.vcd").exists()
        ]
        if missing:
            missing_str = ", ".join(str(s) for s in missing[:30]) + (" ..." if len(missing) > 30 else "")
            print("[red]error[/red]: strict-waves: faltando waves.vcd em seeds FAIL:", missing_str)
            raise typer.Exit(code=3)

    total = len(results)
    fails = sum(1 for r in results if not r.passed)
    passes = total - fails

    md: list[str] = []
    md.append("# vtriage report")
    md.append("")
    md.append(f"Artifact: `{artifact_dir}`")
    md.append("")
    md.append(f"- Total: **{total}**")
    md.append(f"- PASS: **{passes}**")
    md.append(f"- FAIL: **{fails}**")
    md.append("")
    md.append("## Clusters (by signature)")
    md.append("")

    clusters_data: list[dict] = []

    if not clusters:
        md.append("_No failures detected._")
    else:
        for i, (sig, items) in enumerate(clusters.items(), start=1):
            kind, pattern, location, msg = _split_signature(sig)
            subs = subcluster_by_wave_hash(items)

            ex = items[0]
            lines = _read_lines(ex.case_dir / "log.txt")

            loc = location
            if loc == "-" or not loc:
                loc = extract_location_from_lines(lines) or "-"

            prefixes = ex.prefixes or []

            snippet_text = ""
            if ex.hit:
                snippet_text = "\n".join(snippet(lines, ex.hit.line_no))
            else:
                # fallback: mostra as primeiras linhas do log (ou as últimas)
                if lines:
                    snippet_text = "\n".join(lines[:6])

            seeds = ", ".join(str(r.seed) for r in items[:30])
            seeds_str = seeds + (" ..." if len(items) > 30 else "")

            md.append(f"### {i}. {kind} :: {pattern}")
            md.append(f"- count: **{len(items)}**")
            md.append(f"- seeds: {seeds_str}")
            md.append(f"- location: `{loc}`")
            md.append(f"- message: `{msg}`")
            if prefixes:
                md.append(f"- scope_prefix: `{prefixes[0]}`")
            md.append("")

            md.append("**Subclusters (by wave hash)**")
            for j, (wh, subitems) in enumerate(subs.items(), start=1):
                sub_seeds = ", ".join(str(r.seed) for r in subitems[:30])
                md.append(f"- {j}. `{wh}` — count **{len(subitems)}**, seeds: {sub_seeds}{' ...' if len(subitems) > 30 else ''}")
            md.append("")

            if snippet_text:
                md.append("```text")
                md.extend(snippet_text.splitlines())
                md.append("```")
                md.append("")

            if ex.top_tail is not None:
                md.append("**Top suspect signals (tail window)**")
                if ex.top_tail:
                    for name, c in ex.top_tail:
                        md.append(f"- `{name}` — **{c}**")
                else:
                    md.append("_no signals in scope_")
                md.append("")

            if ex.top_total is not None:
                md.append("**Top active signals (whole run)**")
                if ex.top_total:
                    for name, c in ex.top_total:
                        md.append(f"- `{name}` — **{c}**")
                else:
                    md.append("_no signals in scope_")
                md.append("")

            # ---- html data ----
            clusters_data.append(
                {
                    "kind": kind,
                    "pattern": pattern,
                    "location": loc,
                    "message": msg,
                    "count": len(items),
                    "seeds": seeds_str,
                    "example_seed": ex.seed,
                    "snippet": snippet_text,
                    "top_tail": ex.top_tail or [],
                    "top_total": ex.top_total or [],
                    "subclusters": [
                        {
                        "wave_hash": wh,
                        "count": len(subitems),
                        "seeds": ", ".join(str(r.seed) for r in subitems[:30]) + (" ..." if len(subitems) > 30 else ""),
                        }
                        for wh, subitems in subs.items()
                    ]
                }
            )
    (out / "report.md").write_text("\n".join(md) + "\n", encoding="utf-8")

    html = render_html_report(
        artifact=str(artifact_dir),
        generated_at=datetime.now().isoformat(timespec="seconds"),
        total=total,
        passes=passes,
        fails=fails,
        clusters=clusters_data,
    )
    (out / "report.html").write_text(html, encoding="utf-8")

    print("[green]OK[/green] relatório gerado em", out)

@app.command()
def run(
    seeds: int = typer.Option(20, "--seeds"),
    cmd: str = typer.Option("", "--cmd", help="Override do runner cmd"),
    workdir: Path = typer.Option(Path("."), "--workdir"),
    artifact_root: Path = typer.Option(Path("artifacts"), "--artifact-root"),
    run_id: str = typer.Option("", "--run-id"),
    vcd_path: str = typer.Option("build/waves.vcd", "--vcd-path"),
    out: Path = typer.Option(Path("report"), "--out", "-o"),
    no_analyze: bool = typer.Option(False, "--no-analyze"),
    strict_waves: bool = typer.Option(False, "--strict-waves"),
    lenient: bool = typer.Option(False, "--lenient"),
    profile: str = typer.Option("", "--profile", "-p", help="Nome do profile em .vtriage.toml (ex: quick, full)"),
):
    """
    Executa seeds e gera artifacts/run_... (cross-platform).
    Depois roda `vtriage analyze` no run gerado (a menos que --no-analyze).
    """
    repo_root = Path(__file__).resolve().parents[2]

    # Descobre qual TOML usar:
    # - Se workdir aponta pra um projeto (ex: examples/zipcpu), tenta workdir/.vtriage.toml
    # - Senão cai pra raiz
    workdir_abs = workdir.resolve()
    cfg_path = workdir_abs / ".vtriage.toml"
    if not cfg_path.exists():
        cfg_path = repo_root / ".vtriage.toml"
    cfg = VtriageConfig.load(repo_root=repo_root, cfg_path=cfg_path)

    try:
        p = cfg.get_profile(profile) if profile else {}
    except KeyError as e:
        print(f"[red]error[/red]: {e}")
        print("[yellow]hint[/yellow]: perfis disponíveis:", ", ".join(sorted((cfg.profiles or {}).keys())))
        raise typer.Exit(code=2)

    # Começa com defaults vindos do cfg
    eff = {
        "seeds": p.get("seeds", p.get("Seeds")),   # aceita Seeds por compat
        "cmd": p.get("cmd"),
        "workdir": p.get("workdir"),
        "artifact_root": p.get("artifact_root"),
        "out": p.get("out"),
        "vcd_path": p.get("vcd_path"),
        "strict_waves": p.get("strict_waves"),
        "lenient": p.get("lenient"),
        "no_analyze": p.get("no_analyze"),
    }

    # Normaliza: profile -> cfg -> defaults do typer
    # seeds
    if eff["seeds"] is None:
        eff["seeds"] = seeds
    # cmd
    if eff["cmd"] is None:
        eff["cmd"] = cfg.runner_cmd
    # workdir (IMPORTANTE: se vier do profile, é relativo ao TOML)
    if eff["workdir"] is None:
        eff["workdir"] = cfg.runner_workdir
    else:
        wd = Path(str(eff["workdir"]))
        eff["workdir"] = (cfg_path.parent / wd).resolve() if not wd.is_absolute() else wd.resolve()

    # artifact_root/out: normalmente global (relativo ao repo_root)
    if eff["artifact_root"] is None:
        eff["artifact_root"] = cfg.artifact_root
    else:
        ar = Path(str(eff["artifact_root"]))
        eff["artifact_root"] = (repo_root / ar).resolve() if not ar.is_absolute() else ar.resolve()

    if eff["out"] is None:
        eff["out"] = cfg.report_dir
    else:
        od = Path(str(eff["out"]))
        eff["out"] = (repo_root / od).resolve() if not od.is_absolute() else od.resolve()

    # vcd_path: relativo ao workdir
    if eff["vcd_path"] is None:
        eff["vcd_path"] = cfg.vcd_path

    # flags
    if eff["strict_waves"] is None:
        eff["strict_waves"] = strict_waves
    if eff["lenient"] is None:
        eff["lenient"] = lenient
    if eff["no_analyze"] is None:
        eff["no_analyze"] = no_analyze

    # Agora: CLI explícito SEMPRE vence (se usuário passou diferente do default)
    if seeds != 20:
        eff["seeds"] = seeds
    if cmd.strip():
        eff["cmd"] = cmd
    if str(workdir) != ".":
        eff["workdir"] = workdir_abs
    if str(artifact_root) != "artifacts":
        ar = artifact_root
        eff["artifact_root"] = (repo_root / ar).resolve() if not ar.is_absolute() else ar.resolve()
    if str(out) != "report":
        od = out
        eff["out"] = (repo_root / od).resolve() if not od.is_absolute() else od.resolve()
    if vcd_path != "build/waves.vcd":
        eff["vcd_path"] = vcd_path
    if strict_waves:
        eff["strict_waves"] = True
    if lenient:
        eff["lenient"] = True
    if no_analyze:
        eff["no_analyze"] = True

    runner = repo_root / "scripts" / "run.py"
    if not runner.exists():
        print(f"[red]error[/red]: runner not found: {runner}")
        raise typer.Exit(code=2)

    # Executa runner cross-platform
    args = [
        sys.executable, str(runner),
        "--seeds", str(int(eff["seeds"])),
        "--cmd", str(eff["cmd"]),
        "--workdir", str(eff["workdir"]),
        "--artifact-root", str(eff["artifact_root"]),
        "--run-id", run_id,
        "--vcd-path", str(eff["vcd_path"]),
    ]

    print("[cyan]config[/cyan]:", cfg_path)
    if profile:
        print("[cyan]profile[/cyan]:", profile)
    print("[cyan]run cmd[/cyan]:", " ".join(args))

    proc = subprocess.run(args, capture_output=True, text=True)

    run_dir = ""
    for line in (proc.stdout or "").splitlines():
        if line.startswith("RUN_DIR="):
            run_dir = line.split("=", 1)[1].strip()

    if not run_dir:
        print("[red]error[/red]: runner did not print RUN_DIR=")
        if proc.stdout:
            print(proc.stdout)
        if proc.stderr:
            print(proc.stderr)
        raise typer.Exit(code=3)

    print("[green]run[/green]:", run_dir)

    if eff["no_analyze"]:
        raise typer.Exit(code=proc.returncode)

    analyze_args = ["vtriage", "analyze", run_dir, "--out", str(eff["out"])]

    if profile:
        analyze_args += ["--profile", profile]

    if eff["strict_waves"]:
        analyze_args.append("--strict-waves")
    if eff["lenient"]:
        analyze_args.append("--lenient")

    print("[cyan]analyze cmd[/cyan]:", " ".join(map(str, analyze_args)))

    subprocess.run(analyze_args)
    raise typer.Exit(code=proc.returncode)

@app.command("list-runs")
def list_runs(
    limit: int = typer.Option(10, "--limit", "-n", help="Quantos runs mostrar"),
):
    """Lista runs recentes em ./artifacts (mostra total/pass/fail se tiver run_index.json)."""
    repo_root = Path(__file__).resolve().parents[2]
    artifacts_root = repo_root / "artifacts"

    runs = _list_runs(artifacts_root)[: max(1, int(limit))]

    if not runs:
        _die(f"nenhuma pasta run_* encontrada em: {artifacts_root}")

    print(f"[cyan]artifacts[/cyan]: {artifacts_root}")
    for r in runs:
        summ = _read_index_summary(r)
        if summ:
            total, passes, fails = summ
            print(f"- {r.name}  total={total} pass={passes} fail={fails}")
        else:
            print(f"- {r.name}  (no run_index.json)")

@app.command()
def open(
    run: Optional[Path] = typer.Argument(
        None,
        help="Run específico (path, nome run_..., ou 'latest'). Se omitido, usa latest.",
    ),
    latest: bool = typer.Option(False, "--latest", help="Abre o report do run mais recente"),
    report_path: str = typer.Option("report/report.html", "--report-path", help="Caminho do report dentro do repo"),
):
    """Abre o report HTML no navegador/app padrão."""
    repo_root = Path(__file__).resolve().parents[2]
    artifacts_root = repo_root / "artifacts"

    run_dir = _resolve_run_arg(repo_root=repo_root, artifacts_root=artifacts_root, run=run, latest=latest)
    if not run_dir:
        run_dir = resolve_latest_run(repo_root, artifacts_root)

    if not run_dir or not run_dir.exists():
        _die(f"run não encontrado. use: vtriage list-runs")

    # por padrão, abre o report global (repo/report/report.html)
    rp = (repo_root / report_path).resolve()
    if not rp.exists():
        _die(f"report não encontrado: {rp}\nrodar: vtriage analyze \"{run_dir}\" --out .\\report")

    print(f"[green]open[/green]: {rp}")
    _open_file(rp)

@app.command()
def open(
    run: Optional[Path] = typer.Argument(
        None,
        help="Run específico (path, nome run_..., ou 'latest'). Se omitido, usa latest.",
    ),
    latest: bool = typer.Option(False, "--latest", help="Abre o report do run mais recente"),
    report_path: str = typer.Option("report/report.html", "--report-path", help="Caminho do report dentro do repo"),
):
    """Abre o report HTML no navegador/app padrão."""
    repo_root = Path(__file__).resolve().parents[2]
    artifacts_root = repo_root / "artifacts"

    run_dir = _resolve_run_arg(repo_root=repo_root, artifacts_root=artifacts_root, run=run, latest=latest)
    if not run_dir:
        run_dir = resolve_latest_run(repo_root, artifacts_root)

    if not run_dir or not run_dir.exists():
        _die(f"run não encontrado. use: vtriage list-runs")

    # por padrão, abre o report global (repo/report/report.html)
    rp = (repo_root / report_path).resolve()
    if not rp.exists():
        _die(f"report não encontrado: {rp}\nrodar: vtriage analyze \"{run_dir}\" --out .\\report")

    print(f"[green]open[/green]: {rp}")
    _open_file(rp)

@app.command()
def where():
    """Mostra paths úteis (repo/artifacts/report/latest)."""
    repo_root = Path(__file__).resolve().parents[2]
    artifacts_root = repo_root / "artifacts"
    report_root = repo_root / "report"
    latest_run = resolve_latest_run(repo_root, artifacts_root)

    print(f"[cyan]repo[/cyan]:     {repo_root}")
    print(f"[cyan]artifacts[/cyan]: {artifacts_root}")
    print(f"[cyan]report[/cyan]:    {report_root}")
    print(f"[cyan]latest[/cyan]:    {latest_run if latest_run else '-'}")

@app.command()
def clean(
    keep: int = typer.Option(10, "--keep", "-k", help="Quantos runs mais recentes manter"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Não apaga nada; só mostra o que faria"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Não pergunta confirmação"),
    include_report: bool = typer.Option(False, "--report", help="Também limpa a pasta ./report"),
):
    """
    Limpa runs antigos em ./artifacts, mantendo os N mais recentes.
    Opcionalmente limpa ./report.
    """
    repo_root = Path(__file__).resolve().parents[2]
    artifacts_root = repo_root / "artifacts"
    report_root = repo_root / "report"

    runs = _list_runs(artifacts_root)
    if not runs:
        print(f"[yellow]warn[/yellow]: nenhum run_* em {artifacts_root}")
        if include_report and report_root.exists():
            print(f"[yellow]warn[/yellow]: ./report existe, mas sem runs para limpar.")
        raise typer.Exit(code=0)

    keep = max(0, int(keep))
    keep_set = set(runs[:keep])
    to_delete = [r for r in runs if r not in keep_set]

    print(f"[cyan]artifacts[/cyan]: {artifacts_root}")
    print(f"[cyan]runs[/cyan]: total={len(runs)} keep={keep} delete={len(to_delete)}")

    if not to_delete and not include_report:
        print("[green]ok[/green]: nada para limpar.")
        raise typer.Exit(code=0)

    if to_delete:
        print("\n[bold]Will delete:[/bold]")
        for r in to_delete[:50]:
            print(f"  - {r}")
        if len(to_delete) > 50:
            print(f"  ... (+{len(to_delete)-50} more)")

    if include_report:
        print(f"\n[bold]Report folder:[/bold] {report_root}")
        if report_root.exists():
            print("  - will delete all files under ./report")
        else:
            print("  - (does not exist)")

    if dry_run:
        print("\n[yellow]dry-run[/yellow]: nada foi apagado.")
        raise typer.Exit(code=0)

    if not yes:
        confirm = typer.confirm("Confirmar limpeza?")
        if not confirm:
            print("[yellow]aborted[/yellow]")
            raise typer.Exit(code=0)

    # delete runs
    for r in to_delete:
        try:
            shutil.rmtree(r)
        except Exception as e:
            print(f"[yellow]warn[/yellow]: falha ao remover {r}: {e}")

    # delete report folder contents
    if include_report and report_root.exists():
        for p in report_root.iterdir():
            try:
                if p.is_dir():
                    shutil.rmtree(p)
                else:
                    p.unlink()
            except Exception as e:
                print(f"[yellow]warn[/yellow]: falha ao remover {p}: {e}")

    print("[green]done[/green]")

@app.command("show-run")
def show_run(
    run: Optional[Path] = typer.Argument(
        None,
        help="Run (path, nome run_..., ou 'latest'). Se omitido, usa latest.",
    ),
    latest: bool = typer.Option(False, "--latest", help="Usa o run_* mais recente"),
    limit: int = typer.Option(10, "--limit", "-n", help="Quantos clusters mostrar"),
    as_json: bool = typer.Option(False, "--json", help="Imprime o run_index.json completo"),
):
    """Mostra resumo de um run usando run_index.json (se existir)."""
    repo_root = Path(__file__).resolve().parents[2]
    artifacts_root = repo_root / "artifacts"

    run_dir = _resolve_run_arg(repo_root=repo_root, artifacts_root=artifacts_root, run=run, latest=latest)
    if not run_dir:
        run_dir = resolve_latest_run(repo_root, artifacts_root)

    if not run_dir or not run_dir.exists():
        _die("run não encontrado. use: vtriage list-runs")

    idx = load_run_index(run_dir)
    if not idx:
        _die(f"run_index.json não encontrado em {run_dir}\nrode: vtriage analyze \"{run_dir}\"")

    if as_json:
        print(json.dumps(idx, indent=2, sort_keys=True))
        raise typer.Exit(code=0)

    summary = idx.get("summary") or {}
    knobs = idx.get("knobs") or {}
    gen = idx.get("generated_at") or "-"

    print(f"[cyan]run[/cyan]: {run_dir}")
    print(f"[cyan]generated_at[/cyan]: {gen}")
    print(f"[cyan]knobs[/cyan]: tail={knobs.get('tail_event_window')} top_n={knobs.get('top_n')} sketch_top_n={knobs.get('sketch_top_n')} prefix_levels={knobs.get('prefix_levels')}")
    print(f"[cyan]summary[/cyan]: total={summary.get('total')} pass={summary.get('passes')} fail={summary.get('fails')}")
    print("")

    clusters = idx.get("clusters") or []
    if not clusters:
        print("[green]ok[/green]: no clusters")
        raise typer.Exit(code=0)

    limit = max(1, int(limit))
    print(f"[bold]Top clusters (limit={limit})[/bold]")
    for i, c in enumerate(clusters[:limit], start=1):
        sig = c.get("signature", "-")
        count = c.get("count", 0)
        seeds = c.get("seeds", [])
        seeds_str = ", ".join(str(s) for s in seeds[:15]) + (" ..." if len(seeds) > 15 else "")
        print(f"{i:02d}. count={count}  seeds={seeds_str}")
        print(f"    sig: {sig}")

        subs = c.get("subclusters") or []
        if subs:
            top_sub = subs[0]
            wh = top_sub.get("wave_hash", "-")
            sc = top_sub.get("count", 0)
            print(f"    top subcluster: {wh} (count={sc})")
        print("")

@app.command("open-run")
def open_run(
    run: Optional[Path] = typer.Argument(
        None,
        help="Run (path, nome run_..., ou 'latest'). Se omitido, usa latest.",
    ),
    latest: bool = typer.Option(False, "--latest", help="Usa o run_* mais recente"),
    out: Path = typer.Option(Path("report"), "--out", "-o", help="Pasta do relatório (default: ./report)"),
    profile: str = typer.Option("", "--profile", "-p", help="Profile do .vtriage.toml (ex: quick, full)"),
    strict_waves: bool = typer.Option(False, "--strict-waves", help="Falha se seed FAIL não tiver waves.vcd"),
    lenient: bool = typer.Option(False, "--lenient", help="Mensagens mais amigáveis"),
    rebuild_index: bool = typer.Option(False, "--rebuild-index", help="Força recalcular (ignora run_index.json)"),
):
    """Gera (se necessário) e abre o report HTML do run."""
    repo_root = Path(__file__).resolve().parents[2]
    artifacts_root = repo_root / "artifacts"

    run_dir = _resolve_run_arg(repo_root=repo_root, artifacts_root=artifacts_root, run=run, latest=latest)
    if not run_dir:
        run_dir = resolve_latest_run(repo_root, artifacts_root)

    if not run_dir or not run_dir.exists():
        _die("run não encontrado. use: vtriage list-runs")

    # resolve out relative ao repo
    out_dir = (repo_root / out).resolve() if not out.is_absolute() else out.resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    report_html = out_dir / "report.html"

    # se não existe, roda analyze
    if not report_html.exists():
        print(f"[yellow]info[/yellow]: report não encontrado em {report_html}, rodando analyze...")

        cmd = ["vtriage", "analyze", str(run_dir), "--out", str(out_dir), "--reuse-index"]
        if rebuild_index:
            cmd.append("--rebuild-index")
        if profile:
            cmd += ["--profile", profile]
        if strict_waves:
            cmd.append("--strict-waves")
        if lenient:
            cmd.append("--lenient")

        print("[cyan]analyze cmd[/cyan]:", " ".join(cmd))
        r = subprocess.run(cmd)
        if r.returncode != 0:
            raise typer.Exit(code=r.returncode)

        if not report_html.exists():
            _die(f"analyze rodou, mas report.html não apareceu em: {report_html}")

    print(f"[green]open[/green]: {report_html}")
    _open_file(report_html)


@app.command()
def doctor(
    workdir: Path = typer.Option(Path("."), "--workdir", help="Diretório do projeto (onde procurar .vtriage.toml)"),
    latest: bool = typer.Option(True, "--latest/--no-latest", help="Checa também o run mais recente"),
):
    """Verifica configuração, paths e permissões (diagnóstico rápido)."""
    repo_root = Path(__file__).resolve().parents[2]
    artifacts_root = repo_root / "artifacts"
    report_root = repo_root / "report"
    runner = repo_root / "scripts" / "run.py"

    print(f"[cyan]repo[/cyan]: {repo_root}")
    print(f"[cyan]python[/cyan]: {sys.executable}")
    print(f"[cyan]pyver[/cyan]: {sys.version.split()[0]}")
    print("")

    # runner
    if runner.exists():
        print(f"[green]ok[/green] runner: {runner}")
    else:
        print(f"[red]fail[/red] runner missing: {runner}")

    # config discovery
    wd_abs = workdir.resolve()
    cfg_candidates = [wd_abs / ".vtriage.toml", repo_root / ".vtriage.toml"]
    cfg_path = None
    for c in cfg_candidates:
        if c.exists():
            cfg_path = c
            break

    if cfg_path:
        print(f"[green]ok[/green] config: {cfg_path}")
        try:
            cfg = VtriageConfig.load(repo_root=repo_root, cfg_path=cfg_path)
            print(f"  artifact_root: {cfg.artifact_root}")
            print(f"  report_dir:    {cfg.report_dir}")
            print(f"  runner.cmd:    {cfg.runner_cmd}")
            print(f"  runner.workdir:{cfg.runner_workdir}")
            if cfg.profiles:
                print(f"  profiles:      {', '.join(sorted(cfg.profiles.keys()))}")
        except Exception as e:
            print(f"[red]fail[/red] config parse: {e}")
    else:
        print("[yellow]warn[/yellow] .vtriage.toml não encontrado (nem no workdir nem na raiz).")

    print("")

    # writable dirs
    def _check_writable_dir(p: Path, label: str):
        try:
            p.mkdir(parents=True, exist_ok=True)
            test = p / ".vtriage_write_test"
            test.write_text("ok", encoding="utf-8")
            test.unlink()
            print(f"[green]ok[/green] writable {label}: {p}")
        except Exception as e:
            print(f"[red]fail[/red] not writable {label}: {p} ({e})")

    _check_writable_dir(artifacts_root, "artifacts")
    _check_writable_dir(report_root, "report")

    print("")

    if latest:
        lr = resolve_latest_run(repo_root, artifacts_root)
        if not lr:
            print("[yellow]warn[/yellow] nenhum run_* encontrado em ./artifacts")
            raise typer.Exit(code=0)

        print(f"[cyan]latest run[/cyan]: {lr}")
        idx = (lr / "run_index.json")
        if idx.exists():
            try:
                data = json.loads(idx.read_text(encoding="utf-8"))
                s = data.get("summary") or {}
                print(f"[green]ok[/green] run_index.json (total={s.get('total')} pass={s.get('passes')} fail={s.get('fails')})")
            except Exception as e:
                print(f"[yellow]warn[/yellow] run_index.json inválido: {e}")
        else:
            print("[yellow]warn[/yellow] run_index.json não existe (rode analyze para gerar)")

        # quick waves check: mostra até 5 FAIL seeds sem waves
        tests = lr / "tests"
        if tests.exists():
            missing = []
            for d in sorted([p for p in tests.iterdir() if p.is_dir() and p.name.startswith("seed_")]):
                if (d / "fail.json").exists() and not (d / "waves.vcd").exists():
                    missing.append(d.name)
            if missing:
                print(f"[yellow]warn[/yellow] FAIL seeds sem waves.vcd (até 5): {', '.join(missing[:5])}")
            else:
                print("[green]ok[/green] waves.vcd presentes nos FAILs (ou não há FAILs)")
