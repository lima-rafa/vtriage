# scripts/run.py
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
from datetime import datetime
from pathlib import Path


def _now_run_id() -> str:
    return "run_" + datetime.now().strftime("%Y-%m-%d_%H-%M-%S")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", type=int, default=20)
    ap.add_argument("--cmd", type=str, required=True, help='Ex: "python scripts/sim_harness.py" ou "make sim SEED={seed}"')
    ap.add_argument("--workdir", type=str, default=".")
    ap.add_argument("--artifact-root", type=str, default="artifacts")
    ap.add_argument("--run-id", type=str, default="")
    ap.add_argument("--vcd-path", type=str, default="build/waves.vcd")
    ap.add_argument("--build-dir", type=str, default="build", help="Exportado como BUILD_DIR")
    ap.add_argument("--cfg-path", default="", help="Path do .vtriage.toml usado no vtriage run (para reprodutibilidade)")
    args = ap.parse_args()

    repo_root = Path.cwd()
    workdir = (Path(args.workdir).resolve())
    artifact_root = Path(args.artifact_root)
    if not artifact_root.is_absolute():
        artifact_root = (repo_root / artifact_root).resolve()

    run_id = args.run_id.strip() or _now_run_id()
    run_dir = artifact_root / run_id

    tests_dir = run_dir / "tests"
    tests_dir.mkdir(parents=True, exist_ok=True)

    meta = {
        "run_id": run_id,
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "workdir": str(workdir),
        "cmd_template": args.cmd,
        "vcd_path": args.vcd_path,
        "build_dir": args.build_dir,
        "cfg_path": args.cfg_path or None,
    }
    (run_dir / "meta.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")

    fail_count = 0

    for seed in range(1, args.seeds + 1):
        seed_dir = tests_dir / f"seed_{seed:04d}"
        seed_dir.mkdir(parents=True, exist_ok=True)

        log_path = seed_dir / "log.txt"
        fail_path = seed_dir / "fail.json"
        waves_dst = seed_dir / "waves.vcd"

        # comando com {seed}
        real_cmd = args.cmd.replace("{seed}", str(seed))

        # remove waves antigo do workdir (evita copiar lixo)
        vcd_src = workdir / Path(args.vcd_path)
        if vcd_src.exists():
            try:
                vcd_src.unlink()
            except Exception:
                pass

        env = os.environ.copy()
        env["SEED"] = str(seed)
        env["BUILD_DIR"] = args.build_dir

        # roda comando (shell=True pra aceitar string como no PowerShell)
        with log_path.open("w", encoding="utf-8", errors="replace") as f:
            proc = subprocess.run(
                real_cmd,
                cwd=str(workdir),
                shell=True,
                stdout=f,
                stderr=subprocess.STDOUT,
                env=env,
            )

        rc = int(proc.returncode)

        # copia waves se gerou
        if vcd_src.exists():
            try:
                shutil.copyfile(vcd_src, waves_dst)
            except Exception:
                # não quebra a run por erro de copy
                pass

        if rc != 0:
            fail_count += 1
            fail_path.write_text(json.dumps({"seed": seed, "exit_code": rc}, indent=2), encoding="utf-8")

    # printa caminho do run (pra copy/paste)
    print(f"RUN_DIR={run_dir}")
    print(str(run_dir))

    return 1 if fail_count > 0 else 0


if __name__ == "__main__":
    raise SystemExit(main())
