# Temas que merecem atenção — 29/10/2026

O painel de Hoje cruza os estados já calculados pelo plano com tabelas locais de incidência. Não consulta a Osler, não muda a meta do dia, não aplica suspensão e não grava estudo. Seu propósito é permitir localizar um tema específico, conferir o motivo e abrir o tema ou registrar um resultado.

## Leitura e escopo

- **Atenção:** sinais adversos existentes, revisão prevista para hoje ou antes, afastamento que alcançou o intervalo atual, questões pendentes com retorno, incidência específica positiva sem questões registradas e histórico praticado com contato/acerto desconhecido.
- **Nunca praticados:** nenhuma questão encontrada no PDF, retrato, acumulado ou blocos disponíveis. Pode haver cartões ou contato conhecido. Não significa prova de que a pessoa nunca estudou o assunto.
- **Sem contato:** contato desconhecido ou afastamento maior ou igual ao intervalo já calculado pelo plano. O desconhecido recebe esse rótulo, sem número de dias ou atraso inventado.
- **Todos:** catálogo específico completo, sem top-N oculto; busca pelo nome ou caminho.

Áreas, especialidades de primeiro/segundo nível, pais com filhos, rollups e agregados históricos não são recomendados. Isso também exclui pais que têm conteúdo próprio: este painel se restringe às folhas específicas para evitar sugerir grupos amplos.

A primeira leitura é um resumo textual, depois vêm filtro, busca e tabela nativa. A tabela preserva incidência bruta e fonte, modalidade/amostra do acerto, convicção, contato e próxima revisão. A ação depende de um seletor explícito de tema, evitando inferir seleção de uma tabela apenas consultada. Ciência e definições ficam recolhidas. Revenue-Centric Design orientou remover indicadores redundantes e ligar informação à ação; Apple Design e Impeccable orientaram previsibilidade, hierarquia e controles nativos do aplicativo existente. Não há cartões decorativos, urgência comercial, sinais financeiros ou progresso simulado.

## Fontes e separação das medidas

`prepare_incidence` escolhe tabelas com data até o dia consultado e instituições compatíveis. O painel restringe a leitura aos contextos já selecionados por `incidence_weights`; tabelas conjuntas permanecem conjuntas. Exibe o valor original, unidade, instituições, data e identificador de tabela. Linha ancestral é contexto de grupo explicitamente **não individual**; não dispara a contagem de temas incidentes nunca praticados. Ausência permanece desconhecida, enquanto zero informado é exibido como zero.

`performance` já escolheu a base do plano: novas recentes, mistas quando não há novas, último acumulado ou observação manual. O painel exibe a proporção objetiva exata `correct/n`, com `n` e modalidade. Quando essa base não tem contagens exatas, repetidas exatas ficam identificadas como repetidas. Na ausência dessas contagens, percentual declarado é rotulado aproximado; não recebe intervalo binomial. PDF não entra como acerto objetivo do painel. Convicção de blocos e retrato da Osler permanecem identificados em coluna própria e nunca são somados ao acerto como amostras independentes.

`last_contact` vem do estado existente. Apenas uma data de contato até o dia consultado permite calcular `dias = dia - último_contato`. Data de relatório/PDF ou retrato não substitui contato. `next_review` é apresentado como previsão operacional da política atual, sem recalcular o calendário.

## Fórmulas reutilizadas e limites

Nenhum escore novo foi criado. A ordenação chama diretamente `review_policy.review_order`. Compromissos vencidos e sinais adversos seguem as prioridades já existentes. O escore do estado é calculado em `adaptive_planning.topic_states`:

```text
score = max(importance, 0.000001)
        × (gap + uncertainty_weight × uncertainty + 0.1 × imported_pending + 0.01)
        × urgency
urgency = 1 + min(age / max(1, interval), 2), se contato conhecido; senão 1
```

