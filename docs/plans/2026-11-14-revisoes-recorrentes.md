# Revisões recorrentes em sete dias

Manter fila agregada, sem questões individuais nem acesso automatizado à Osler. Cada registro de revisões pode informar a quantidade errada/sem convicção: essa quantidade vence em dia de estudo +7. Contagens desconhecidas permanecem desconhecidas. Um formulário adicional registra revisões geradas por outras questões, sem registrar estudo ou acertos fictícios.

Implementação: projeção FIFO de lotes por vencimento, consumo somente após vencer e retornos registrados apenas uma vez. Pendências carregam para a próxima vaga, respeitando descansos, simulados e capacidade compartilhada. Não presumir erros futuros para inventar recorrência. Atualizar o saldo inicial preserva retornos futuros já conhecidos e não duplica vencidos incluídos no saldo informado. Configurações antigas e registros sem contagem continuam válidos.

Arquivos: novo `osler/recurring_questions.py` para a projeção; `recovery.py` para gravação e capacidade; `recovery_ui.py` para contagens e agenda dos próximos retornos. Referência padrão de questões totais passa para 80, sem sobrescrever configurações pessoais já salvas. Os cartões manuais mantêm as regras atuais.

Testes: vencimento exato +7, repetição após novo erro, nenhum retorno por acerto convicto, desconhecido não vira zero conhecido, proibição de antecipar, descanso/simulado, limite diário, saldo esgotado que volta a ter vencimentos, atualização de saldo com futuros e concorrência. Rodar testes locais e comparar suíte completa com a base online antes de integrar. Banco pessoal não é publicado nem restaurado.
