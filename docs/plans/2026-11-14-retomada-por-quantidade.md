# Retomada por quantidade e decks inteiros

Objetivo: reagendar dentro de uma carga suportável, sem restaurar banco antigo ou publicar dados pessoais. Código na branch online; histórico aditivo no SQLite protegido pela fronteira Supabase existente.

- Corrigir HTML com contadores de cartões e treino: ler somente o primeiro contador de cartões, preservando compatibilidade das exportações anteriores.
- Adicionar serviço de retomada: fila externa por quantidade, registro separado de realização sem temas/acertos fictícios; saldo real e limite diário. Reservar essa carga dentro do total, inclusive em Hoje, Calendário e reagendamento.
- Guardar reservas de decks por snapshot e tema; projetar somente o saldo não estudado, carregar perdas para a próxima vaga sem dobrar a meta. Referência 50 e limite habitual 70; deck maior sozinho em dia com menos questões. Não inferir vencimento a partir do inventário.
- Formulário recolhido em Hoje: informar quantidade externa, limites e HTML opcional para nova passagem. Prévia antes de aplicar; backup atual e gravação auditável; sem migração silenciosa de dados pessoais no código público.
- Verificar parser, soma exata da fila, dias de descanso/simulado, limites compartilhados, decks grandes, perda de dias, registros reais, concorrência e integridade. Testes sintéticos; arquivos pessoais permanecem fora do Git.

Execução autorizada no AGENTS.md e na conversa. Usar implementação direta na sessão.
