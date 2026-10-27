# Bento — entrega da fase 2

27/10/2026 · base913f055 · navegação e Hoje. Fases3–5 não executadas. Uso das skills Superpowers, Impeccable (Operate, crítica/polimento/auditoria) e Revenue-Centric Design.

## Arquivos e escopo

- Composição nova: osler/bento_day_ui.py, osler/study_navigation_ui.py; resumos somente de leitura em osler/study_dashboard.py.
- Integração: ui.py/adaptive_ui.py; controles existentes extraídos em study_day_ui.py; alinhamento opcional do botãoTrocar tema em study_swap_ui.py; destaque da primeira ação de lote em review_parts_ui.py; horário do registro em study_activity_ui.py.
- Estilo: osler/bento.css. Documentos: DESIGN.md, .impeccable/design.json, plano e este relatório.
- QA: scripts/capture_bento.py adaptado à navegação e scripts/check_bento_today.py para estados/teclado/pausa/zoom. Novos testes test_bento_day.py e test_bento_phase2_ui.py.

Nenhum módulo de algoritmo, modelo, importação, schema ou persistência foi alterado. Quantidades/prioridades/intervalos permanecem iguais; os estados de apresentação não geram estudo. README e versão ficam para a fase5. O arquivo não rastreado docs/design/DIRETRIZES-REDESIGN-BENTO-CLAUDE.md foi preservado fora do commit. Nenhum push.

## Decisões e comportamento

1. NavegaçãoB: um menu lateral, botões nativos; main_view/adaptive_view permanecem como estado, sem seus antigos radios. Registrar bloco é a ação principal lateral. Outros seletores continuam nas próprias telas.
2. Sem nome cadastrado: Olá, conforme decisão3.9 do briefing; não adicionar perfil pessoal antes da fase5. Dia/data usam o corte04h já existente.
3. Hero usa o primeiro item real. Exceder a meta não esconde temas preservados; o estadoMeta registrada exige ausência de blocos restantes. Lotes e complementos conservam rótulos específicos e session_id/review_of, sem transformar revisão vinculada em questões novas. Apenas a primeira ação do hero é primária.
4. Feito hoje usa registros ativos e hora real de registro/atualização em Brasília. Não inventa hora de conclusão. Correções continuam disponíveis.
5. Semana: volume de blocos (tentativas), acerto exato somente em novas com n, pais históricos fora da contagem de dominados e prova cadastrada como fonte da data. Simulado conta como dia com estudo, mantendo seus resultados fora dos denominadores de questões. Passado sem meta conhecida não vira dívida.
6. Erros/trajetória e detalhes ficam recolhidos; disponibilidade parcial do Planner e complemento no banco continuam visíveis. Ajustar meu dia, adiantar revisões, trocas, retorno das trocas, flashcards, revisão semanal e exportação continuam disponíveis.
7. Pausa após pelo menos um bloco hoje: fragmento não bloqueante, prazo monotônico apenas na sessão, dispensável. O botão não compartilha a chave do estado de abertura. Descanso de revisão final aponta ao Calendário. Em dias sem meta, não mostrarX de0.

## Testes executados

Antes do produto: `.venv/Scripts/python.exe -m pytest -q` → **845passed,1skipped,1warning**,190.62s.

Suíte completa após implementação: `.venv/Scripts/python.exe -m pytest -q` → **860passed,1skipped,1warning**,219.63s.

Depois do ajuste final de texto em dias sem meta: `.venv/Scripts/python.exe -m pytest -q tests/test_bento_day.py tests/test_bento_phase2_ui.py tests/test_daily_excess_ui.py tests/test_question_ui.py` → **21passed**,19.08s.

O skip é a criação de symlink indisponível no Windows; o warning é o ZIP com nome duplicado deliberado do teste de backup. Na primeira execução intermediária, dois contratos de apresentação tinham sido perdidos (mensagem do excedente e aviso do início); foram restaurados. Um teste de formulário com timeout3s expirou durante execução concorrente do navegador; passou na execução isolada e na suíte completa, sem aumentar timeout.

TDD: helpers/estados, navegação/pausa, primeira ação primária do lote, simulado no ritmo e texto sem meta tiveram RED observado antes do respectivo código e GREEN depois. Registro não duplica nem apaga eventos nos testes; regressões existentes de excedentes, Planner parcial, trocas, simulados e revisões continuam cobertas.

## Navegador e evidências

