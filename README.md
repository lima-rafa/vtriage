# vtriage

CLI local (Windows/Linux) para triagem de falhas em verificação/debug de RTL/FPGA usando logs + waveforms (VCD/FST).
MVP: Verilator + VCD, clustering determinístico, relatório Markdown/HTML.

## Quickstart (dev)
`powershell
python -m venv .venv
.\.venv\Scripts\activate
python -m pip install -U pip
python -m pip install -e .
vtriage --help

## runs
# Como usar (na raiz)
powershell -ExecutionPolicy Bypass -File .\scripts\run_and_analyze.ps1
# Ou customizando:
powershell -ExecutionPolicy Bypass -File .\scripts\run_and_analyze.ps1 -Seeds 50 -Workdir .\examples\zipcpu -Cmd "python scripts/sim_harness.py" -VcdPath "build\waves.vcd"
# Se não quiser abrir o navegador:
powershell -ExecutionPolicy Bypass -File .\scripts\run_and_analyze.ps1 -Seeds 50 -Workdir .\examples\zipcpu -Cmd "python scripts/sim_harness.py" -VcdPath "build\waves.vcd"


# run automático
powershell -ExecutionPolicy Bypass -File .\scripts\run_generate.ps1 -Seeds 20 -Workdir .\examples\zipcpu

# run com ID custom (fica fácil comparar)
powershell -ExecutionPolicy Bypass -File .\scripts\run_generate.ps1 -Seeds 50 -Workdir .\examples\zipcpu -RunId "run_zipcpu_50seeds_$(Get-Date -Format yyyyMMdd_HHmmss)"
# só lista e pede você escolher via parâmetros
powershell -ExecutionPolicy Bypass -File .\scripts\run_analyze.ps1

# analisa o mais novo
powershell -ExecutionPolicy Bypass -File .\scripts\run_analyze.ps1 -Latest

# analisa um específico pelo índice mostrado
powershell -ExecutionPolicy Bypass -File .\scripts\run_analyze.ps1 -Pick 2

# Analisar o mais novo (sem pensar)
powershell -ExecutionPolicy Bypass -File .\scripts\pick_run.ps1 -Latest
# Escolher por índice (mostra a lista e analisa o 2)
powershell -ExecutionPolicy Bypass -File .\scripts\pick_run.ps1 -Pick 2
# Interativo (digita o índice)
powershell -ExecutionPolicy Bypass -File .\scripts\pick_run.ps1 -Interactive
