# Roadmap v1 - Wave Triage

## 1) Núcleo do Produto (Funcional + Confiável)

- [ ] **F1 UX de CLI**
  - Comandos claros e intuitivos
  - Sistema de help completo (`--help`)
  - Mensagens de erro consistentes e acionáveis

- [ ] **F2 Runner cross-platform “de verdade”**
  - Suporte a Windows e Linux
  - Gerenciamento estável de paths e variáveis de ambiente
  - Comportamento consistente entre plataformas

- [ ] **F3 Contrato de artifacts bem definido**
  - Estrutura de artifacts documentada
  - Schemas versionados
  - Compatibilidade retroativa controlada

- [ ] **F4 Relatório HTML/MD estável e completo**
  - Geração de relatórios sem dependência de debug
  - Formato HTML e Markdown consistentes
  - Informações completas e bem estruturadas

## 2) Performance e Escalabilidade (VCD grande)

- [ ] **G1 Otimizar parsing VCD**
  - Implementar streaming de dados
  - Suporte a tail-only real (processamento incremental)
  - Evitar leitura completa quando desnecessário

- [x] **G2 Cache robusto**
  - Cache funcional implementado
  - [ ] Controles adicionais:
    - `--no-wave-cache`
    - `--refresh-wave-cache`

- [x] **G3 Index robusto**
  - Indexação funcional implementada
  - [ ] Comandos:
    - `--reuse-index`
    - `--rebuild-index`
  - [ ] Validações de integridade do índice

## 3) Qualidade de Triagem (Assinatura/Clustering/Localização)

- [x] **H1 Assinatura robusta** (✅ parcial)
  - Normalização de mensagens
  - Extração confiável de localização
  - [ ] Melhorias na normalização
  - [ ] Extração mais precisa de contexto

- [x] **H2 Subclusters por wave hash**
  - Agrupamento por hash de onda funcional

- [x] **H3 Localização melhor** (✅ parcial)
  - [ ] Expansão de prefixes por níveis
  - [ ] Fallback progressivo
  - [ ] Melhor precisão na localização de falhas

- [ ] **H4 Métricas internas**
  - Contagem de clusters
  - Medidas de estabilidade
  - Detecção básica de "merge errado"

## 4) Integração com CI (Entregável Real)

- [ ] **I1 GitHub Actions**
  - Workflow completo: run → analyze → upload report
  - Exemplos de configuração
  - Documentação específica

- [ ] **I2 GitLab CI** (opcional)
  - Pipeline equivalente ao GitHub Actions
  - Configuração example

- [ ] **I3 Padronização de saídas e exit codes**
  - `exit 0`: tudo passou
  - `exit 1`: falhas detectadas (análise completa)
  - `exit 2`: erro de uso/parâmetros inválidos
  - `exit 3`: contrato inválido/artifact corrompido

## 5) Dataset + Exemplos (Validação e Regressão)

- [ ] **J1 Examples prontos**
  - ZipCPU (funcional)
  - VexRiscv/LiteX
  - [ ] +1 exemplo adicional

- [ ] **J2 Bug injection**
  - Framework simples para injeção de bugs
  - Ground truth definido
  - Começar com casos pequenos

- [ ] **J3 Test suite do vtriage**
  - Testes com pytest
  - Cobertura: parsing, signature, cache, index
  - Testes de regressão automatizados

## 6) Documentação e Organização do Repositório

- [ ] **K1 README.md**
  - Quickstart para Windows e Linux
  - Troubleshooting comum
  - Exemplos básicos de uso

- [ ] **K2 Docs curtas**
  - Formatos de artifacts suportados
  - Configuração TOML (knobs disponíveis)
  - Profiles de execução

- [ ] **K3 Versionamento**
  - Estratégia de versionamento definida
  - Changelog (mesmo que simples)
  - Tags e releases

## 7) IA Copiloto (Opcional pós-v1)

- [ ] **L1 Interface pluggable**
  - Desacoplada do core
  - Desativada por padrão (opt-in)
  - API clara para integração

- [ ] **L2 Guardrails**
  - Evidências estruturadas obrigatórias
  - Sem decisão autônoma de clusters
  - Validações de segurança

- [ ] **L3 Prompt + output format**
  - Template de prompt padronizado
  - Formato de saída com citação de evidências
  - Rastreabilidade das sugestões

