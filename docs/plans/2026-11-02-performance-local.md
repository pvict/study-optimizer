# Abertura e desempenho local

Objetivo: abrir pelo iniciar.bat sem manter um terminal aberto, reaproveitar o servidor deste projeto e reduzir trabalho que não contribui para a tela solicitada.

Autorização: usuário escolheu execução local com melhor desempenho; AGENTS dispensa ciclos adicionais para escolhas reversíveis. Sem registro automático no Windows, migração de dados ou mudança da política de revisões.

Abordagem: manter Streamlit, SQLite e dependências atuais. Um lançador da biblioteca padrão espera a saúde do servidor e verifica a identidade da pasta por um arquivo estático, com trava entre aberturas simultâneas. Imports das telas são feitos na rota responsável. A consulta de primeiras datas consome a previsão por dia e termina quando todos os temas já têm contato; o calendário completo continua percorrendo todo o horizonte. Evitam-se doses de temas inelegíveis e cópias de estados sem lotes, sem perder reservas ou retornos futuros.

Invariantes: apenas loopback; nunca encerrar um processo desconhecido; não abrir um serviço de outro projeto; não abrir o navegador antes da prontidão; falhas têm mensagem e log; sessões, prioridades, doses, datas e diagnósticos da previsão idênticos antes/depois.

- [x] Inspecionar abertura, imports e perfil do calendário; salvar originais em evidencias/performance-local-2026-11-02/codigo-antes.zip.
- [x] Testar lançador: espera prontidão, reuso, concorrência, conflito, falha do filho e timeout.
- [x] Implementar osler/local_launcher.py e atualizar iniciar.bat; documentar uso e logs. Encerramento pelo encerrar.bat com PID e criação nativa verificados, mantendo o handle durante a operação. Identidade gravada atomicamente antes de esperar o servidor.
- [x] Adiar imports de ferramentas fora da rota e confirmar a abertura real.
- [x] Reduzir preparação repetitiva da previsão, provando igualdade completa com a implementação anterior em cópia dos dados e cenários com reservas/retornos.
- [x] Verificar testes pertinentes, navegação e tempos antes/depois; remover cópias descartáveis. Suíte: 1.080 passaram, um pulado, aviso esperado de ZIP duplicado. Comparações completas idênticas; navegação sem exceções; ciclo de vida após saída do lançador confirmado.

Verificação: testes de lançador com HTTP local e processos controlados; comparação integral dos calendários, sem gravar na base ativa; medições em processos novos; auditoria do navegador em cópia temporária. Não interpretar uma medição como garantia de latência.
