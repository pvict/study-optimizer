# Repetição, convicção e calendário — versão 0.10

15/10/2026. Implementação independente, dados locais e atualizações manuais. Não existe evidência suficiente nos PDFs para identificar uma curva pessoal de memória ou garantir o algoritmo matematicamente ótimo para aprovação. A política prioriza prática com recuperação, evidência de convicção, vencimento, incidência e capacidade; seus resultados precisam ser acompanhados com blocos e provas representativas.

## Modelo de convicção e pendências

Cada bloco pode registrar `questions`, `correct` e `confident_correct`. A terceira contagem exige acertos exatos e fica entre zero e acertos. Campos ausentes em dados anteriores continuam desconhecidos. Acerto comum e convicto não são intercambiáveis. A estimativa por modalidade usa Beta(1+s,1+n−s) e Wilson separado, com `s` convicto somente entre tentativas com convicção explicitamente informada. Não se fabrica contagem exata a partir de percentuais arredondados.

Para um bloco informado, `pendentes = questões − convictas`. Um lote retorna sete dias depois. Revisão vinculada consome a quantidade revisada do lote de origem; seus acertos convictos saem da pendência e o restante forma um novo retorno em sete dias. A data é uma regra operacional solicitada pelo usuário a partir de sua descrição da plataforma, não extraída de uma API privada. Os lotes não identificam individualmente questões da Osler.

O grafo de revisão exige mesma hierarquia, origem existente, data não anterior, ausência de ciclos e contagens dentro do saldo. Correções ou desconsiderações que invalidem descendentes são rejeitadas antes da escrita. CSV valida o lote inteiro dentro da transação. Eventos anteriores não são regravados para preencher campos novos; defaults compatíveis permitem reconhecer reenvios antigos.

`Com convicção (%)` é descritivo das tentativas do período. `Lotes consolidados (%)` considera os lotes iniciados no período e suas revisões vinculadas até a data de referência: `convictas iniciais + convictas das revisões`, dividido pelo tamanho inicial, sem somar novamente os denominadores das revisões. Repetições não vinculadas são outros lotes, sem alegação de questões únicas. Consolidação não altera retrospectivamente a taxa de primeira tentativa.

## Espaçamento de temas

Referência primária: [SM-2, Piotr Wozniak](https://super-memory.com/english/ol/sm2.htm). Usamos sua ideia de intervalo crescente e fator de facilidade: `EF'=max(1,3; EF+0,1−(5−q)×(0,08+(5−q)×0,02))`, inicialmente2,5, limitado a3 nesta adaptação.

**Decisões próprias para blocos de tema:** contagens convictas de um mesmo dia definem a qualidade, sem avançar a sequência várias vezes por lançamentos no mesmo dia. Com amostra de ao menos dez e convicção na meta, usar sete dias, depois14, depois arredondar para cima o intervalo×EF. Falha abaixo de60% reinicia em três dias; desempenho intermediário usa sete. Intervalo máximo inicial30dias e proximidade da prova podem encurtar a janela. Sem convicção conhecida não se amplia intervalo com uma confiança presumida. Contato por leitura/flashcards continua visível, mas não renova evidência vencida de domínio nem resolve um lote.

Esses intervalos e a conversão de porcentagem em qualidade são adaptações heurísticas, não o SM-2 original nem FSRS calibrado por item. O [projeto FSRS](https://github.com/open-spaced-repetition/awesome-fsrs/wiki/The-Algorithm) é referência de pesquisa, não uma fórmula que se possa ajustar individualmente aos dados cumulativos disponíveis. O app não mostra porcentagem de memória supostamente retida ou chance de aprovação.

## Estados e blocos

Dominado exige convicção recente na meta, ao menos30tentativas na base nova/mista identificada, limite inferior Wilson>=80%, contato de recuperação não vencido e ausência de pendência vencida. Evidência adversa recente em repetidas/mistas impede domínio sem misturar esses denominadores no posterior principal. Aprendendo inclui evidência insuficiente; alerta inclui ausência de estudo registrado, rendimento/convicção<60%, retorno pendente vencido ou revisão de tema vencida. Baixo acerto no PDF pode gerar alerta provisório sem inventar convicção ou amostra binomial.

Para evitar blocos automáticos de uma questão, o planejador usa piso inicial10. Pequenas folhas são absorvidas pelo ancestral real mais próximo com banco suficiente e pelo menos dois níveis. A fronteira é disjunta: nenhum pai e filho como blocos automáticos simultâneos. Incidência do grupo conserva sua massa incluindo filhos absorvidos; não se descontam filhos para depois perder seu peso. Extras sobrepostos de pai/filho são rejeitados. Temas fora do agrupamento continuam pesquisáveis e registráveis manualmente.

Domínio de grupo não é transferido para filhos. Desempenho agregado do grupo pode usar suas sessões reais descendentes; estatísticas de tentativas na tabela são atribuídas ao caminho efetivamente informado, evitando duplicar denominadores entre níveis. Pais reais com estudo próprio permanecem reconhecidos no catálogo.

## Calendário e capacidade

Previsão até18meses, por semana/mês. Somente os dados atuais fornecem desempenho: a projeção move contatos planejados para distribuir revisões, sem criar sessões, sucessos ou convicção. Presume execução dos blocos; falhas, ausências e novos resultados reais recalculam o futuro. Vencimentos de lotes são incorporados ao orçamento, e o saldo que não cabe é sinalizado. Reduzir meta ou escolher descanso pode adiar revisões existentes, sem gerar uma nova dívida fictícia.

A quantidade é uma recomendação dentro da meta escolhida, não uma dose comprovadamente suficiente para90%. Prazos máximos são prioridades da política e podem ser inviáveis se houver mais demanda do que capacidade. A UI declara as pendências sem vaga e mantém os detalhes técnicos recolhidos.
