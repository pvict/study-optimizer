# Prevenção de atrasos — v0.13

O indicador laranja é uma previsão condicional: supondo a realização dos blocos propostos, alguns temas chegariam ao retorno sem vaga. A lista agora contém os temas específicos que formam o indicador. Não significa atraso pessoal já confirmado.

## Regra de planejamento

Uma política temporária seleciona temas e uma janela de 1–90 dias, limitada à prova e ao horizonte de 18 meses. Na carga atual, preserva a divisão de questões entre temas novos e revisões. As alternativas reservam a janela para revisões ou acrescentam questões temporárias destinadas a revisões. Descanso e reservas de recuperação existentes continuam valendo.

Para cada tema, a elegibilidade preventiva começa em `vencimento − min(2, intervalo // 5)` dias. Um intervalo de 7 dias admite 1 dia de antecipação; intervalos inferiores a 5 dias não são antecipados. Esta margem é uma escolha operacional limitada, **não uma fórmula de retenção ótima ou calibrada com dados pessoais**. Lotes de respostas sem convicção continuam retornando na data de sete dias. Primeiro contato não recebe uma reserva de revisão futura que impediria seu estudo.

A prioridade conserva os sinais adversos observados (baixo acerto, baixa convicção, erros críticos/recorrentes), separados do alerta por tempo sem contato. Contato projetado não implica melhora de desempenho. Temas urgentes conservam precedência; uma revisão antecipada não recebe urgência artificial por ter sido antecipada. Revisões sucessivas continuam dependendo dos contatos realizados e dos intervalos já calculados pelo modelo de espaçamento.

## Comparação e persistência

A comparação usa o plano diário real como ponto de partida e a mesma rotina de cálculo da agenda aplicada. Conta temas em risco, soma de dias com pendência por tema, questões programadas e primeiro dia sem vaga. Expõe novos riscos e piora de temas já em risco, mesmo se os totais melhorarem. Uma comparação não certifica capacidade suficiente; pode ser necessário mudar janela, estratégia ou quantidade de temas por dia.

Aplicar registra um evento imutável no histórico existente, sem criar sessão de estudo ou alterar último contato, acertos e convicção. Mudanças nas fontes, resultados ou configurações invalidam a prévia, e a aplicação confere novamente o cenário sob controle de concorrência. Desfazer cancela a política e restaura o estado anterior da agenda, preservando resultados e recuperações anteriores.

O desempenho futuro é desconhecido: as datas dependem da execução dos blocos e são recalculadas com novos resultados. Os limites de evidência e fontes do espaçamento permanecem os de [revisões sucessivas v0.11](revisoes-sucessivas-v0.11.md). Esta entrega adiciona uma regra de distribuição de carga, sem nova alegação de eficácia clínica, previsão de memória pessoal ou garantia de 90%/aprovação.
