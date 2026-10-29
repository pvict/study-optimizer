# Bento — entrega da fase 4

28/10/2026 · base `522d7aa` · Calendário, Simulados e Evolução, seções 8.2, 8.3 e 8.6 do briefing principal. Fase 5 não executada. Superpowers, Impeccable e Revenue-Centric Design aplicados.

## Arquivos e decisões

- `osler/study_calendar_ui.py`: navegação mensal, Semana como entrada, estados textuais, seleção e hoje distintos, áreas em chips e reorganização compacta. Os detalhes abrem automaticamente quando um atalho de prevenção precisa mostrar seu destino. Dias com algum estudo dizem “Com registro”, sem afirmar que a meta foi concluída.
- `osler/mock_exams_ui.py` e `osler/mock_schedule_ui.py`: resumo do último simulado antes do formulário, acertos/amostra, duração informada, barras por área e comparação com corte somente na instituição vinculada e escala compatível. Programação, prévia, aplicação, correção, conversão e desfazer preservados.
- `osler/study_evolution_ui.py` e novo `osler/evolution_history_ui.py`: Histórico como entrada; acerto em questões novas, convicção com sua própria amostra, volume semanal, dias com estudo e áreas com intervalos Wilson. Cenários preexistentes permanecem em uma seção secundária, explicitamente condicionais. A referência semanal usa a rotina atual nos dias decorridos; não inventa metas históricas.
- `osler/evolution_components.py`: jornada dos Cenários em HTML estático, pois o SVG era removido pelo sanitizador do Streamlit e deixava a faixa vazia. Mantidos dados, distinção realizado/previsto e helper SVG anterior para compatibilidade.
- `osler/bento.css` e `osler/bento.py`: composição, estados e responsividade; métrica compacta 28/34 documentada. Sem dependência nova ou recursos remotos.
- Documentação: `DESIGN.md`, `.impeccable/design.json`, plano `docs/plans/2026-10-28-bento-fase4.md` e este relatório. QA: novo `scripts/check_bento_planning.py` e três novos arquivos de testes.

Nenhum modelo estatístico, alocador, prioridade, schema, importador ou persistência foi alterado. Ausência continua diferente de zero; revisões e acumulados não viram acerto em questões novas. O arquivo não rastreado de diretrizes do usuário permanece fora do commit.

## Prova funcional

Baseline recente: **910 passed, 1 skipped, 1 warning**.

Suíte completa após implementação e correção da jornada:

```text
.venv/Scripts/python.exe -m pytest -q
944 passed, 1 skipped, 1 warning in 237.23s
```

Após o último polimento de texto/CSS:

```text
.venv/Scripts/python.exe -m pytest tests/test_bento_calendar.py tests/test_bento_evolution.py tests/test_evolution_ui.py tests/test_bento_mocks.py tests/test_ui_refinement.py -q
47 passed in 106.88s
```

Skip: symlink indisponível no Windows. Warning: entrada ZIP duplicada deliberada no teste de backup. Novos testes cobrem navegação, estados, datas-limite, escape, amostras separadas, ausência/zero, escalas, prévia sem aplicação e Histórico sem projeção nem gravação.

Testes preexistentes alterados deliberadamente: `tests/test_evolution_ui.py` abre Cenários em três testes que já verificavam essa função; suas asserções anteriores foram preservadas. `tests/test_ui_refinement.py` passa a esperar Semana como visão inicial. Nenhuma expectativa estatística foi relaxada.

Revisão independente de integridade encontrou o destino recolhido dos atalhos de prevenção; corrigido e coberto por testes. A inspeção visual foi feita pelo coordenador e pelo agente de QA. Uma tentativa adicional de crítica independente de design ficou indisponível por limite de uso da ferramenta; não é apresentada como revisão concluída.

## Evidência visual e rubrica

Edge/Playwright com dados sintéticos descartáveis na porta 8602, sem acesso ao banco real ou à plataforma Osler. Capturas em **1440×900, 1366×768, 768×1024 e 390×844**: 16 antes, 18 depois, 38 de estados adicionais. Zero requisições externas; diretórios temporários removidos pelo harness.

