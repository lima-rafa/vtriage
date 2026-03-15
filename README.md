

# vtriage



CLI local-first (Windows/Linux) para triagem determinística de falhas em verificação/debug de RTL/FPGA usando **logs + waveforms** (VCD/FST).



**MVP atual**

- Runner cross-platform (`vtriage run`) + Analyzer (`vtriage analyze`)

- Clustering determinístico por assinatura (log) + **subclusters por `wave_hash`**

- Relatório **Markdown + HTML**

- Cache por seed: `wave_cache.json`

- Index por run: `run_index.json` (com `--reuse-index/--rebuild-index`)

- GitHub Actions: CI do projeto + **OSS validate** (ZipCPU/LiteX/VexRiscv)


Repo: `lima-rafa/vtriage`

---
## Instalação (dev)

#### Windows (PowerShell)

~~~powershell

python -m venv .venv

.\.venv\Scripts\Activate.ps1

python -m pip install -U pip

python -m pip install -e .

vtriage --help
~~~

#### Linux/macOS
~~~bash
python3 -m venv .venv

source .venv/bin/activate

python -m pip install -U pip

python -m pip install -e .

vtriage --help
~~~


## Quickstart (5 comandos)

>Rode na raiz do repo.

1. Run (gera artifacts)
```powershell
vtriage run --workdir ./examples/zipcpu --profile quick
```

2. Analyze o último run (gera report/)
```powershell
vtriage analyze --latest --out ./report
```

3. Veja resumo do último run (usa run_index.json)
```powershell
vtriage show-run latest --limit 10
```

4. Rebuild do index (força re-análise)
```powershell
vtriage analyze --latest --out ./report --rebuild-index
```

5. Abrir report.html automaticamente
```powershell
vtriage analyze --latest --out ./report --open
```
  ---

## Saídas geradas (contrato)

Um run típico fica assim:
* artifacts/run_YYYY-MM-DD_HH-MM-SS/
	- run_index.json (schema run_index_v1)
	- tests/seed_0001/
		- log.txt
		- fail.json (se FAIL)
		- waves.vcd (se houver / se FAIL normalmente)
		- wave_cache.json (cache do VCD: hash + top signals + meta)

E o relatório:
* report/report.md
* report/report.html
* report/report.json (quando `--json`)
---

## Exit codes (CI-friendly)

 - 0 = tudo PASS
 - 1 = análise ok, mas houve FAIL
 - 2 = erro de uso/args inválidos
 - 3 = contrato inválido/artifact corrompido (faltando log, etc.)
 - 4 = erro interno inesperado (bug)
---

## GitHub Actions (OSS validate)

O workflow oss-validate.yml roda manualmente via workflow_dispatch com target:

 - zipcpu
 - litex
 - vexriscv
 - all

Ele executa vtriage run -> vtriage analyze -> upload report/artifacts.

---

## (Opcional) Rodar via scripts PowerShell (Windows)

Você também pode usar os scripts do diretório scripts/:

### Run + Analyze (atalho)
```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\run_and_analyze.ps1
```
### Custom
```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\run_and_analyze.ps1 `
	-Seeds 50 `
	-Workdir .\examples\zipcpu `
	-Cmd "python scripts/sim_harness.py" `
	-VcdPath "build\waves.vcd"
```
### Só run (gera artifacts)
```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\run_generate.ps1 -Seeds 20 -Workdir .\examples\zipcpu
```
### Só analyze
```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\run_analyze.ps1 -Latest
```
---
## Config discovery (.vtriage.toml) — regra determinística

Objetivo: evitar confusão sobre “qual TOML está valendo”.

### Regra do vtriage run

-   Se existir workdir/.vtriage.toml, usa ele.


-   Senão, usa repo_root/.vtriage.toml.



### Regra do vtriage analyze

-   Usa repo_root/.vtriage.toml como base.


-   Se existir artifact_dir/.vtriage.toml, ele pode ser usado (apenas se você optar por essa regra).


-   Em --debug, o CLI imprime os candidatos e qual foi selecionado.



Observação: se você quer “um único comportamento simples”, recomendo manter:
analyze sempre usa o TOML da raiz do repo, e run pode usar TOML do workdir quando existir.

---

## Troubleshooting

### 1) `index: knobs changed -> rebuild`

Você mudou parâmetros que afetam a análise (ex: `--top-n`, `--tail-event-window`, `--sketch-top-n`, `--prefix-levels`, `--max-bytes`, `--tail-bytes`, `--max-events`).

