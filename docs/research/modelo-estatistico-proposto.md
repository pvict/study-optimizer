# Proposta estatística para um planejador local de questões

Pesquisa independente em 15/10/2026. Este documento distingue um modelo de proporção, uma política de planejamento e evidência científica sobre estudo. As constantes de planejamento abaixo são escolhas de produto ajustáveis; não foram calibradas para prever aprovação em residência.

## 1. O que os dados permitem afirmar

Cada resultado deve representar tentativas de questões, com `tema`, `data`, `questoes`, `acertos`, `tipo` (novas/repetidas), `origem` e identificador persistente. Um bloco registrado acrescenta apenas suas tentativas; salvar ou importar o mesmo bloco novamente não pode acrescentá-las outra vez. A data de importação de um relatório não é a data de estudo.

Um relatório cumulativo fornece uma âncora por tema, com total de questões e acertos. Relatórios sucessivos não são somados. A cobertura da âncora precisa ser conhecida: uma sessão já incluída no relatório não pode ser acrescentada à âncora. Quando isso for incerto, preservar os dois registros e pedir reconciliação de cobertura, exibindo totais separados enquanto houver conflito. Substituir um relatório sem reconciliar sessões também pode contar duas vezes.

Implementação mínima segura: manter a âncora mais recente, os blocos posteriores e um marcador explícito de quais blocos estão incorporados na âncora. Data de corte ajuda, mas sozinha não comprova inclusão. Relatório com contagem menor pode ser correção ou mudança de escopo; não gerar tentativas negativas nem ignorar silenciosamente.

Ausência de um tema no relatório significa dado ausente. Zero só é zero se o arquivo o declara ou se o universo completo de temas está conhecido. `n=0` significa sem evidência de questões, não necessariamente nunca estudado por outros meios. Contato por leitura ou flashcards pode atualizar última exposição, mas não fornece acertos de questões.

## 2. Estimativa de desempenho e incerteza

Modelo de trabalho: tentativas Bernoulli com probabilidade de acerto aproximadamente comparável dentro do tema. Com prior explícito `Beta(1,1)` e `s` acertos em `n` tentativas:

```
a = 1 + s
b = 1 + n - s
media = a / (a + b)
variancia = a*b / ((a+b)**2 * (a+b+1))
desvio = sqrt(variancia)
```

