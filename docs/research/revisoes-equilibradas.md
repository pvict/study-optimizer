# Revisões equilibradas — v0.25.0

## O que muda

A política anterior usava convicção como critério central, encurtava intervalos pela incidência e impunha dose mínima de 20 em qualquer reforço. Na estratégia `balanced_v2`, o acerto objetivo é o sinal central; convicção permanece informativa e mantém a fila de questões que voltam após sete dias. Um acerto inseguro não vira erro no cálculo do tema.

Em Ajustes → Meta e rotina → Como o app calcula as revisões, o usuário compara estratégias antes de aplicar. A prévia inclui doses, intervalos, prioridades, estados e datas devidas de todos os temas alterados, blocos restantes de hoje e próximos contatos da janela de 28 dias. Exibe a meta padrão e a meta específica do dia separadamente. Dados novos invalidam a prévia. Aplicação grava uma nova versão do perfil e o comparativo, na mesma transação; resultados, metas por área, incidências, simulados e ajustes diários são preservados. Para voltar à anterior, selecione-a e aplique uma nova prévia, sem apagar alterações posteriores.

Arquivos antigos usam `legacy_v1` por padrão. Sua saída matemática continua coberta pelo baseline original. O usuário desta instalação autorizou a ativação da estratégia equilibrada. As duas estratégias usam os parâmetros versionados existentes; a versão numérica V1 não foi reescrita nem apresentada como calibrada. A estratégia é uma dimensão separada do perfil. Não há migração de schema: permanece 12.

## Evidência e incerteza

Por dia, questões novas têm precedência, depois mistas, depois repetidas não vinculadas. As modalidades não são somadas para estimar desempenho em inéditas. Os posteriores Beta(1+acertos,1+erros) e intervalos de Wilson já existentes descrevem a incerteza dos acertos exatos. Uma amostra pequena abaixo da meta não é rotulada como déficit confirmado quando seu intervalo ainda inclui a meta. Percentuais aproximados não são convertidos em contagens exatas, nem ampliam intervalos como se fossem evidência exata.

Essas medidas pressupõem condições de amostragem que uma lista selecionada por tema pode não satisfazer. Não estimam nota futura ou chance de aprovação. A segurança acumulada importada da Osler mantém seu denominador próprio e serve para triagem documental quando faltam blocos atuais; não vira acerto bruto. Sem medição objetiva suficiente, o próximo bloco continua diagnóstico.

## Intervalo e quantidade

O primeiro bloco suficiente, sem baixo rendimento, parte do intervalo inicial configurado (sete dias nos parâmetros V1). Um novo encontro precisa estar separado pelo intervalo vigente, respeitando também o mínimo de três dias; fazer mais blocos cedo não prova retenção espaçada. Resultados inferiores a 70% encurtam para o intervalo de falha. Erros críticos continuam protegidos.

Após bons encontros exatos espaçados, a qualidade é `clamp((média_posterior − limiar_de_falha)/(meta − limiar_de_falha), 0, 1)`, e o intervalo cresce pelo fator `1 + qualidade`. O segundo encontro respeita o teto do segundo intervalo; os demais respeitam limite máximo de contato e prazo da preparação. Incidência permanece na prioridade e na quantidade, sem presumir uma velocidade pessoal de esquecimento. O cenário progressivo da Evolução identifica sua hipótese de atingir a meta e respeita a mesma exigência de espaçamento, sem criar sessões ou alterar resultados observados.

A dose usa mínimo configurado + lacuna para a meta + incerteza + incidência. Não há piso de 20 por estar simplesmente abaixo da meta. Diagnóstico sem medição atual, evidência antiga e erros críticos preservam a dose diagnóstica. Manutenção menor exige amostra suficiente e bons encontros espaçados. Domínio exige acerto na meta, amostra suficiente, limite inferior de Wilson, modalidade apropriada e encontros espaçados; um único bloco não libera domínio.

Falhas em retornos vinculados são sinais adversos enquanto a cadeia permanece sem recuperação. Impedem promoção a domínio/manutenção e mantêm atenção ao tema, sem acrescentar as repetições ao posterior de questões novas. O alerta cessa quando a cadeia é recuperada, mantendo os registros anteriores intactos.

## Lotes e complementos

Quando datas de revisão geral e retorno específico ficam a até dois dias, o app pode coordená-las dentro do máximo de contato. Não adia erros urgentes, acompanhamento de cartões ou o vencimento de um lote conhecido. A janela de dois dias é uma convenção operacional, não um ótimo científico.