Somente cenários sintéticos temporários, portas8602, Edge instalado/Playwright já disponível. O harness recusa outro endereço e dados sem marcador sintético, bloqueia recursos externos e encerra apenas seus processos. Nenhuma visita à plataforma Osler ou teste no banco real.

- Antes:4capturas de Hoje,1440×900,1366×768,768×1024,390×844.
- Depois:36capturas das nove telas nessas quatro resoluções, com manifesto, fonte efetiva viaCDP e geometria. Nenhuma rolagem horizontal detectada, zero requisições remotas.
- Estados adicionais: descanso, meta cumprida, início futuro, simulado, sem relatório, erro técnico e retorno vinculado, em1366e390;14capturas. Loading usa st.spinner; erro usa o tratamento existente de st.error.
- Teclado: Shift+Tab/Tab com foco3px, Enter abre registro e Espaço volta aHoje. Feito hoje mostra o horário local. Pausa foi iniciada e dispensada por widget no fragmento, sem gravação de estudo.
- Zoom de200% por CSS no Chromium, com ação principal acessível e sem overflow. Teste de nome longo sintético no DOM, largura390, sem alterar o banco. É emulação de layout/zoom, não teste em aparelho físico nem zoom nativo do sistema.

Fontes: mantidas as da fase1. Inter local continua disponível e sua renderização forçada de fallback é comprovada no manifesto; nenhuma fonte Apple redistribuída. corner-shape é melhoria progressiva no Edge; fallback24px já verificado na fundação. Estado HTML mantém rótulo sem ligatura de ícone não empacotada; ações usam Material nativo.

### Rubrica de Hoje

| Critério | Resultado |
|---|---|
| Uma ação primária por contexto/card | ✔; lotes destacam só a primeira ação |
| Hero e primeiro bloco visíveis em1366×768 | ✔ no cenário principal: título, quantidade e ação do primeiro restante visíveis; no hero com lote vinculado, título/quantidade do seguinte aparecem e suas ações exigem rolagem |
| Padding24 e gap16 entre cards | ✔ medidos nos containers Bento |
| Até3 tamanhos por card; título650–700 | ✔ padrão11/13/20 no hero/lista,13/14/20 no anel,13/15/20 na pausa; métricas usam15/32/13 |
| Sem corte/sobreposição, nome longo | ✔; título longo quebra sem overflow |
| Área e estado com semânticas diferentes | ✔ área tintada; estado com rótulo e borda neutra |
| ContrasteAA | ✔ pares textuais abaixo, mínimo5.21:1 |
| Nenhum fundo preto | ✔ |
| Bordas/alinhamento consistentes | ✔ |
| Tarefa e alvos44px em390 | ✔ |

Três rodadas de inspeção/polimento da composição principal: corrigidos sobreposição do anel, hero excessivamente alto, recuo da lateral e largura mínima que impedia recolhimento no tablet. O teste de estados teve ajuste próprio do textoX de0 e da espera pelo primeiro tick do relógio; não houve nova direção visual.

Capturas abertas e comparadas às referências anexadas, usando a hierarquia e removendo seus fundos pretos. Evidências locais: evidencias/bento/fase2/antes-*, depois-*, estado-*, estados-e-acessibilidade.json, contrastes.json e detector.json. As imagens ficam fora do Git conforme a política do repositório.

### Contraste calculado sobre cores computadas no navegador