`gap` considera a distância até a meta segundo a base e os sinais selecionados no planejador. `importance` é massa relativa institucional, com repartição/reserva exploratória já implementadas; não é probabilidade de cobrança nem taxa de aprovação. O bônus de envelhecimento de `review_order` também é preservado: para fila inicial com prazo conhecido vencido, acrescenta `importance × (1 + wait/max(1, interval))`. Grupos, compromissos, sinais e demais desempates da função têm precedência. Esses pesos são escolhas operacionais não calibradas; o painel não os trata como coeficientes publicados ou pessoalmente validados.

Na base objetiva exata, `posterior` já usa `Beta(1+correct,1+n-correct)`, média `(1+correct)/(n+2)` e desvio dessa distribuição para a política; a taxa mostrada é a observada `correct/n`. O intervalo armazenado é Wilson, calculado em `classification.wilson_interval` com `z=1.96`. A hipótese binomial é limitada: questões selecionadas por dificuldade, repetições, dependência entre itens e mudanças de modalidade podem violar independência e comparabilidade. `n` pequeno produz incerteza alta; mesmo 100% em poucos itens não estabelece domínio.

Os intervalos vêm de `topic_spacing`, `balanced_reviews` e `review_policy`: estratégia anterior adaptada de SM-2 ou equilibrada por acerto e encontros espaçados. Na equilibrada, a evidência diária prefere novas, depois mistas e repetidas; retornos vinculados não compõem essa evidência representativa. Intervalos e doses usam os parâmetros ativos do perfil. Os valores padrão de 7/14 dias, retorno após falha de 3 dias, amostra de 30 e demais limiares são políticas do aplicativo, não valores ótimos estabelecidos pelas pesquisas abaixo. A filtragem não muda essas regras.

## Fundamentação consultada

1. Karpicke e Roediger (2007), [Repeated retrieval during learning is the key to long-term retention](https://learninglab.psych.purdue.edu/downloads/2007/2007_Karpicke_Roediger_JML.pdf), estudo primário, DOI 10.1016/j.jml.2006.09.004. Experimentos com recordação de palavras sustentam praticar recuperação para retenção posterior. Não validam os pesos institucionais nem uma previsão de desempenho médico individual.
2. Cepeda et al. (2006), [Distributed practice in verbal recall tasks: A review and quantitative synthesis](https://escholarship.org/uc/item/3rr6q10c), síntese dos próprios pesquisadores. Os resultados apoiam contatos distribuídos e mostram que o intervalo de retenção altera o espaçamento favorável. Essa relação não fornece uma agenda universal ou um prazo individual de esquecimento.
3. NIST/SEMATECH, [Confidence intervals for proportions](https://www.itl.nist.gov/div898/handbook/prc/section2/prc241.htm), fonte técnica primária do instituto. Explica Wilson e alternativas para proporções/amostras pequenas. Serve para comunicar incerteza, não para transformar o resultado do banco de questões em chance de aprovação.

A evidência apoia recuperação e espaçamento em geral; aplicar esses princípios a uma política de temas/blocos de residência é uma decisão de produto com limitações. A meta de 90% continua referência de preparação, sem garantia de aprovação.

## Validação

Testes sintéticos em memória cobrem dados ausentes/zero, fontes conjuntas e ancestrais, data futura, contexto institucional ativo, exclusão de pais, acerto/modalidade/convicção separados, contato desconhecido, ordem existente e imutabilidade. AppTest cobre tabela sem truncamento, busca, rota para o tema, registro do identificador selecionado e estados vazios. Não usam o banco ativo nem aplicam migrações.

Comando: `.venv/Scripts/python.exe -m pytest tests/test_study_attention.py tests/test_study_attention_ui.py -q`.

Temas específicos que são folhas podem ter dois níveis no arquivo; não se exige um terceiro nível inventado. Áreas, grupos com filhos e agregados históricos continuam excluídos. Nunca praticados destaca incidência específica e ordena pela importância institucional já calculada, antes dos desempates da política. Atenção e Todos preservam a ordem geral do planejador.
