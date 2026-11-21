# Auditoria do Osler e revisão de Hoje

Base `7a723bf`. Implementar os achados de usabilidade mais bem sustentados na tela Hoje e fechar a divergência de teste conhecida. Usar o worktree do chat. A etapa visual usa dados sintéticos e preserva rotas, registros, resultados, agenda, confirmação e cálculos.

- [x] Reproduzir a asserção do agrupamento e atualizar apenas a expectativa de sucesso do teste. Validar que a prévia continua sem escrita.
- [x] Em `bento_day_ui.py` e `today_replanning_ui.py`, ordenar a tarefa do dia antes dos controles de administração. Mostrar simulados marcados no próprio dia e deslocar o formulário ad hoc para o planejamento. Recolher a gestão dos atrasos em um resumo com contagem.
- [x] Em `study_day_ui.py` e `bento.css`, reduzir o peso dos controles secundários. Usar superfície clara para o primeiro bloco e lista separada por divisores. Progresso horizontal com números reais visíveis. Preservar ações específicas dos lotes e acervos parciais.
- [x] Testar normal, simulado, descanso, plano concluído, antecipação, troca, retorno indisponível, conclusão parcial e reagendamento. Conferir Hoje no navegador em 1280 px e 390 px.

Decisões de escopo: preservar Temas em atenção como destino independente, conforme a preferência anterior, e manter Agrupamentos visível. Revisar as demais telas com esses resultados em mãos antes de migrar navegação. Não usar a simulação sintética como justificativa para alterar dose, convicção, intervalos ou carga.

Próximos lotes técnicos recomendados: explicitar falta de capacidade sem tratar como nota baixa, descrever intervalos de calibração com denominadores por faixa, indicar o ajuste de carga para decks grandes. Auditar a fila de cards habitual e a retomada em conjunto antes de automatizar datas. Reproduzir a comparação com os scripts originais e verificar incidência, importações, simulados, reservas e carga conjunta antes de qualquer ajuste de parâmetros.

Verificação visual em cenário sintético com primeira ação acima da dobra, opções abertas por Enter e registro do tema a partir do próprio bloco. A revisão final reproduziu o recolhimento da etapa de temas errados após salvar um simulado. A correção preserva a expansão durante o preenchimento e tem um teste de regressão.