---

## Legenda
- [ ] Não iniciado
- [x] Concluído
- (✅ parcial) Em andamento/completo parcialmente






###### -----------------------------------------

1) K — Polimento de CLI/UX
K1 — Debug/verbosity (✅ parcialmente)

K1.1 --debug realmente imprimir algo útil mesmo em index reuse (log de reuse/rebuild)

K1.2 Padronizar mensagens error/warn/info + códigos de saída (exit code consistente)

K2 — Saída estruturada (✅ em andamento)

K2.1 --json gerar report.json sempre que pedido

K2.2 index reuse gerar MD/HTML/JSON sem reconstruir CaseResult (ajuste que acabamos de definir)

K2.3 Validar schema (schema: vtriage_report_v1) e manter compatibilidade

K3 — “Quality-of-life” comandos

K3.1 vtriage show-run --latest (ou equivalente) para imprimir o caminho do run

K3.2 vtriage open / analyze --open (abrir report.html cross-platform)

K3.3 Melhor help/usage (--help e exemplos curtos)

K4 — Robustez de path/config

K4.1 Resolver “qual .vtriage.toml usar” de forma determinística (root vs workdir) e documentar

K4.2 Mensagens de erro boas quando existem 2 TOMLs e o usuário se confunde

K4.3 Validar/normalizar caminhos (Windows/Linux) sem surpresa

K5 — Documentação mínima do usuário

K5.1 README “happy path” (5 comandos)

K5.2 Troubleshooting (VCD grande, paths, python -m venv, etc.)

2) L — Testes automatizados (Pytest) completos
L1 — Unit tests (✅ você começou)

L1.1 normalize_message, extract_location, signature_from

L1.2 vcd_wave_sketch_hash e parsing básico de VCD

L2 — Integration tests (J2 / end-to-end)

L2.1 Criar run_dir fake com seeds, logs, fail.json, waves.vcd

L2.2 Verificar clustering por signature e subcluster por wave_hash

L2.3 Garantir que não quebra em PASS-only e FAIL-only

L3 — CI para testes

L3.1 Workflow pytest no GitHub Actions (Windows + Ubuntu)

L3.2 Coverage opcional (pytest-cov) e badge opcional

3) M — Performance e escalabilidade (VCD grande)
M1 — Guardrails para VCD grande

M1.1 Limites (top_n, tail_event_window, sketch_top_n) sempre aplicados

M1.2 Tolerância a arquivo gigante: nunca explodir memória

M1.3 Mensagens claras quando truncou/analisou parcial

M2 — Cache e index (✅ parcialmente)

M2.1 wave_cache.json versionado por schema + knobs + fingerprint

M2.2 run_index.json versionado por schema

M2.3 Rebuild automático quando fingerprint muda

4) N — “Contrato” de artifacts (estável e documentado)
N1 — Estrutura final do artifact

N1.1 meta.json padronizado (cmd, workdir, sha, created_at)

N1.2 tests/seed_xxxx/{log.txt, fail.json?, waves.vcd?}

N1.3 Convenções: RUN_DIR= sempre, fail.json significa FAIL

N2 — Validações (✅ boa parte)

N2.1 validate_artifact_dir completa (logs obrigatórios, waves opcional/strict)

N2.2 Mensagens de erro com sugestões (Recent runs:)

5) O — Templates de CI e validação OSS (GitHub)
O1 — CI do próprio vtriage (✅ você já rodou)

O1.1 build + install + vtriage run quick

O1.2 upload report e artifacts

O2 — OSS validate (manual via workflow_dispatch) (✅ você já fez)

O2.1 scripts de clone/run (ZipCPU/LiteX etc.)

O2.2 “gates” por projeto (se falhar não quebra tudo — ou quebra dependendo do objetivo)

O2.3 matriz de projetos (ZipCPU primeiro; LiteX depois; VexRiscv etc.)

O3 — Ordem de validação (importante pro MVP)

O3.1 ZipCPU (ok) → LiteX (ok) → VexRiscv → OpenTitan (mais pesado)

O3.2 Para cada um: comando único + artifact root separado + relatório

6) P — Dataset / Bug Injection (para medir qualidade)
P1 — Bug injection MVP

