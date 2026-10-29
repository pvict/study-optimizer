# Bento — entrega da fase 5

28/10/2026 · base `49490c2` · versão **0.28.0**. Conclusão das seções 8.7–8.8 e acabamento do briefing `docs/redesign/PROMPT-CODEX-REDESIGN-BENTO-OSLER.md`. Impeccable, Revenue-Centric Design e Superpowers aplicados; execução inline e uma revisão independente, para conter recursos.

## Arquivos e decisões

- `osler/error_cards_ui.py`: resumo de respostas, saldo e referência diária; explicações recolhidas; registro antes do motivo de prioridade de cada deck. Importação, primeira passagem, repetições e desfazer preservados. Datas em DD/MM/AAAA.
- `osler/practical_reduction_ui.py`: três medidas com origens explícitas: total estudado declarado no PDF selecionado; cartões estudados nos temas sugeridos para avaliação; média da consulta de revisões por período, com data, origem e indicação de aproximação. Nenhuma medida estima suspensão, economia ou erros futuros. Ausência continua traço, zero informado continua zero.
- `osler/ui.py`: Biblioteca e Importar relatórios como entrada; inspeção e ferramentas técnicas recolhidas. Backup com atalho e retorno à biblioteca. Seletores, importações e ferramentas legadas mantidos.
- `osler/adaptive_ui.py`, `osler/guide_settings_ui.py`, `osler/bento_day_ui.py`: três seções Bento de Ajustes; meta diária e proporção em destaque, personalização e detalhes recolhidos. Instituições usa o formulário existente preservando tempos do roteiro legado. Nome opcional somente em sessão, identificado na interface e escapado na saudação, sem novo armazenamento ou mudança de perfil.
- `osler/bento.css`: composição e responsividade pelos tokens existentes; margem de rolagem no formulário de cards para o cabeçalho não cobrir o título.
- QA: `tests/test_bento_tools.py`, `scripts/check_bento_tools.py`. Documentação e versão: `README.md`, `DESIGN.md`, `.impeccable/design.json`, `pyproject.toml`, `osler/__init__.py`, plano desta fase e este relatório.

Reaproveitados formulários, callbacks, keys e cálculos. Nenhum modelo estatístico, prioridade, alocador, importador, schema ou módulo de persistência alterado. Originais e histórico preservados. A preferência de nome expira ao encerrar/reiniciar a sessão do navegador; não foi introduzido um arquivo paralelo de configurações.

## Prova funcional

Baseline: **944 passed, 1 skipped, 1 warning**.

```text
.venv/Scripts/python.exe -m pytest -q
952 passed, 1 skipped, 1 warning in 261.19s
```

Após o último polimento de apresentação e datas:

```text
.venv/Scripts/python.exe -m pytest tests/test_bento_tools.py tests/test_created_cards_ui.py tests/test_error_cards.py -q --tb=short
27 passed in 12.85s
```

Também passaram 19 testes de Ajustes, distribuição, provas e cards criados após a composição principal. Skip: symlink indisponível no Windows; warning: entrada ZIP duplicada deliberada no teste de backup.

Oito novos casos cobrem ausência/zero/fonte do total PDF, ausência de relatório, soma das sugestões, média medida sem consultas futuras, nome com Markdown e retorno entre telas sem mudar o perfil, navegação biblioteca/backup e salvamento de instituições preservando tempos e capacidade. Contratos novos foram vistos falhar antes da implementação. Nenhum teste preexistente foi alterado ou relaxado.

Revisão independente `bento5_review`, somente leitura: nenhum P1/P2 concreto encontrado. Lacunas apontadas nos testes foram cobertas: média medida, múltiplas sugestões, salvamento de instituições e nome com Markdown. Sem QA no banco real.

## Capturas, auditoria e rubrica

Edge/Playwright já instalado, servidor próprio na porta 8602, dados sintéticos descartáveis e recursos externos bloqueados. Foram preservadas **24 capturas antes**, **42 depois**, incluindo auditoria das seis telas anteriores em desktop/celular, e **20 estados adicionais**: vazio, nomes longos, formulário de cards e backup. Quatro larguras principais: 1440×900, 1366×768, 768×1024 e 390×844.

As capturas foram abertas e comparadas. Exemplos:

