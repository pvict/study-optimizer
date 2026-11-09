# Concluir um bloco com menos questões

Reutiliza a decisão auditável de dispensar complemento, agora disponível mesmo sem retrato do Planner ou quando o banco disponível difere do arquivo importado.

No card: registrar a quantidade realmente feita, clicar em **Concluir bloco com menos questões**, conferir a quantidade feita e a dispensada e confirmar. A alternativa anterior **Encerrar tema hoje** continua disponível quando a capacidade importada do Planner já foi cumprida.

- Não há conclusão com zero questões registradas. Dispensa vale para o encontro atual, não significa domínio nem encerra lotes de erro.
- Totais de questões feitas, acertos, convicção e datas de contato permanecem baseados nos lançamentos reais. A próxima revisão é calculada com essa evidência parcial; a dispensa não alonga o intervalo por si só.
- Bloco concluído sai do dia e não gera dívida pelo saldo dispensado. Capturas originais permanecem no histórico.
- A conclusão tem confirmação, toast e **Desfazer dispensa**. Correções/void dos lançamentos revalidam o crédito; não é possível reutilizar um resultado de simulado como se fosse sua prática de correção.
- Novos extras ou trocas explícitas depois da conclusão têm crédito próprio e não são ocultados pela decisão antiga.

Verificação final: 85 testes focados e os 12 testes originais de conclusão/dispensa passaram, incluindo confirmação/reversão na UI, preservação estatística, edição de lançamentos, reservas atrasadas, novo extra e exclusão do resultado do próprio simulado. Revisão independente encontrou e motivou regressões para os limites de crédito por encontro e para conclusões independentes de blocos extras posteriores. Decisões de contextos distintos ficam preservadas; desfazer e repetir a conclusão no mesmo contexto não reaproveita uma decisão desfeita.

Backup das fontes anteriores: `evidencias/conclusao-parcial-2026-11-08/antes.zip`. Nenhuma conclusão foi aplicada aos dados pessoais do usuário durante o desenvolvimento.