Um retorno de quatro questões pode ser feito como quatro, sem inflá-lo automaticamente para dez. No bloco combinado, o total inclui os lotes e ao menos a quantidade mínima de prática representativa necessária. A UI oferece registrar cada lote vinculado e o complemento separadamente, preservando vínculos, fontes e contagem. A capacidade adaptativa usa essa mesma necessidade; não subestima a carga combinada.

Se o orçamento só comportar parte de um lote, o retorno parcial é permitido e o restante continua pendente. Isso não conta como revisão completa do tema. Se o complemento ficar para um contato próximo, as tentativas vinculadas já realizadas na janela coordenada são creditadas, sem cobrar novamente o bloco inteiro. Na previsão, esse crédito é apenas projetado; nos dados reais, exige registros reais. Descanso e simulados continuam limitando as vagas. Datas devidas, referências de dose e vagas no calendário são conceitos distintos.

## Evidências e limites

Testar e recuperar o conteúdo em encontros espaçados tem suporte experimental, inclusive na educação médica. Isso sustenta o princípio do método, não os coeficientes, os sete dias iniciais ou a quantidade exata calculada para cada tema:

- [Cepeda et al., 2008](https://digitalcommons.usf.edu/psy_facpub/1766/): relação entre intervalo de estudo e prazo de retenção.
- [Butler, Karpicke e Roediger, 2008](https://pubmed.ncbi.nlm.nih.gov/18605878/): feedback beneficia acertos com baixa confiança, sem equipará-los a erros.
- [Larsen, Butler e Roediger, 2009](https://pubmed.ncbi.nlm.nih.gov/19930508/): testes espaçados com feedback melhoraram retenção em educação médica.
- [Pavlik e Anderson, 2008](https://pubmed.ncbi.nlm.nih.gov/18590367/): modelagem dinâmica de prática por item; sem IDs e histórico individual, o app não reproduz esse modelo.

Esta é uma política transparente por tema, ainda não calibrada nem validada longitudinalmente para prever retenção ou aprovação. A análise de calibração continua separada, após acumular histórico suficiente. A quantidade e o intervalo são recalculados com novos resultados.

## Entrega e verificação — 23/10/2026

Suíte completa: **672 testes passaram em 170,87 segundos**, com um aviso intencional do teste de ZIP duplicado. Inclui o baseline matemático V1 sem alterações. Após o ajuste final de contraste do texto principal, os três AppTests da UI também passaram. Detector estático sem apontamentos e whitespace conferido.

A revisão independente encontrou quatro casos: promoção após falha em lote, carga combinada subestimada, lote grande sem retorno parcial e crescimento antecipado na Evolução. Todos foram reproduzidos por regressões RED/GREEN e corrigidos. A validação real acrescentou proteção para creditar lotes feitos no contato próximo; a corrida entre prévia e gravação também possui regressão, sem perfil/auditoria parcial.

Os testes do serviço confirmaram aplicação e reversão por prévia. QA em cópia mínima do banco e dos snapshots necessários confirmou aplicação, Calendário/Ajustes sem exceções, estudos e simulados intactos. As cópias foram removidas automaticamente. Em Atenção Básica, o registro de 17/19 acertos e 15 convictas, com meta95, passou de20 questões em seis dias para referência de15 em sete dias. A previsão conferida reservou bloco combinado em30/10: quatro do lote e11 de complemento. Essas vagas continuam condicionais à capacidade e aos próximos resultados.

A ativação autorizada criou perfil12 a partir do11 e uma auditoria de mudança, após backup `data/backups/osler_20261024T003044Z_4307f4fe190e4bec.zip` (5.840.250 bytes, data do nome em UTC). Comparação confirmou todas as linhas anteriores intactas e57 arquivos de origem por hash. Meta padrão120, ajuste diário130, provas, metas por área, simulados e a troca manual do tema de hoje foram preservados. Nenhum estudo fictício foi inserido.

Conferência no navegador local confirmou a estratégia equilibrada selecionada e o plano de hoje preservado; a janela disponível tinha1280px. Não houve teste de toque em celular físico ou declaração de conformidade completa. Evidências pequenas em `tmp/balanced-*`, fora do Git. Para voltar ao código anterior, preserve o banco atual e use o backup com o código correspondente em outra pasta; preferir a reversão de estratégia dentro do app quando o objetivo for apenas restaurar o cálculo anterior.