Isso **invalida o run_index.json** e o vtriage recalcula automaticamente.

**Como resolver:**

- Rode normalmente (vai rebuild sozinho), ou force:

```bash
vtriage analyze --latest --rebuild-index
```
----------

### 2) index: fingerprint changed -> rebuild

Algum arquivo do run mudou:

-   log.txt
-   fail.json
-   waves.vcd (nos FAIL)

Isso faz o índice ser considerado “stale” e será recalculado.

Como resolver:
-   Normalmente: nada. É comportamento correto.
-   Se você alterou arquivos manualmente, gere outro run.
---

### 3) `--strict-waves` falhou

Significa que existe seed FAIL sem waves.vcd.

Como resolver:
-   Rode sem `--strict-waves` (tolerante), ou
-   Ajuste seu runner/sim para sempre gerar wave quando der FAIL.
---

### 4) VCD grande / memória alta / truncamento

O analyzer tem guardrails para não explodir RAM:
-   `--max-bytes` (limite p/ ler inteiro)
-   `--tail-byte`s (se truncar, lê só o final)
-  `--max-events` (limite de eventos)
-   `--tail-event-window` (janela de eventos do fim)

Sinais de que truncou:
-   No report aparece “VCD read limits applied” e truncated=true.

Como resolver:
-   Se você quer mais fidelidade, aumente limites (com cuidado).
-   Se seu VCD é enorme, prefira aumentar tail e max-events antes de max-bytes.
---------

### 5) Windows: `--open` não abre o report

Em alguns ambientes o os.startfile pode falhar por associação/política.

Como resolver:
-   Abra manualmente: report/report.html
-   Ou rode vtriage open / vtriage open-run latest (se você estiver usando esses comandos).

----------

### 6) CI: “Operation was canceled”

Geralmente é:
-   timeout do job
-   cancelamento manual
-   limite de runtime do runner

Como resolver:

-   Aumente timeout-minutes no job (principalmente VexRiscv full).
-   Reduza o escopo do comando (ex: compile ao invés de test).
-   Use cache (sbt/coursier/ivy) quando aplicável.

----------

### 7) LiteX: testes não rodam / demoram / faltam deps

LiteX pode exigir deps adicionais dependendo do subset de testes.

Como resolver:
-   Comece com smoke:
    `python -c "import litex; print('litex-ok')" `
-   Depois rode testes por pasta:
    `python -m pytest -q test`

Se falhar por falta de libs, instale conforme o erro (ex: pyserial, requests, etc).

----------

### 8) VexRiscv: sbt não encontrado / muito lento / cache ausente

Em runners Ubuntu “limpos”, sbt pode não estar disponível via apt padrão, e a primeira execução baixa muita coisa.

Como resolver (CI):

-   Preferir usar o script ./sbt do repo se existir.
-   Cache:
-   ~/.cache/coursier
-   ~/.sbt
-   ~/.ivy2/cache



Dica prática:

-   Para smoke: sbt compile
-   Para full: rode regressão C++/Verilator (demora mais)

----------

### 9) “runner did not print RUN_DIR=”

O scripts/run.py precisa imprimir RUN_DIR=... para o CLI localizar o run.

Como resolver:

-   Verifique se o scripts/run.py está sendo chamado.
-   Rode com debug:  `vtriage run --debug ... `
-   Veja stdout/stderr do runner.

----------

### 10) “artifact inválido / faltando log.txt”

O contrato mínimo do run exige tests/seed_xxxx/log.txt.
fail.json marca FAIL; waves.vcd é opcional (exceto no --strict-waves).

Como resolver:

-   Regerar o run.
-   Se você está apontando pro diretório errado, use:
    `vtriage list-runs`
    `vtriage analyze latest`

----------

### 11) Diagnóstico rápido

Use:
`vtriage doctor`

Ele mostra paths, Python, runner, config e profiles.

---

## Opcional (melhor prática): docs/ em vez de README gigante

Se você quiser separar depois, a estrutura que “fecha” K5.2 de forma limpa é:

- `docs/troubleshooting.md` (esse bloco inteiro)

- `docs/artifacts.md` (contrato + schemas + exemplos)

- `docs/ci.md` (GitHub Actions: CI + oss-validate + como baixar artifacts)

Se você disser “quero docs/”, eu já te devolvo os 3 arquivos prontos.

---