As capturas foram abertas e comparadas. Exemplos locais:

| Tela | Antes | Depois |
|---|---|---|
| Calendário | [Desktop](../../evidencias/bento/fase4/antes-calendario-1366x768.png) | [Desktop](../../evidencias/bento/fase4/depois-calendario-1366x768.png) · [Celular](../../evidencias/bento/fase4/depois-calendario-390x844.png) |
| Simulados | [Desktop](../../evidencias/bento/fase4/antes-simulados-resultados-1366x768.png) | [Desktop](../../evidencias/bento/fase4/depois-simulados-resultados-1366x768.png) · [Celular](../../evidencias/bento/fase4/depois-simulados-resultados-390x844.png) |
| Evolução | [Desktop](../../evidencias/bento/fase4/antes-evolucao-1366x768.png) | [Desktop](../../evidencias/bento/fase4/depois-evolucao-1366x768.png) · [Celular](../../evidencias/bento/fase4/depois-evolucao-390x844.png) |

Imagens e manifestos ficam em `evidencias/bento/fase4/`, fora do Git. No manifesto principal, a medição detalhada de Calendário em 1366px precede apenas a última troca de rótulo; a captura final e as verificações agregadas foram repetidas em 1366/390px e passaram.

| Critério do briefing | Resultado |
|---|---|
| Uma ação primária por contexto | ✔; widgets e ações existentes preservados |
| Hero e primeiro bloco acima da dobra | Não se aplica ao hero de Hoje; nestas telas, resumo e primeira linha principal visíveis em 1366×768 |
| Padding 24px e gaps 16px | ✔ nos cards principais; exceção explícita: grade interna do calendário mantém gap 12px para sete dias |
| Até três escalas por card, títulos 650–700 | ✔; métricas compactas 28/34 documentadas |
| Sem cortes ou sobreposição, incluindo nomes longos | ✔ nas larguras e estados medidos |
| Cor de área restrita e estado neutro | ✔ |
| Contraste AA dos pares de texto | ✔; tabela abaixo |
| Sem cards pretos | ✔ |
| Alinhamento de cards e ações | ✔; empilhamento no celular |
| Tarefa em 390px, alvos ≥44px | ✔; nenhuma rolagem horizontal da página |

Tab com foco visível, Enter selecionando dia e Espaço abrindo Resultados verificados. Estados vazio, nomes longos, descanso, simulado, Semana/Mês e navegação entre meses incluídos. Zoom 200% foi emulado por CSS: mantém as tarefas, mas não equivale a uma verificação de zoom nativo do navegador. Não houve auditoria completa com leitor de tela, Safari, Firefox ou celular físico.

Contraste calculado pela luminância relativa sRGB dos tokens, não estimado visualmente:

| Texto / fundo | Razão |
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

Todos os 13 pares passam AA para texto normal. Isso não constitui certificação integral WCAG. `contraste-texto.json` contém cores e método; manifestos contêm geometria, botões e fontes.

## Limitações e reversão

O detector Impeccable deixou um único aviso: Inter é uma fonte muito usada. Ela é exigida pelo briefing como fallback local, então foi mantida. A fonte efetiva neste computador é SF Pro instalada no sistema; nenhum arquivo Apple foi distribuído. Carregamento local do fallback Inter confirmado nas quatro larguras. `corner-shape` permanece aprimoramento progressivo, com border-radius convencional como fallback.

O detector não prova semântica Python. A integridade foi verificada por testes e revisão; a aparência, por capturas reais. Cenários continuam dependendo das premissas do modelo existente e não prometem desempenho futuro ou aprovação.

Entrega em commit separado com título `feat: aplica Bento ao calendario simulados e evolucao (fase 4)`, integrado apenas localmente. Para reverter, use `git revert <hash desse commit>`; nenhum dado ou histórico precisa ser apagado. Sem push remoto. Fase 5 permanece pendente.
