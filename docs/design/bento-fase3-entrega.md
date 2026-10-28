# Bento — entrega da fase 3

28/10/2026 · base0291faa · Temas e Registro, seções8.4–8.5 do briefing. Fases4–5 não executadas. Superpowers, Impeccable e Revenue-Centric Design aplicados.

## Arquivos e decisões

- `study_tables_ui.py`: filtros em container, atalhos de área/estado, tabela preservada como entrada e Lista com cards em duas colunas,12 por página. Nomes completos, próxima revisão, barra/meta, fontes, ações nativas e detalhes recolhidos. Acerto em novas com n exato no card de Todas; filtros explícitos de repetidas/mistas identificam a própria base. A tabela, os totais e o CSV filtrado mantêm o recorte original.
- `study_registration_ui.py`: extração coerente do formulário de adaptive_ui, card680px, seletor de tipo visível, três contagens, validação do modelo junto ao campo. Aproximados, contatos, acumulados, importação, cards criados, correção e histórico preservados. Toast e total real após salvar; Próximo bloco usa o primeiro item do plano atual e a alocação já existente de lotes. Não grava estudo ao navegar e mantém session_id/review_of.
- `adaptive_ui.py`: integração do formulário, abas controláveis para Ver erros e download Exportar CSV consolidado, mantendo a key. `bento.css`: composição responsiva e estados neutros. `goal_risk_ui.py`, `study_errors_ui.py`, `study_triage_ui.py`: containers nas abas existentes, confiança da fonte cadastrada, erros12 por página; regras de cálculo e ações mantidas.
- Documentação: DESIGN, sidecar, plano e este relatório. QA: capture_bento_phase3.py, check_bento_topics.py e três novos arquivos de testes.

Uma medição principal de convicção continua sendo uma fonte existente, sem média ou soma com outro denominador. PDF não vira acerto em novas. Ausência difere de zero. Nenhum modelo, algoritmo, importador, schema ou módulo de persistência foi alterado. Nenhum push; arquivo de diretrizes não rastreado do usuário preservado fora do commit.

## Verificação funcional

Baseline antes do produto: `.venv/Scripts/python.exe -m pytest -q` → **860 passed,1 skipped,1 warning**,253.81s.

Suíte completa após implementação: mesmo comando → **881 passed,1 skipped,1 warning**,230.28s. Skip: symlink indisponível no Windows. Warning: ZIP duplicado deliberado do teste de backup.

Após polimento final (tema inicial específico e feedback neutro): `.venv/Scripts/python.exe -m pytest -q tests/test_bento_registration.py tests/test_bento_topics.py tests/test_bento_topic_tabs.py tests/test_redesign_ui.py tests/test_study_activity_feedback_ui.py tests/test_created_cards_ui.py tests/test_topic_picker_ui.py` → **32 passed**,25.14s.

Novos testes: `test_bento_registration.py` (3), `test_bento_topics.py` (8), `test_bento_topic_tabs.py` (10). RED observado antes da implementação; GREEN depois. Nenhum teste preexistente alterado. Cobrem bases exatas/modos, ausência/zero, escape, paginação, filtros, callbacks, validação sem gravação, retenção dos valores, identidade e próximo bloco; fonte/confiança/Wilson, erros e prévia de corte. Atalho Ver erros limpa o motivo e a página residuais.

Revisões independentes: phase3_topic_review, phase3_tabs_review e phase3_final_integrity. P2 do filtro residual corrigido e coberto. Revisão final adicional por AppTest confirmou acumulado com último contato, correção versão2 preservando evento anterior, contato, percentual aproximado e rerun sem duplicação. Nenhum dado real usado.

## Navegador e evidências

Edge/Playwright já instalados; servidores próprios na porta8602, dados sintéticos em TemporaryDirectory, recursos externos bloqueados, processos e cenários descartáveis encerrados automaticamente. Nenhuma visita à plataforma Osler ou teste no banco real. Não foi tentada nova remoção do cenário antigo da fase2 cuja exclusão fora recusada.

`evidencias/bento/fase3/` contém8 capturas antes e8 depois de Temas/Registro em1440×900,1366×768,768×1024,390×844, com manifesto de geometria/fontes. Capturas adicionais: cards nas4 larguras, nome longo, validação, salvo, três abas secundárias em1366/390 e zoom200% do registro. Ao todo17 capturas adicionais. Imagens e JSON locais ficam fora do Git.