P1.1 Mutators simples (if invertido, bit slice, off-by-one)

P1.2 Registro de ground truth (módulo/sinal esperado)

P1.3 Pipeline de execução: gerar bugs → rodar seeds → coletar artifacts

P2 — Métricas (para saber se está “bom”)

P2.1 Cluster purity (bug id)

P2.2 Top-K accuracy (módulo/sinal)

P2.3 Tempo de triagem (antes/depois)

7) Q — Empacotamento e distribuição local
Q1 — pip install -e . e pip install . funcionarem

Q1.1 entrypoint vtriage ok

Q1.2 optional deps dev ok (pip install -e ".[dev]")

Q2 — Versionamento + release (opcional agora)

Q2.1 tag v0.1.0

Q2.2 changelog mínimo

--------------------------------------
o que for referente ao load_run_index estará escrito "#import do load_run_index" ou "# uso do load_run_index"
foi colocado todo o código do analyze() no estado atual dele
os trexos com o uso do "vcd_meta" possui comentario na linha como "#ponto onde aparece vcd_meta" e ele está sendo atribuido a meta = ..."
analyze.py:
def load_run_index(run_dir: Path) -> dict | None:
    p = _run_index_path(run_dir)
    if not p.exists():
        return None
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return None

    # sanity checks (harden)
    if not isinstance(data, dict):
        return None
    if data.get("schema") != "run_index_v1":
        return None
    if "knobs" not in data or "fingerprint" not in data or "summary" not in data:
        return None
    if "clusters" not in data or "seeds" not in data:
        return None

    return data

def _run_index_path(run_dir: Path) -> Path:
    return run_dir / "run_index.json"

cli.py:

