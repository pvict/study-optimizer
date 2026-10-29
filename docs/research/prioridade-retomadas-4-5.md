# Retomadas sem espera silenciosa — política 4.5

28/10/2026 · base `b6c68c3`. Correção global de prioridade e admissão; nenhum peso institucional, percentual importado, posterior de desempenho ou parâmetro de dose/espaçamento foi recalibrado.

## Problema e correção

Taquiarritmias tinha contato em22/09/2026, intervalo descritivo de7dias, referência operacional de22/10 e vaga em26/04/2027. O destaque semanal rebaixava sinais adversos dos demais temas. O bônus de afastamento era constante depois do vencimento e o controle de admissão podia bloquear indefinidamente diagnósticos por suas repetições hipotéticas futuras.

- `review_policy.py`: a pressão de espera cresce diariamente, preservando o peso institucional e o intervalo existentes. Para a fila inicial com referência vencida: `score da fila = score-base existente + importância × (1 + dias além da referência / intervalo)`. É uma política operacional de envelhecimento, não uma probabilidade de esquecer nem fórmula validada de retenção.
- `adaptive_planning.py`: o foco semanal não apaga a prioridade de evidência. Dificuldade alta declarada usa `Observation.dificuldade`, já existente, sem converter relato em taxa de acerto ou erro crítico. Vale dentro da janela recente, limitada ao afastamento configurado; um bloco posterior com contagens exatas e amostra mínima passa a orientar o tema. Modalidades e retornos continuam com bases próprias.
- `study_capacity.py`: no modo adaptativo, a demanda estimada de retomadas em relação à janela de contato abre mais espaço de revisão. A proporção configurada permanece como referência; o modo fixo mantém a preferência explícita. Retomadas antigas podem usar capacidade real de hoje mesmo quando sua repetição futura hipotética pressiona a previsão. A pressão fica identificada; descansos, orçamento e limite efetivo de temas continuam valendo.
- Reserva/recuperação não desconta a mesma quantidade duas vezes: a parte já alocada é abatida só da carga de hoje. Cargas futuras conhecidas continuam presentes. Reagendamentos futuros são excluídos antes da admissão, para não consumirem a vaga de um tema elegível hoje.
- `reduction_recommendations.py`: dificuldade alta atual impede sugerir uma pausa seletiva dos cartões daquele tema. Não é suspensão ou reativação automática.
- `bento_day_ui.py`: detalhes do plano explicam a pressão prospectiva e quando o objetivo de afastamento não cabe na carga. Não são criadas centenas de faltas retroativas, datas fictícias ou garantias de prazo.

A revisão de [Trumble et al.](https://pubmed.ncbi.nlm.nih.gov/37615780/) sustenta prática distribuída e recuperação; [Pavlik e Anderson](https://pubmed.ncbi.nlm.nih.gov/18590367/) estudam modelagem de espaçamento com dados de aprendizagem. Esses trabalhos não validam um prazo universal por tema nem os pesos desta fila. A correção trata da alocação; o modelo de memória do aplicativo não ganhou uma calibração fictícia.

## Relato de hoje

Registrados, pelas APIs existentes e com histórico aditivo:

- Contato em28/10/2026 com Taquiarritmias, sessão `relato-taquiarritmias-2026-10-28`, tipo contato, **zero tentativas adicionadas**.
- Observação2: dificuldade alta declarada nesta conversa, sem contagem de questões ou acertos e sem marcar erro crítico/recorrente.

Os63 itens e57,1% de segurança do retrato Osler permanecem na fonte original. O relato não vira uma nova amostra binomial. A primeira medição objetiva no app continua ausente até o usuário informar seus resultados. O novo contato previsto é **04/11/2026,20 questões de referência**; recalculável após novos registros.

## Efeito global e custo

Diagnóstico de dados atuais em SQLite somente em RAM; origem aberta `mode=ro`. Testes funcionais usam apenas dados sintéticos. Nenhuma cópia de banco em disco ou teste no banco ativo. Arquivos de diagnóstico em `evidencias/taquiarritmias/`, ignorados pelo Git.

| Medida da previsão | Antes | Depois, incluindo o relato |
|---|---:|---:|
| Unidades com próxima data | 1490/1490 | 1490/1490 |
| Mediana de espera dos529 contatos iniciais conhecidos | 198dias | 69dias |
| Percentil90 da espera nesse grupo | 265dias | 149dias |
| Espera acima de90dias nesse grupo | 459 | 175 |
| Taquiarritmias | 26/04/2027 | 04/11/2026 |

Na comparação,522 temas foram antecipados,934 ficaram para depois e34 mantiveram a data. **Nenhum compromisso de revisão já registrado foi adiado.** Parte das primeiras passagens de outros temas cede espaço às retomadas: esse é um custo real da reorganização, preservada a carga de120 questões e6temas/dia.

Ainda há421 contatos iniciais conhecidos previstos além de30dias. A mudança reduz a espera, mas não faz toda a demanda caber nesse intervalo. A janela é um objetivo de planejamento, não uma garantia impossível. O app comunica a insuficiência e a fila continua mudando com resultados reais. Ter uma vaga não comprova execução, domínio ou melhora futura.

Uma primeira implementação que alterava somente a ordem foi rejeitada na análise: a espera de Taquiarritmias continuava em meses. A comparação final inclui a correção do bloqueio de capacidade.

## Verificação e revisão

Quatorze novos casos em `tests/test_intake_priority.py`: preservação de sinais fora do foco, envelhecimento contínuo e sem mutação, admissão sob pressão hipotética, limites reais, descanso, modo fixo, dificuldade sem acertos inventados, evidência posterior, elegibilidade, proporção adaptativa, proteção de cards, observação/contato end-to-end, reserva sem duplo desconto e reagendamento futuro sem vaga fantasma.

Os novos contratos relevantes foram vistos falhar antes das correções. Última bateria focada de alocação, trocas e regressão: **47 passed,6.38s**.

Suíte completa final:

```text
.venv/Scripts/python.exe -m pytest -q --tb=short
966 passed, 1 skipped, 1 warning in 249.09s
```

Skip: symlink indisponível no Windows. Warning: entrada ZIP duplicada deliberada no teste de backup. Nenhuma falha pendente. A primeira suíte revelou a expectativa antiga de prioridade no golden; a mudança deliberada descrita abaixo preservou suas verificações estatísticas. A suíte final inclui as regressões adicionais da revisão.

O golden `algorithm_v1_baseline.json` ficou intacto. O teste de regressão agora compara estados por ID e permite apenas prioridade operacional diferente: todos os demais campos, inclusive posteriors, confiança, intervalos, doses, scores-base e metas, continuam sendo comparados exatamente ao golden. Novos testes cobrem as prioridades corrigidas.

Revisão independente `intake_review` encontrou os dois P2 de duplo desconto e elegibilidade. Ambos receberam regressões e correções; revisão incremental reproduziu os casos corrigidos sem novos P1/P2. Sem banco real nessa revisão.

## Reversão

Commit separado com título `fix: protege retomadas e preserva sinais de dificuldade`. `git revert <hash>` reverte a política. Os registros declarados pelo usuário permanecem como fatos com histórico; observação e contato podem ser desconsiderados pelas ações existentes, sem apagar originais. Sem push remoto.
