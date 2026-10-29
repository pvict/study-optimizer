# Rodízio com prévia editável

Autorização: execução direta conforme AGENTS.md. Não alterar dados ativos durante validação.

## Desenho
Estender ExamPracticeService: a prévia resolve conflitos em datas próximas sem mudar provas, descanso, resultados ou o orçamento diário. Identidades permanecem estáveis. Datas manuais prevalecem quando válidas; conflitos manuais exigem correção. Usa prioridades já calculadas, sem criar evidência de aprendizagem nem prometer ótimo estatístico.

Temas afetados podem receber reserva manual na própria prévia. Recalcular pelo calendário existente e verificar dose, capacidade, datas protegidas e concorrência antes da aplicação. Salvar reservas e rodízio no mesmo evento versionado; desfazer restaura ambos.

## Plano
- [x] Reproduzir rodízio inteiro bloqueado e testar encaixe, limites e datas manuais.
- [x] Implementar encaixe e reservas de temas no serviço existente.
- [x] Adicionar controles na prévia, mostrando datas originais, novas e avisos.
- [x] Testar serviço, calendário, aplicação/desfazer e UI nativa.

## Decisões e evidências
- Reutilizado o simulador existente; busca limitada a sete dias e desempate pela pressão de prioridades, sem novo modelo de aprendizagem ou dependência.
- Find Skills consultado: resultados de scheduling voltados a calendários externos/produção/otimização GPU não necessários a este fluxo local; nenhuma instalação adicional.
- TDD: falhas originais observadas para série bloqueada, ausência de edição de temas e edição após passagem dos dias; corrigidas. Testes de origem da correção, colisão com resultado, aplicação/desfazer e UI adicionados.
- Revisão independente identificou quatro problemas: colisão com treino registrado, perda de origem da correção, histórico automaticamente remanejado e expiração de datas manuais. Corrigidos e cobertos por regressões.
- Suíte dirigida de serviço/UI/planejamento/reagendamento: 54 testes aprovados. Revisão independente final sem novos bloqueadores e 17 testes de serviço aprovados separadamente. QA Chromium/Edge: 16 verificações em 1440, 1366, 768 e 390 pixels; prévia aberta, sem exceções nem overflow da página. Somente dados sintéticos temporários, removidos.
- Reservas manuais explicitamente escolhidas podem usar o orçamento completo do dia, alterando a divisão entre novos/revisões; aviso visível antes de aplicar. A substituição usa o saldo real da reserva anterior, preservando progresso parcial.
- Dados ativos não foram modificados; usuário continua responsável por revisar e aplicar sua prévia.
- Verificação ampla durante a implementação: 991 aprovados, 1 ignorado (symlink indisponível no Windows), 1 aviso de fixture ZIP inválido esperado. Após os últimos ajustes de reservas, a suíte dirigida de 54 testes passou; após a compatibilidade com prévias antigas em memória, os 3 testes de UI passaram novamente.
