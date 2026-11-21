# Cobertura e calibração

Base `068e8f6`. Priorizar as lacunas de cobertura e os denominadores antes de comparar mudanças de política.

- Em Temas em atenção, mostrar quantos temas com data documentada excedem o máximo de dias configurado. Estimar a parcela da incidência documentada por tema usando as fontes e os pesos ativos. Distinguir datas desconhecidas e valores ausentes.
- Permitir filtrar os temas fora do intervalo e cruzar pouca prática com incidência alta. Usar a exposição e o peso que o plano já calcula. A seleção na tabela determina o atalho para abrir ou registrar.
- Incluir faixas de intervalo em repetidas na calibração e conservar os denominadores. O indicador é descritivo.
- Comparar cenários de dose e intervalo com a mesma capacidade. Registrar as limitações antes de propor mudança na política.
- Verificar os novos recortes, seleção após filtrar, ausência de dados e regressão do planejador. Usar dados sintéticos no navegador.

## Comparação de doses e intervalos

O pacote de scripts citado na auditoria não estava disponível. A comparação independente usou o alocador real, 200 temas sintéticos, 120 dias, 60 questões por dia, `balanced_v2` por tema e as sementes 5, 19 e 37. As duas condições estudaram em média 131,3 temas e responderam aproximadamente 7.200 questões. O piso é um mínimo aplicado pelo algoritmo. Os tamanhos finais dos blocos variam.

| Peso de incidência com último contato há mais de 30 dias | Piso 20 | Piso 10 |
| --- | ---: | ---: |
| Ganho de estabilidade igual por contato | 25,5% | 6,3% |
| Ganho de estabilidade proporcional à dose | 23,7% | 6,7% |

O peso da simulação vem do alocador. O indicador da interface usa a incidência documentada de subtemas específicos. A simulação pressupõe execução integral e não inclui erros críticos, retornos vinculados ou o consumo de tempo pelos flashcards. A dose menor é candidata a teste para diagnóstico não crítico sob sobrecarga. Medir acertos em inéditas após um prazo comum em temas comparáveis, sob carga equivalente. [Espaçamento e prazo de avaliação](https://pubmed.ncbi.nlm.nih.gov/19076480/) · [Recuperação em residentes](https://pubmed.ncbi.nlm.nih.gov/19930508/)

No modo equilibrado, 11/20 e 12/20 levaram a 3 e 7 dias, respectivamente. As faixas Wilson de 95% foram 34,2–74,2% e 38,7–78,1%. No modo legado, registrar 16/20 com convicção zero deu 3 dias e omitir a convicção deu 7 dias. No modo equilibrado por tema, ambos deram 7 dias. No modo vinculado, a informação ainda afeta a quantidade de retornos. Vale testar o intervalo com evidência amostral sem abrir mão de feedback para respostas corretas inseguras. [Feedback para acertos inseguros](https://learninglab.psych.purdue.edu/downloads/2008/2008_Butler_Karpicke_Roediger_JEPLMC.pdf)

## Verificação

Passaram 150 testes, incluindo regressão da política v1, faixas que capturam revisões feitas após oito dias, incidência ponderada com fontes de unidades diferentes e mudanças de seleção após filtrar. O painel foi aberto no navegador com dados sintéticos. Os testes de interface verificaram os dois recortes e o registro encaminhado pela seleção.
