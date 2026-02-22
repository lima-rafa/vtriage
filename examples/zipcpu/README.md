# vtriage example (Windows-friendly harness)

Este exemplo NÃO usa make. Ele roda um harness em Python que:
- gera um VCD mínimo (build/waves.vcd)
- falha em ~30% das seeds (para criar clusters)

## Rodar
No PowerShell, a partir da raiz do repo vtriage:

```powershell
cd .\examples\zipcpu
..\..\scripts\ci_run.ps1 -Seeds 20 -Cmd "python scripts/sim_harness.py" -Workdir . -VcdPath "build\waves.vcd"