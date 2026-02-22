# scripts/oss_run.py
from __future__ import annotations

import argparse
import os
import subprocess
from datetime import datetime
from pathlib import Path

def run_case(cmd: str, workdir: Path, log_path: Path, seed: int) -> int:
    env = os.environ.copy()
    env["SEED"] = str(seed)
    env["BUILD_DIR"] = "build"

    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("w", encoding="utf-8", errors="replace") as f:
        p = subprocess.run(
            cmd,
            cwd=str(workdir),
            shell=True,
            stdout=f,
            stderr=subprocess.STDOUT,
            env=env,
        )
    return int(p.returncode)

def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--target", required=True, choices=["zipcpu", "litex", "vexriscv"])
    ap.add_argument("--seeds", type=int, default=20)
    ap.add_argument("--artifact-root", default="artifacts")
    args = ap.parse_args()

    repo_root = Path(__file__).resolve().parents[1]
    artifact_root = (repo_root / args.artifact_root).resolve()

    # por enquanto: smoke "zipcpu" roda o harness do seu example
    if args.target == "zipcpu":
        workdir = repo_root / "examples" / "zipcpu"
        cmd = "python scripts/sim_harness.py"
        vcd_rel = Path("build") / "waves.vcd"
    else:
        raise SystemExit("target not implemented yet (we will add litex/vexriscv next)")

    run_id = "run_" + datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    run_dir = artifact_root / run_id
    tests_dir = run_dir / "tests"
    tests_dir.mkdir(parents=True, exist_ok=True)

    # meta.json mínimo
    meta = {
        "run_id": run_id,
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "target": args.target,
        "workdir": str(workdir),
        "cmd": cmd,
        "seeds": args.seeds,
    }
    (run_dir / "meta.json").write_text(__import__("json").dumps(meta, indent=2), encoding="utf-8")

    fails = 0
    for seed in range(1, args.seeds + 1):
        case_dir = tests_dir / f"seed_{seed:04d}"
        case_dir.mkdir(parents=True, exist_ok=True)

        log_path = case_dir / "log.txt"

        # remove VCD antigo pra não copiar lixo
        vcd_src = workdir / vcd_rel
        if vcd_src.exists():
            vcd_src.unlink()

        rc = run_case(cmd, workdir, log_path, seed)

        # copia waves se gerou
        if vcd_src.exists():
            (case_dir / "waves.vcd").write_bytes(vcd_src.read_bytes())

        if rc != 0:
            fails += 1
            (case_dir / "fail.json").write_text(f'{{"seed": {seed}, "exit_code": {rc}}}\n', encoding="utf-8")

    outdir = repo_root / "scripts" / "out"
    outdir.mkdir(parents=True, exist_ok=True)
    (outdir / "run_dir.txt").write_text(str(run_dir), encoding="utf-8")

    print("RUN_DIR=" + str(run_dir))
    print(f"[done] failures: {fails}/{args.seeds}")

    # CI: se houver falha, retorna 1 (mas artifacts existem)
    raise SystemExit(1 if fails > 0 else 0)

if __name__ == "__main__":
    main()
