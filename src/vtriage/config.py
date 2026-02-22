# src/vtriage/config.py
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

try:
    import tomllib  # py3.11+
except ModuleNotFoundError:
    import tomli as tomllib  # fallback

@dataclass(frozen=True)
class VtriageConfig:
    repo_root: Path
    artifact_root: Path
    report_dir: Path
    runner_cmd: str
    runner_workdir: Path
    vcd_path: str

    # ---- NEW: waveform knobs ----
    waveform_tail_event_window: int
    waveform_top_n: int
    waveform_sketch_top_n: int
    waveform_prefix_expand_levels: int

    # ---- NEW: report knobs ----
    report_include_top_signals: int

    # ---- NEW: profiles ----
    profiles: dict[str, dict[str, Any]]

    @staticmethod
    def load(*, repo_root: Path, cfg_path: Path | None = None) -> "VtriageConfig":
        cfg_path = cfg_path or (repo_root / ".vtriage.toml")

        data: dict[str, Any] = {}
        if cfg_path.exists():
            data = tomllib.loads(cfg_path.read_text(encoding="utf-8"))

        project = data.get("project", {})
        runner = data.get("runner", {})
        waveform = data.get("waveform", {})
        report = data.get("report", {})
        profiles = data.get("profiles") or {}

        artifact_root = project.get("artifact_root", "artifacts")
        report_dir = project.get("report_dir", "report")

        artifact_root = (repo_root / artifact_root).resolve() if not Path(artifact_root).is_absolute() else Path(artifact_root)
        report_dir = (repo_root / report_dir).resolve() if not Path(report_dir).is_absolute() else Path(report_dir)

        runner_cmd = runner.get("cmd", "python scripts/sim_harness.py")
        runner_workdir = runner.get("workdir", ".")
        runner_workdir = (repo_root / runner_workdir).resolve() if not Path(runner_workdir).is_absolute() else Path(runner_workdir)
        vcd_path = runner.get("vcd_path", "build/waves.vcd")

        # waveform defaults
        waveform_tail_event_window = int(waveform.get("tail_event_window", 50_000))
        waveform_top_n = int(waveform.get("top_n", 20))
        waveform_sketch_top_n = int(waveform.get("sketch_top_n", 12))
        waveform_prefix_expand_levels = int(waveform.get("prefix_expand_levels", 2))

        # report defaults
        report_include_top_signals = int(report.get("include_top_signals", waveform_top_n))

        return VtriageConfig(
            repo_root=repo_root,
            artifact_root=artifact_root,
            report_dir=report_dir,
            runner_cmd=runner_cmd,
            runner_workdir=runner_workdir,
            vcd_path=vcd_path,
            waveform_tail_event_window=waveform_tail_event_window,
            waveform_top_n=waveform_top_n,
            waveform_sketch_top_n=waveform_sketch_top_n,
            waveform_prefix_expand_levels=waveform_prefix_expand_levels,
            report_include_top_signals=report_include_top_signals,
            profiles=profiles,
        )

    def get_profile(self, name: str) -> dict[str, Any]:
        if not name:
            return {}
        p = (self.profiles or {}).get(name)
        if not p:
            raise KeyError(f"profile '{name}' not found")
        return p

    def effective_analyze_params(self, profile: str | None = None) -> dict[str, int]:
        """
        Retorna parâmetros efetivos do analyze, já aplicando overrides de profile.
        Precedência aqui: profile > base.
        (CLI explícito pode sobrescrever depois, no cli.py)
        """
        # base (config global)
        tail_event_window = self.waveform_tail_event_window
        top_n = self.waveform_top_n
        sketch_top_n = self.waveform_sketch_top_n
        prefix_levels = self.waveform_prefix_expand_levels

        if profile:
            p = self.get_profile(profile)

            wf = (p.get("waveform") or {})
            # waveform
            if "tail_event_window" in wf:
                tail_event_window = int(wf["tail_event_window"])
            if "top_n" in wf:
                top_n = int(wf["top_n"])
            if "sketch_top_n" in wf:
                sketch_top_n = int(wf["sketch_top_n"])
            if "prefix_expand_levels" in wf:
                prefix_levels = int(wf["prefix_expand_levels"])

            # opcional: profile.report.include_top_signals (se você quiser)
            rpt = (p.get("report") or {})
            if "include_top_signals" in rpt:
                top_n = int(rpt["include_top_signals"])

        return {
            "tail_event_window": tail_event_window,
            "top_n": top_n,
            "sketch_top_n": sketch_top_n,
            "prefix_levels": prefix_levels,
        }