| Tela | Antes | Depois |
|---|---|---|
| Flashcards | [Desktop](../../evidencias/bento/fase5/antes-flashcards-1366x768.png) | [Desktop](../../evidencias/bento/fase5/depois-flashcards-1366x768.png) · [Celular](../../evidencias/bento/fase5/depois-flashcards-390x844.png) |
| Arquivos | [Desktop](../../evidencias/bento/fase5/antes-arquivos-1366x768.png) | [Desktop](../../evidencias/bento/fase5/depois-arquivos-1366x768.png) · [Celular](../../evidencias/bento/fase5/depois-arquivos-390x844.png) |
| Ajustes | [Desktop](../../evidencias/bento/fase5/antes-ajustes-1366x768.png) | [Desktop](../../evidencias/bento/fase5/depois-ajustes-1366x768.png) · [Celular](../../evidencias/bento/fase5/depois-ajustes-390x844.png) |

Manifestos e imagens ficam em `evidencias/bento/fase5/`, fora do Git. Cenários temporários e servidores de QA são encerrados e removidos pelo harness; nenhuma cópia de ambiente ou backup do usuário criada.

| Rubrica | Resultado |
|---|---|
| Uma ação primária por contexto | ✔ |
| Hero/primeiro bloco em 1366×768 | ✔ próximo deck e botão de registro visíveis; hero não se aplica às três telas desta fase |
| Padding 24px, gaps 16px | ✔ cards principais; barras de navegação com variante 16×24 documentada |
| Até três escalas por card, títulos 650–700 | ✔; métricas 28/34 conforme sistema |
| Sem cortes ou sobreposição, nomes longos | ✔ nas larguras e estados verificados; tabelas rolam internamente e nomes completos têm consulta própria |
| Cor de área restrita e estado neutro | ✔ |
| Contraste de texto AA medido | ✔ nos 13 pares de tokens abaixo |
| Sem cards pretos | ✔ |
| Alinhamento dos cards e ações | ✔; empilhamento no celular |
| Tarefa em 390px, alvos ≥44px | ✔ botões visíveis medidos, sem overflow horizontal da página |

Teclado: Tab/Shift+Tab com foco 3px no registro de cards e no backup; Espaço abre o registro e Enter abre backup. No slider nativo, a seta mudou 50→55 e o toque sintetizado do Chromium mudou 55→70 em viewport390, sem salvar. `slider-controls.json` guarda a propriedade value do input nativo; o primeiro registro dos estados consultava aria-valuenow, ausente nesse input, e por isso tem valores nulos. Zoom 200% foi emulado por CSS, não pelo zoom nativo do navegador. Não houve auditoria integral com leitor de tela, Firefox, Safari ou aparelho físico; não é certificação WCAG.

Contraste por luminância relativa sRGB, documentado em `contraste-texto.json`:

| Par de texto / superfície | Razão |
|---|---:|
| Principal / branco | 17,74 |
| Apoio / branco | 7,56 |
| Secundário / branco | 4,83 |
| Apoio / fundo geral | 7,06 |
| Branco / ação primária | 7,90 |
| Seleção | 7,07 |
| Descanso | 7,55 |
| Clínica / tint | 8,88 |
| Cirurgia / tint | 5,98 |
| Pediatria / tint | 5,21 |
| GO / tint | 6,48 |
| Preventiva / tint | 6,84 |
| Neutro / tint | 9,37 |

Auditoria geral: acessibilidade e responsividade verificadas dentro dessa cobertura; widgets nativos, labels, foco e movimento reduzido mantidos. Nenhuma biblioteca ou recurso remoto acrescentado. Tokens e superfícies das fases anteriores preservados; melhorias de desempenho dos modelos não fizeram parte desta entrega.

## Limites e reversão

Detector Impeccable: único aviso sobre Inter ser uma fonte muito usada. Mantida por exigência do briefing como fallback local. A fonte efetiva neste computador é SF Pro instalada; nenhum arquivo Apple distribuído. `corner-shape` continua aprimoramento progressivo com border-radius convencional como fallback. A inspeção determinística não substitui a visual nem prova semântica Python.

As cinco fases do redesign estão entregues. Isso não altera premissas dos cenários nem promete 90% ou aprovação. Aplicações de suspensão e reativação na Osler continuam manuais.

Commit separado com título `feat: conclui Bento em flashcards arquivos e ajustes (fase 5)`, integrado somente localmente. Para reverter: `git revert <hash desse commit>`. Nenhum dado precisa ser apagado. Sem push; diretrizes não rastreadas do usuário preservadas fora do commit.
