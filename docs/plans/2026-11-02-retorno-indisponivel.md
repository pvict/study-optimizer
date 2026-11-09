# Retorno indisponível na Osler

O usuário informa manualmente que um lote previsto ainda não está disponível. A ação adia o bloco inteiro para a partir do próximo dia de estudo (limite às 04h), sem registrar estudo, alterar convicção ou consumir a pendência. Não acessa a Osler.

1. Reutilizar a agenda auditável e cancelável para reservar o bloco e guardar uma data operacional por lote. Manter a previsão original de sete dias nos dados.
2. Excluir o tema indisponível de todas as entradas de alocação do dia, inclusive extras/trocas. Recalcular a vaga usando as prioridades existentes. Não ultrapassar a carga nem os compromissos protegidos.
3. Oferecer ação nos cards com retornos vencidos, prévia com data e mudanças do dia, confirmação e opção de desfazer. Quando amanhã não comportar estudo, mostrar a distinção entre disponibilidade e previsão de encaixe.
4. Provar persistência, reposição, calendário, reversão, concorrência e preservação dos resultados com testes focados. Não reescrever capturas históricas; derivar o plano efetivo para que indisponibilidade não vire falta do aluno.

Backup dos arquivos anteriores: `evidencias/retorno-indisponivel-2026-11-02/antes.zip`.

## Concluído

- Agenda persistente, fila operacional, alocação, calendário, prévia, confirmação e reversão implementados.
- Revisão independente encontrou dois casos adicionais corrigidos: capacidade adaptativa ainda ocupada pelo tema adiado e atraso reaparecendo no dia da disponibilidade. Ambos têm regressões automatizadas.
- Recibo diferencia lote antigo pendente de nova revisão após registro, conforme o caso real de Miocardite informado durante a execução. Nenhum resultado real foi reclassificado.
- Verificação final: **183 testes passaram** em 97,54s. Log em `evidencias/retorno-indisponivel-2026-11-02/testes.log`.
- Navegador sintético em 1440×1000 e 390×844: nenhuma exceção ou rolagem horizontal; 16px entre os botões de confirmar/manter. Dados temporários e servidor de teste removidos.
- A nota no ZIP identifica a baseline de `bento_day_ui.py`, reconstruída removendo somente as duas linhas de integração desta tarefa. Os demais arquivos alterados foram copiados antes das mudanças correspondentes. O diff dessa tarefa está em `alteracoes.patch`, separado das mudanças anteriores do projeto.
