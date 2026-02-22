# scripts/oss_clone.py
from __future__ import annotations

import argparse
import subprocess
from pathlib import Path

TARGETS = {
    "zipcpu": ("https://github.com/ZipCPU/zipcpu.git", "master"),
    # próximos:
    "litex": ("https://github.com/enjoy-digital/litex.git", "master"),
    "vexriscv": ("https://github.com/SpinalHDL/VexRiscv.git", "master"),
}

def run(cmd: list[str], cwd: Path | None = None) -> None:
    print("[cmd]", " ".join(cmd))
    subprocess.run(cmd, cwd=str(cwd) if cwd else None, check=True)

def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--target", required=True, choices=["zipcpu", "litex", "vexriscv"])
    ap.add_argument("--dest", default="third_party", help="Pasta base para clonar")
    args = ap.parse_args()

    repo_url, branch = TARGETS[args.target]
    base = Path(args.dest).resolve()
    base.mkdir(parents=True, exist_ok=True)
    dest = base / args.target

    if dest.exists():
        print("[info] already exists:", dest)
        # tenta atualizar
        try:
            run(["git", "fetch", "--all"], cwd=dest)
            run(["git", "checkout", branch], cwd=dest)
            run(["git", "pull", "--ff-only"], cwd=dest)
        except Exception as e:
            print("[warn] failed to update repo, continuing:", e)
        return

    run(["git", "clone", "--depth", "1", "--branch", branch, repo_url, str(dest)])
    print("[ok] cloned:", dest)

if __name__ == "__main__":
    main()