| Par | Razão | AA |
|---|---:|---|
| Texto principal (#111827 / #F6F7FB) | 16.57:1 | ✔ |
| Apoio (#4B5563 / #FFFFFF) | 7.56:1 | ✔ |
| Seleção lateral (#4338CA / #EEF2FF) | 7.07:1 | ✔ |
| Areia (#5B4A32 / #F5F1EA) | 7.55:1 | ✔ |
| clinica texto (#3730A3 / #EEF2FF) | 8.88:1 | ✔ |
| clinica botão (#FFFFFF / #4338CA) | 7.90:1 | ✔ |
| cirurgia texto (#B42318 / #FFF1F0) | 5.98:1 | ✔ |
| cirurgia botão (#FFFFFF / #B42318) | 6.57:1 | ✔ |
| pediatria texto (#047857 / #ECFDF5) | 5.21:1 | ✔ |
| pediatria botão (#FFFFFF / #047857) | 5.48:1 | ✔ |
| go texto (#6D28D9 / #F5F3FF) | 6.48:1 | ✔ |
| go botão (#FFFFFF / #6D28D9) | 7.10:1 | ✔ |
| preventiva texto (#92400E / #FFFBEB) | 6.84:1 | ✔ |
| preventiva botão (#FFFFFF / #92400E) | 7.09:1 | ✔ |
| neutral texto (#374151 / #F3F4F6) | 9.37:1 | ✔ |
| neutral botão (#FFFFFF / #374151) | 10.31:1 | ✔ |

O trilho do anel e contornos claros são decoração: o número/estado textual mantém a informação. Foco de teclado: rgb(67,56,202), sólido3px, confirmado no navegador.

## Crítica, auditoria e revisão

Duas avaliações independentes: bento_phase2_design_review (hierarquia/capturas) e bento_phase2_integrity_review (callbacks/fontes/invariantes). Ajustes recebidos e feitos: preservar hero quando há itens apesar da meta atingida; primeira ação de lote primária; instrução correta no descanso final; simulado concluído no ritmo sem somar seus denominadores. Revisão final própria confirmou o diff restrito à apresentação.

Detector Impeccable executado **uma vez** nos dez arquivos UI/helper/CSS alterados: **9achados (1warning,8advisories)**. Inter é exigida pelo briefing. Demais achados: raio14 de botão,34 de squircle, campos16px, navegação14px e cinzas decorativosE5E7EB/9CA3AF. Variantes intencionais documentadas em DESIGN.md após o scan. Não foi executado segundo detector e não se declara resultado zero. Nenhum achado bloqueador de funcionalidade.

Auditoria: acessibilidade3/4 (teclado/contraste/emulação; leitor de tela/aparelho físico não testados); desempenho3/4 (fragmento isolado, listas limitadas, sem profiling formal); tema3/4 (claro aprovado, sem tema escuro nesta fase); responsividade3/4 (quatro resoluções/zoomCSS); integridade4/4 (fontes reais e domínio preservado). Total16/20; os limites são de cobertura de verificação, não alegação de certificaçãoWCAG.

Questions skipped: escopo fechado pelo briefing; AGENTS autoriza escolhas reversíveis e dispensa nova aprovação.

## Testes preexistentes alterados

Somente migração de navegação para open_view em conftest e leitura de session_state. test_ui ajusta seu helperadvanced à nova entrada lateral; test_question_ui verifica os destinos por suas keys nativas. Exceção deliberada e documentada: test_ui_refinement troca o título antigoSeu plano de hoje porOlá, exigido pela nova apresentação. Nenhum teste estatístico ou de algoritmo foi afrouxado.

- tests/conftest.py
- tests/test_adaptive_ui.py
- tests/test_capacity_ui.py
- tests/test_current_reduction.py
- tests/test_distribution_ui.py
- tests/test_evolution_ui.py
- tests/test_exam_goals_ui.py
- tests/test_final_review_ui.py
- tests/test_guided_ui.py
- tests/test_lote_c_ui.py
- tests/test_planner_snapshot.py
- tests/test_planner_supply.py
- tests/test_practical_reduction.py
- tests/test_prevention_ui.py
- tests/test_question_ui.py
- tests/test_redesign_ui.py
- tests/test_reduction.py
- tests/test_replanning_ui.py
- tests/test_schedule_start.py
- tests/test_simple_planner_ui.py
- tests/test_study_activity_feedback_ui.py
- tests/test_topic_picker_ui.py
- tests/test_trajectory_ui.py
- tests/test_ui.py
- tests/test_ui_refinement.py

## Limitações e reversão

No hero com lote vinculado e seus avisos, a ação do bloco seguinte pode exigir rolagem em768px de altura; o registro do bloco principal continua visível. Nome opcional, demais layouts e acabamento geral seguem nas fases3–5. Sem verificação em Safari/Firefox, aparelhos físicos, leitor de tela ou zoom nativo; sem alegação de conformidade total. A escolha de chip textual segue a fundação existente. Não há replanejamento implícito nem nova configuração no banco.

Commit único da fase na branchcodex/bento-fase2, integrado localmente àmain porfast-forward após as verificações. Para reverter, usar `git revert <commit-da-fase2>`; não usar reset destrutivo. A base é913f055. Dados, histórico e originais não precisam de migração/reversão. Os sete cenários de check_bento_today foram removidos automaticamente. O cenário comparativo C:/Users/Paulo/AppData/Local/Temp/osler-bento-fase2-xj5cwsr_/scenario e seu ponteiro tmp/bento-fase2-scenario.txt permanecem: a revisão automática recusou a exclusão recursiva mesmo após a conferência do marcador sintético e do caminho, com a mensagem blocked by policy, sem motivo mais específico. Nenhum contorno foi tentado. Evidências pequenas e o arquivo de diretrizes do usuário são preservados.