Capturas abertas e comparadas às prévias e à rubrica; três rodadas de inspeção/polimento. Correções: filtro neutro com ícone, escolha de tema recolhida quando específico, alinhamento dos campos, escala dos cards e feedback neutro após salvar. A referência visual foi adaptada para fontes/tokens aprovados, sem fundos pretos ou exemplos pessoais no app real.

`check_bento_topics.py` passou: quatro larguras sem overflow da página/cards, padding24px, no máximo12 cards e alvos dos cards≥44px. Tab/Shift+Tab com foco3px e Enter abre registro em1366/390. Formulário inválido preserva contagem e não grava; salvar e Próximo bloco fazem uma gravação e só navegação depois. ZoomCSS200% mantém tarefa e largura. Zero requisições externas. Manifesto das telas principais também mostra todos os botões medidos≥44px.

### Rubrica

| Critério | Resultado |
|---|---|
| Uma ação primária por contexto/card | ✔ formulário e confirmação; cards de consulta usam secundária |
| Hero e primeiro bloco acima da dobra em1366×768 | ✘ em Temas, filtros/resumo vêm antes da tabela/cards; resultados exigem rolagem. Hero de Hoje não pertence a esta fase. Registro mostra tema/campos; salvar pode exigir rolagem |
| Padding24 e gap16 nos cards | ✔ padding medido; gap declarado e inspecionado |
| Até3 tamanhos por card; títulos650–700 | ✔ cards11/13/20; controles nativos preservados |
| Sem texto cortado/sobreposto; nome longo | ✔ quatro larguras e nome longo sintético |
| Cor de área separada de estado | ✔ eyebrow/barra da área; estados e feedback neutros |
| ContrasteAA | ✔ pares textuais abaixo |
| Sem fundo preto | ✔ |
| Bordas e ações consistentes | ✔ cards em grade; formulário central680px |
| Tarefa possível e alvos44px em390 | ✔ registro, correção de erro e próximo bloco exercitados |

O ✘ restante é uma limitação de densidade da consulta, declarada acima. O navegador foi emulado; aparelho físico, leitor de tela e zoom nativo do sistema não foram testados. Estados sem amostra e filtros vazios cobertos por AppTest; spinner existente preservado. A auditoria não é certificação WCAG.

### Contraste calculado dos tokens usados

| Par | Razão |
|---|---:|
| Texto111827 / branco |17.74:1|
| Apoio4B5563 / branco |7.56:1|
| Branco / botão4338CA |7.90:1|
| Confirmação4338CA / EEF2FF |7.07:1|
| Estado111827 / F3F4F6 |16.12:1|
| Clínica3730A3 / EEF2FF |8.88:1|
| CirurgiaB42318 / FFF1F0 |5.98:1|
| Pediatria047857 / ECFDF5 |5.21:1|
| GO6D28D9 / F5F3FF |6.48:1|
| Preventiva92400E / FFFBEB |6.84:1|
| Neutro374151 / F3F4F6 |9.37:1|

### Auditoria e limites

Revisão visual independente phase3_visual_review abriu7 capturas: sem bloqueio/overflow visível, apontou feedback amarelo; corrigido no CSS de registro e recapturado. Fonte efetiva SF Pro instalada, Inter local comprovada no manifesto; nenhuma fonte Apple redistribuída. corner-shape é melhoria progressiva; fallback24px permanece.

Detector Impeccable executado uma vez no conjunto alterado: listou **1 warning, overused-font, bento.css:3**, referente a Inter exigida pelo briefing. Retornou código1 no conjunto misto Python/CSS, portanto não se declara cobertura completa nem scan limpo do código Python. Não houve segunda execução. Validação funcional e visual são evidências separadas.

Auditoria: acessibilidade3/4, desempenho3/4 (listas limitadas, sem profiling), tema3/4 (claro aprovado), responsividade3/4 (emulação), integridade4/4. Total16/20. Sem alteração do método estatístico. Não há promessa de aprovação.

Questions skipped: briefing fechado e AGENTS autoriza decisões reversíveis sem novo ciclo de aprovação.

## Reversão

Fase em um commit separado. Use `git revert <commit da fase3>` para preservar o histórico; base anterior0291faa. Dados ativos e versões do usuário não fazem parte desta alteração. O identificador do commit é informado na entrega da conversa.
