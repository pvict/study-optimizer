# Simulados com datas flexíveis — desenho e execução

Objetivo: reservar simulados a cada sete dias a partir de 25/10/2026, permitir mudar ou retirar cada ocorrência independentemente e mostrar o efeito nos temas, dentro da carga diária. O usuário autorizou a implementação e informou a primeira data. Frequência é ponto de partida, não obrigação de manter o mesmo dia da semana.

Decisão: usar eventos imutáveis `reschedule.apply`, escopo `mock_schedule`, no StudyAgenda existente, sem nova tabela ou resultados fictícios. Uma nova versão substitui a anterior por referência, com cancelamento reversível. Cada ocorrência conserva uma identidade baseada na data original; mudanças individuais não deslocam as demais. Datas passadas e dias de prova/descanso final são protegidos. Um simulado reservado é distinto de um simulado realizado.

Alternativas consideradas: marcar apenas lembretes manteria a falha de capacidade; criar registros de resultados futuros inventaria estudo; alterar diretamente a configuração de descanso esconderia o motivo e dificultaria desfazer. A escolha mantém motivo, histórico e o canal de planejamento existente.

UI: Calendário mostra “Simulado programado” em Agenda/Semana/Mês e oferece a gestão em área própria; Simulados oferece Programação e Resultados em abas. Data inicial + frequência montam a série até a prova de referência. Cada ocorrência pode ser movida ou retirada, com prévia antes de aplicar. Prévia mostra temas deslocados, datas encontradas e falta de vaga, sem aumentar a meta de 120. Detalhes de horizonte e limites ficam recolhidos. Nenhum campo novo no registro rápido.

Remanejamento: o calendário operacional recalcula próximos contatos ao remover vagas de simulados. A comparação antes/depois lista os temas originalmente previstos nos dias reservados e a nova data no horizonte calculado; temas sem vaga ficam explicitamente sem data. Datas são previsões condicionadas aos resultados futuros, não compromissos de aprendizagem nem estudo concluído. Reservas explícitas já existentes conservam precedência e aparecem na prévia. A série afeta capacidade e Evolução em todo o horizonte; a prévia identifica o período efetivamente comparado.

## Plano de implementação

Stack: Python, Streamlit, SQLite, pytest/AppTest. Execução inline com Superpowers:executing-plans, TDD e verificação antes da conclusão. A pasta corrente precisa continuar servindo o app local; isolamento por branch `codex/simulados-flexiveis`, sem duplicar dados pessoais.

- [x] Testes RED: geração de datas, mudança individual, retirada, colisões, passado, limite, seleção de versão e desfazer.
- [x] `osler/mock_schedule.py`: funções puras para série e comparação de calendário. `mock_schedule_service.py`: consulta, prévia/aplicar/mover/retirar, token e versões pelo StudyAgenda. `study_agenda.py` e `study_read_model.py`: respeitar versões substituídas também na análise de aderência.
- [x] Integrar dia reservado ao controle de capacidade, descanso normal, prevenção, revisão final, calendário, Hoje e Evolução, preservando filas de retorno e sem crédito por estudo.
- [x] Testes RED/GREEN de integração: simulado ocupa o dia, temas mudam de data dentro da carga, filas permanecem, limites/erros/ausência de vaga, resultados e versões preservados, prévia obsoleta rejeitada.
- [x] `mock_schedule_ui.py`: programação, mover/retirar, prévia legível e histórico. Calendário e Simulados com acesso visível; configurações explicam a diferença entre frequência e reserva. AppTest.
- [x] Revisão independente, suíte completa, cópia mínima para QA real, backup antes de configurar a série real, versão 0.24.0, docs e conferência visual. Aplicar a série autorizada de 25/10 a cada sete dias, sem alterar estudos registrados.

## Pontos de revisão

Não reativar uma versão antiga quando a substituição é desfeita; não deslocar toda a série ao mudar um domingo para terça; não sobrescrever prova, descanso final ou simulado já realizado; não confundir reserva com resultado; não esconder temas sem vaga nem fazer uma questão retornada parecer respondida. Preservar alterações passadas em novas versões e respeitar a virada às 04h.

