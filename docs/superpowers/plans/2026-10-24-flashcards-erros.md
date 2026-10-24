# Flashcards de erros — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans para execução nesta sessão. Usuário dispensou ciclos de aprovação.

**Goal:** Organizar a recuperação do lote de cards pessoais sem aumentar a meta de questões.

**Architecture:** Parser local e planejamento puros; eventos aditivos com namespace error_cards.* no diário genérico existente study_plan_runs, sem migração de schema. Serviço lê o planejador de questões, mas nunca altera seus estudos/configurações. UI estende a identidade nativa existente.

**Tech Stack:** Python, HTMLParser, SQLite, Streamlit, pytest/AppTest.

**Spec:** docs/superpowers/specs/2026-10-24-flashcards-erros-design.md

## Global Constraints
Uso local, originais imutáveis, português simples, dia vira04h Brasília. Meta200 cards/dia escolhida pelo usuário. Sem automação Osler, sem aprovação fictícia ou curva individual inventada.

## Review Focus
- HTML truncado, grupo recolhido ou total incoerente não deve perder ou duplicar cards.
- Importação repetida/novo retrato não deve apagar estudo nem deduzir o mesmo saldo duas vezes.
- Repetições não devem aparentar cards diferentes concluídos; flashcards não são questões.
- Registro duplicado, desfazer e tela obsoleta não devem alterar indevidamente os totais.
- Descanso/simulado/início e ausência de dados não devem gerar obrigação artificial.

## Tasks
- [x] Parser em osler/error_cards.py; testes de hierarquia, folhas, fechamento, números, duplicidade e resíduos em tests/test_error_cards.py. RED → GREEN.
- [x] Planejamento puro: prioridade com dados ausentes, limite, repetições, dias bloqueados e previsão. Testes de orçamento e cenários. RED → GREEN.
- [x] Serviço em osler/error_cards_service.py: eventos/versionamento, importar, registrar/desfazer, ajustes e contexto da rotina. Testes de idempotência, concorrência e preservação. RED → GREEN.
- [x] Interface em osler/error_cards_ui.py; integrar osler/ui.py, study_day_ui.py e study_calendar_ui.py. AppTest, detector e validação visual desktop/mobile.
- [x] Importar arquivo real com escopo correto, validar em cópia mínima, revisão independente, suíte completa, documentos/versionamento e integração local. Não publicar.

## Ledger
- Escolha: sem nova dependência ou skill de terceiros; Find Skills encontrou ferramentas de autoria/Anki, não um mecanismo de recuperação aplicável a este inventário. Skills não substituem evidência científica.
- Evidência de aprendizagem: https://pubmed.ncbi.nlm.nih.gov/37615780/ e https://www.jmir.org/2024/1/e57760/ sustentam recuperação e espaçamento, não os pesos da nossa fila nem uma dose universal de200.
- Revisão independente encontrou teto de50 por tema/dia, falta de acesso a repetições de temas concluídos e corrida entre leituras/token. Corrigidos com rodadas, manutenção dos temas concluídos e leitura única de eventos; regressões reproduziram os casos. QA real encontrou alias de Trauma de face, conciliado com fontes preservadas.
- Usuário corrigiu o escopo: todos os8153 são não estudados ou pendentes. Importação ativa autorizada pelo pedido, com200/dia, sem criar estudo fictício. Cenário em cópia mínima mantém plano de questões, perfis e eventos de estudo intactos e completa a passagem dos8067 identificados em09/12/2026 sob premissas constantes.