A conjugação Beta/binomial é documentada pelo [NIST](https://www.itl.nist.gov/div898/handbook/apr/section2/apr1a.htm). O prior uniforme é uma escolha transparente para começar, não conhecimento pessoal sobre o estudante. A previsão de contagem de acertos de um bloco futuro sob esse modelo tem distribuição [beta-binomial](https://mc-stan.org/docs/2_25/functions-reference/beta-binomial-distribution.html); o produto não precisa calcular probabilidades de aprovação.

Exibir também `s/n` como taxa observada e o intervalo de Wilson de 95%, calculável com `math.sqrt` e `z=1.959963984540054`. Fórmula: `den=1+z²/n`, `centro=(s/n+z²/(2n))/den`, `raio=z*sqrt((s/n)*(1-s/n)/n+z²/(4n²))/den`. Limites `centro±raio`. Com `n=0`, não calcular Wilson: mostrar “sem evidência”. Wilson é intervalo de confiança para a proporção, não intervalo posterior da Beta. Ver [fórmula e interpretação no NIST](https://www.itl.nist.gov/div898/handbook/prc/section2/prc241.htm).

Prior, média e desvio usam apenas `math`; não exigem SciPy. Uma aproximação normal `media±1.96*desvio` não deve ser rotulada como intervalo posterior exato, especialmente com poucos dados.

Uma média de 90% com cinco ou dez questões não confirma domínio. Mostrar contagem e incerteza ao lado. Separar histórico cumulativo e desempenho recente: blocos datados recentes podem fornecer uma segunda Beta na janela configurável, por exemplo 90 dias. Essa janela é uma política, não duração demonstrada da memória. Sem blocos recentes, usar histórico e informar que faltam medidas atuais. Não misturar decaimento fracionário arbitrário e chamar a posterior de calibrada.

Questões repetidas, seleção só de questões fáceis, consulta durante resposta e dificuldade variável quebram independência/comparabilidade. Quando possível, usar primeiras tentativas de questões novas para diagnóstico e registrar revisões separadamente. Sem identificadores individuais, chamar os números de tentativas; não afirmar quantidade de questões únicas.

## 3. Incidência institucional e hierarquia

Importação deve aceitar instituição, período, tema, contagem, denominador e fonte. Uma instituição com arquivo maior não deve dominar automaticamente: normalizar contagens por instituição e aplicar pesos escolhidos pelo usuário, cuja soma é 1. Usar a mesma definição de tema e denominador. Exibir cobertura quando há apenas parte das provas.

Incidência ausente não é incidência zero. Na ausência total de dados, o plano pode usar pesos iguais com rótulo “distribuição uniforme provisória”. Com cobertura parcial, não fingir conhecer o peso dos temas ausentes: oferecer completar dados ou usar uma política explícita de imputação/fatia exploratória.

O peso de um pai é massa total, não peso herdado integralmente por cada filho. Exemplo: cardiologia 20%, com quatro filhos sem detalhamento, pode repartir 5% por filho como aproximação declarada. Os filhos devem somar 20%, não 80%. Se há parte dos filhos conhecida, preservar um residual não especificado; inconsistências como filhos somando mais que o pai exigem correção. O plano opera sobre uma fronteira disjunta da árvore: não agenda pai e descendente simultaneamente como demandas independentes.

## 4. Prioridade e alertas: política explicável

Ponto de partida mínimo: `incidencia × max(0,0.90-media)`. Isso favorece lacunas de maior peso, mas pode abandonar temas pouco medidos, nunca vistos ou fora de contato.

Uma extensão implementável é:

```
lacuna = max(0, meta - media)
exploracao = 0.5 * desvio
idade = min(dias_desde_contato / 30, 1) se a data é conhecida; 0 se desconhecida
prioridade = peso_tema * (lacuna + exploracao) * (1 + idade)
```

`0.5`, `30 dias` e o teto `2×` são heurísticas editáveis. O bônus de incerteza sinaliza valor em medir o tema; não estima diretamente ganho por questão. A idade aumenta urgência sem inventar um percentual de memória perdido. Data desconhecida gera um aviso próprio e não é convertida em atraso de muitos anos.

Alertas podem ordenar: lacuna relevante em tema incidente; evidência insuficiente; contato vencido pela política; data desconhecida; tema sem questões registradas. Um tema pode ter várias razões, mas continua sendo uma única demanda. “Todos os temas abaixo de 90%” não deve virar uma emergência impraticável.

Pode haver uma regra de retorno de 7/14/30 dias segundo faixas de desempenho e evidência, desde que rotulada como política ajustável. O estudo de [Cepeda et al.](https://pubmed.ncbi.nlm.nih.gov/19076480/) sustenta distribuir estudo no tempo e mostra que o intervalo favorável depende do prazo até o teste. Não sustenta um calendário universal específico para temas médicos. [Roediger e Karpicke](https://www.psychologicalscience.org/journals/psychological-science/j.1467-9280.2006.01693.x/) fornecem evidência experimental de benefício da recuperação ativa para retenção posterior, sem definir quantas questões médicas uma pessoa deve fazer hoje.

Não aplicar uma curva universal `p(t)=p0*exp(-t/tau)` a todos. A [replicação de Murre e Dros](https://journals.plos.org/plosone/article?id=10.1371/journal.pone.0120644) estudou um participante e listas com medida de economia de reaprendizagem. Não identifica a meia-vida pessoal de cada tema nem uma probabilidade de acerto em prova médica.

## 5. Quantidades inteiras e dois limites globais

Entradas: minutos disponíveis, máximo de questões, minutos estimados por questão incluindo correção, máximo de temas e eventual tempo inicial para temas novos. A estimativa de minutos é ajustável e pode ser aprendida de duração registrada; não usar uma constante como se fosse universal.

Invariantes obrigatórios: `sum(questoes_por_tema) <= limite_questoes` e `sum(minutos_planejados) <= minutos_disponiveis`; todas as quantidades são inteiras não negativas. Se todos os custos são iguais `c` e não há custo inicial, `Q=min(limite_questoes,floor(minutos/c))` é o orçamento exato de questões. Com custo inicial, descontá-lo antes. Com custos variáveis, alocar apenas a próxima questão que cabe nos dois limites, sem arredondar minutos para baixo.

Separar candidatos disjuntos: novos; revisões com alerta; manutenção. Uma divisão inicial, como 20%/50%/30%, é política editável. Redistribuir sobras de grupos vazios. Pode-se converter frações em inteiros por maiores restos e desempate estável. Dentro de cada grupo, distribuir por prioridade com retorno decrescente de alocação, como `prioridade/(1+questoes_alocadas/5)`, respeitando máximo de temas e tamanho de bloco preferido. Não chamar essa política gulosa de otimizador estatístico ou de solução global ótima.

Com orçamento pequeno, blocos mínimos são preferências: cabem três questões? Planejar três, ou informar insuficiência se houver preparação obrigatória. A reserva para novos pode ser implementada por contagem de questões e tempo; nunca reservar apenas rótulos. Evitar fragmentar dez questões em dez temas. Alertas não acrescentam questões fora do orçamento: são motivos anexados às mesmas linhas do plano.

Exemplo: 60 min, máximo 40 questões, custo 3 min/questão resulta em 20 questões. Se um tema novo exige 12 min de preparo, restam 48 min e 16 questões. Um backlog de “500 revisões de flashcards” não significa 500 questões, não entra no `n` binomial e exige seu próprio custo de tempo.

## 6. Casos de aceitação

1. Zero tentativas: Beta(1,1), média 50% como prior, sem taxa observada e sem Wilson; tema marcado sem evidência.
2. 9/10 e 90/100: mesma taxa observada, incertezas diferentes; a primeira amostra demanda mais diagnóstico.
3. 0/10 e 10/10: Wilson fica dentro de [0,1] e não tem amplitude zero.
4. Importar exatamente o mesmo arquivo duas vezes: totais e plano não mudam por duplicação.
5. Âncora 100/70 + bloco 10/8: total 110/78. Âncora posterior 110/78 que inclui o bloco: continua 110/78.
6. Relatório com data de emissão sem última atividade: última exposição continua desconhecida.
7. Um tema ausente na nova importação não é apagado nem zerado automaticamente.
8. Pai com 20% e quatro filhos: peso conjunto permanece 20%; pai não recebe um segundo bloco além dos filhos.
9. Incidência nova pode ser importada a qualquer momento, muda o próximo plano e preserva histórico de estudo.
10. 60 min / 40 questões / 3 min produz no máximo 20 questões; custos iniciais reduzem a capacidade.
11. Alertas + novos + manutenção nunca excedem a soma do plano; duplicar motivos não duplica volume.
12. Orçamento zero produz plano vazio explicável; tempo insuficiente não cria tarefas que não cabem.
13. Registrar uma sessão altera desempenho, evidência e contato do tema correto; nenhuma sessão futura pode atualizar contato de hoje.
14. Flashcards e leitura afetam contato/tempo conforme seu tipo e não a contagem de questões novas.

## 7. Promessas que o produto não pode fazer

Não garantir 90%, aprovação, ganho de nota por questão, curva individual de esquecimento, intervalo ideal universal ou calendário matematicamente ótimo. “Exatamente quantas questões hoje” é a saída inteira de uma política que respeita capacidade e dados disponíveis, não uma quantidade cientificamente necessária ou suficiente para alcançar a meta. Incidência histórica orienta cobertura e não garante incidência futura. Validar a política prospectivamente com aderência, duração real e simulados representativos antes de alegar capacidade preditiva.
