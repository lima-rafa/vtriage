import os, random, sys
from pathlib import Path

# Entradas
seed = int(os.environ.get("SEED", "1"))
out_dir = Path(os.environ.get("BUILD_DIR", "build"))
waves = out_dir / "waves.vcd"

random.seed(seed)
out_dir.mkdir(parents=True, exist_ok=True)

# Gera um VCD mínimo
waves.write_text(
"""$date today $end
$version fake $end
$timescale 1ns $end
$scope module tb $end
$var wire 1 ! tb.u_dut.u_core.a $end
$upscope $end
$enddefinitions $end
#0
0!
#10
1!
#20
0!
""",
encoding="utf-8"
)

# Falha em ~30% das seeds para simular bugs e gerar clusters
if random.random() < 0.3:
    print("%Error: Assertion failed at tb/u_dut/u_core: mismatch expected got", file=sys.stderr)
    print("opening /home/user/proj/build/out.log", file=sys.stderr)
    sys.exit(1)

print("PASS")
sys.exit(0)