from vtriage.analyzer import (
    analyze_run,
    _read_lines,
    snippet,
    extract_location_from_lines,
    subcluster_by_wave_hash,
    load_run_index, #import do load_run_index
    run_fingerprint,
    CaseResult,
)

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
    debug: bool = typer.Option(False, "--debug", help="Mostra logs de debug (cache/index/etc.)"),
    json_out: bool = typer.Option(False, "--json", help="Gera também report.json"),
    max_bytes: Optional[int] = typer.Option(None, "--max-bytes", help="Limite p/ ler VCD inteiro (bytes)"),
    tail_bytes: Optional[int] = typer.Option(None, "--tail-bytes", help="Se truncar, quantos bytes do fim ler"),
    max_events: Optional[int] = typer.Option(None, "--max-events", help="Limite de eventos de valor no VCD"),
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
    if max_bytes is not None:
        params["max_bytes"] = int(max_bytes)
    if tail_bytes is not None:
        params["tail_bytes"] = int(tail_bytes)
    if max_events is not None:
        params["max_events"] = int(max_events)

    print(
        f"analyze params: tail={params['tail_event_window']} "
        f"top_n={params['top_n']} sketch_top_n={params['sketch_top_n']} "
        f"prefix_levels={params['prefix_levels']} "
        f"max_bytes={params['max_bytes']} tail_bytes={params['tail_bytes']} max_events={params['max_events']}"
    )

    index = None
    if debug:
        print("[debug] reuse_index=", reuse_index, "rebuild_index=", rebuild_index)
        print("[debug] index_loaded=", bool(index))

    if reuse_index and (not rebuild_index):
        idx = load_run_index(artifact_dir) #uso do load_run_index
        if idx and idx.get("schema") == "run_index_v1":
            same_knobs = (idx.get("knobs") == _knobs_now(params))
            if same_knobs:
                current_fp = run_fingerprint(artifact_dir)
                if idx.get("fingerprint") == current_fp:
                    index = idx
                    if index:
                        if debug:
                            print("[debug] index: reuse run_index.json")
                            print("[debug] index: report from run_index.json (no re-analyze)")
                        else:
                            print("index: reuse run_index.json")
                            print("index: report from run_index.json (no re-analyze)")
                else:
                    print("[yellow]index[/yellow]: fingerprint changed -> rebuild")
            else:
                print("[yellow]index[/yellow]: knobs changed -> rebuild")
    results = None
    clusters = None
    clusters_data = []
    if index is not None:
        # constrói results/clusters mínimos a partir do index

        summary = index.get("summary") or {}
        total = int(summary.get("total", 0))
        passes = int(summary.get("passes", 0))
        fails = int(summary.get("fails", 0))

        clusters_data = []

        # 1) Monta clusters_data “cru” a partir do index
        for cidx in (index.get("clusters") or []):
            kind, pattern, location, msg = _split_signature(cidx.get("signature", ""))

            seeds_list = cidx.get("seeds") or []
            seeds_str = ", ".join(str(s) for s in seeds_list[:30]) + (" ..." if len(seeds_list) > 30 else "")
            example_seed = int(seeds_list[0]) if seeds_list else None

            subclusters = []
            for sc in (cidx.get("subclusters") or []):
                wh = sc.get("wave_hash")
                if (wh is None) or (str(wh).strip() in ("", "-", "None")):
                    wh = "no_wave_hash"
                subclusters.append({
                    "wave_hash": wh,
                    "count": int(sc.get("count", 0)),
                    "seeds": ", ".join(str(s) for s in (sc.get("seeds") or [])[:30]) +
                            (" ..." if len((sc.get("seeds") or [])) > 30 else ""),
                })

            clusters_data.append({
                "kind": kind,
                "pattern": pattern,
                "location": location,
                "message": msg,
                "count": int(cidx.get("count", len(seeds_list))),
                "seeds": seeds_str,
                "example_seed": example_seed,
                "snippet": "",
                "top_tail": [],
                "top_total": [],
                "prefixes": [],
                "subclusters": subclusters,
                "vcd_meta": None,
            })

        # 2) Enriquecer clusters_data a partir de index["seeds"] + wave_cache.json + log
        seed_rows = index.get("seeds") or []
        seed_map = {int(s["seed"]): s for s in seed_rows if "seed" in s}

        for c in clusters_data:
            ex_seed = c.get("example_seed")
            if ex_seed is None:
                continue

            srow = seed_map.get(int(ex_seed))
            if not srow:
                continue

            case_dir = Path(srow["case_dir"])
            log_path = Path(srow.get("log") or (case_dir / "log.txt"))

            # snippet
            lines = _read_text_safe(log_path, limit=200)
            if lines:
                c["snippet"] = "\n".join(lines[:10])

            # prefixes (preferir o do seed row)
            c["prefixes"] = srow.get("prefixes") or []

            # vcd_meta (se veio no index)
            c["vcd_meta"] = srow.get("vcd_meta")

            # top signals via wave_cache.json (se existir)
            wc = _load_wave_cache_json(case_dir)
            if wc:
                c["top_tail"] = wc.get("top_tail") or []
                c["top_total"] = wc.get("top_total") or []
                if not c["prefixes"]:
                    c["prefixes"] = wc.get("prefixes") or []


        # --- gera MD/HTML/JSON e encerra ---
        md = []
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

        if not clusters_data:
            md.append("_No failures detected._")
        else:
            for i, c in enumerate(clusters_data, start=1):
                md.append(f"### {i}. {c['kind']} :: {c['pattern']}")
                md.append(f"- count: **{c['count']}**")
                md.append(f"- seeds: {c['seeds']}")
                md.append(f"- location: `{c['location']}`")
                md.append(f"- message: `{c['message']}`")
                md.append("")

                # scope_prefix
                prefixes = c.get("prefixes") or []
                if prefixes:
                    md.append(f"- scope_prefix: `{prefixes[0]}`")
                md.append("")

                if c.get("subclusters"):
                    md.append("**Subclusters (by wave hash)**")
                    for j, sc in enumerate(c["subclusters"], start=1):
                        wh = sc.get("wave_hash") or "no_hash"
                        md.append(f"- {j}. `{wh}` — count **{sc['count']}**, seeds: {sc['seeds']}")
                    md.append("")

                # snippet
                if c.get("snippet"):
                    md.append("```text")
                    md.extend(c["snippet"].splitlines())
                    md.append("```")
                    md.append("")


                # vcd meta (se truncou)
                meta = c.get("vcd_meta") #ponto onde aparece meta = ...
                if meta and meta.get("truncated"):
                    md.append("**VCD read limits applied**")
                    md.append(f"- size_bytes: **{meta.get('size_bytes')}**")
                    if meta.get("used_tail_bytes"):
                        md.append(f"- used_tail_bytes: **{meta.get('used_tail_bytes')}**")
                    md.append(f"- reason: `{meta.get('reason')}`")
                    md.append("")


                    # top signals
                    top_tail = c.get("top_tail") or []
                    top_total = c.get("top_total") or []

                    md.append("**Top suspect signals (tail window)**")
                    if top_tail:
                        for name, cnt in top_tail[:20]:
                            md.append(f"- `{name}` — **{cnt}**")
                    else:
                        md.append("_no signals in scope_")
                    md.append("")

                    md.append("**Top active signals (whole run)**")
                    if top_total:
                        for name, cnt in top_total[:20]:
                            md.append(f"- `{name}` — **{cnt}**")
                    else:
                        md.append("_no signals in scope_")
                    md.append("")

        (out / "report.md").write_text("\n".join(md) + "\n", encoding="utf-8")

        html = render_html_report(
            artifact=str(artifact_dir),
            generated_at=index.get("generated_at") or datetime.now().isoformat(timespec="seconds"),
            total=total,
            passes=passes,
            fails=fails,
            clusters=clusters_data,
        )
        (out / "report.html").write_text(html, encoding="utf-8")

        if json_out:
            (out / "report.json").write_text(
                json.dumps(index, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )

        print("[green]OK[/green] relatório gerado em", out)
        return


    else:
        # ---------- REBUILD ----------
        results, clusters = analyze_run(
            artifact_dir,
            tail_event_window=params["tail_event_window"],
            top_n=params["top_n"],
            sketch_top_n=params["sketch_top_n"],
            prefix_levels=params["prefix_levels"],
            max_bytes=params["max_bytes"],
            tail_bytes=params["tail_bytes"],
            max_events=params["max_events"],
        )
        # strict waves só faz sentido aqui porque temos results
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


    if index is not None:
        if not clusters_data:
            md.append("_No failures detected._")
        else:
            for i, c in enumerate(clusters_data, start=1):
                md.append(f"### {i}. {c['kind']} :: {c['pattern']}")
                md.append(f"- count: **{c['count']}**")
                md.append(f"- seeds: {c['seeds']}")
                md.append(f"- location: `{c['location']}`")
                md.append(f"- message: `{c['message']}`")
                md.append("")
                if c.get("subclusters"):
                    md.append("**Subclusters (by wave hash)**")
                    for j, sc in enumerate(c["subclusters"], start=1):
                        md.append(f"- {j}. `{sc['wave_hash']}` — count **{sc['count']}**, seeds: {sc['seeds']}")
                    md.append("")
    else:
        for i, (sig, items) in enumerate(clusters.items(), start=1):
            kind, pattern, location, msg = _split_signature(sig)
            subs = subcluster_by_wave_hash(items)

            ex = items[0]
            meta = ex.vcd_meta
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

            meta_truncated = False
            meta_size_bytes = None
            meta_used_tail_bytes = None
            meta_reason = None

            if isinstance(meta, dict):
                meta_truncated = bool(meta.get("truncated"))
                meta_size_bytes = meta.get("size_bytes")
                meta_used_tail_bytes = meta.get("used_tail_bytes")
                meta_reason = meta.get("reason")
            elif meta is not None:
                meta_truncated = bool(getattr(meta, "truncated", False))
                meta_size_bytes = getattr(meta, "size_bytes", None)
                meta_used_tail_bytes = getattr(meta, "used_tail_bytes", None)
                meta_reason = getattr(meta, "reason", None)

            if meta_truncated:
                md.append("**VCD read limits applied**")
                md.append(f"- size_bytes: **{meta_size_bytes}**")
                if meta_used_tail_bytes:
                    md.append(f"- used_tail_bytes: **{meta_used_tail_bytes}**")
                md.append(f"- reason: `{meta_reason}`")
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

    if json_out:

        payload = {
            "schema": "vtriage_report_v1",
            "artifact": str(artifact_dir),
            "generated_at": index.get("generated_at") or datetime.now().isoformat(timespec="seconds"),
            "knobs": index.get("knobs") or {},
            "summary": index.get("summary") or {"total": total, "passes": passes, "fails": fails},
            "clusters": clusters_data,
        }
        (out / "report.json").write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

    print("[green]OK[/green] relatório gerado em", out)


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

    idx = load_run_index(run_dir) #uso do load_run_index
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
