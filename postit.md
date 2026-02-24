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
