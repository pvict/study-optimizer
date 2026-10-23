# Trocar um tema no plano de hoje

Cada bloco de Hoje tem **Trocar tema**, também disponível no detalhe de hoje no
Calendário. A escolha vale apenas para esse dia e mantém a quantidade do bloco.

- **Sugestão do app:** outro tema específico do mesmo tipo (novo ou revisão /
  diagnóstico), com banco suficiente, fora dos outros blocos, estudos já feitos
  hoje e reservas existentes. Prefere a mesma prioridade; aceita uma categoria
  vizinha. Dentro dessa faixa, aproxima a pontuação de priorização. Não sugere
  uma prioridade normal para substituir uma urgente.
- **Escolher tema:** busca digitada e navegação por área → assunto → tema. Permite
  mudar de novo para revisão ou o contrário, avisando que a divisão muda só hoje.

A comparação de pontuações usa distância logarítmica e categorias do planejador.
É uma regra de produto para semelhança, sem alegação de equivalência científica.

## Tema retirado e remanejamento

Antes de confirmar, o app mostra a primeira data para o tema retirado. A busca
considera carga em questões, divisão entre novos/revisões, limite de temas,
descansos, reservas existentes e blocos de prioridade alta/urgente previstos.
Busca primeiro em 14 dias, amplia para 30 e depois 90, sempre antes da prova.
Sem uma vaga, não aplica a troca: orienta ajustar a rotina.

A data torna-se uma reserva na agenda. Quando o bloco ou saldo anterior for maior
que uma sessão comporta, preserva a quantidade total e informa o primeiro bloco;
o restante continua nos dias seguintes dentro da carga. Reservas explícitas de
remanejamento podem ajustar a divisão do dia, sem aumentar a meta em questões.
Mudanças posteriores na rotina podem alterar a execução prevista; a origem e a
reserva continuam no histórico. Um atraso anterior não é zerado pela troca.

O tema retirado não é marcado como estudado e mantém desempenho, convicção, último
contato e lotes de respostas sem convicção. No calendário, aparece como tema
remanejado. Trocas de temas adicionais preservam a meta adicional e creditam as
respostas ao bloco extra original para não gerar uma meta crescente.

## Continuidade e controle

Os outros temas do plano são preservados. O substituto permanece no dia após
atualizar a página; blocos reais dele abatem a quantidade restante. A alocação
contabiliza o slot de origem, enquanto o histórico e o desempenho mantêm o tema
realmente respondido. Não são criados resultados ou contatos para simular uma troca.

**Trocas de hoje** mostra as reservas e oferece **Desfazer troca**. Em uma sequência
A → B → C, desfazer restaura B e retira apenas o remanejamento criado nessa etapa.
Estudos realmente registrados permanecem. Operações concorrentes ou prévias antigas
são rejeitadas, pedindo atualizar a escolha.

Trocas e cancelamentos são eventos imutáveis no armazenamento de agenda existente;
não há migração de banco nem dependência nova. Reservas alteradas posteriormente
prevalecem sobre versões anteriores, inclusive quando outra troca é encadeada.

Testes cobrem sugestões e escolha manual, cotas, saldos, adicionais, versões,
descansos, prazo da prova, lotes, encadeamento, conclusão e desfazer, além do fluxo
de interface. A conferência dos dados pessoais usa uma cópia local.
