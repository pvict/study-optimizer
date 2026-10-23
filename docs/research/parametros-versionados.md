# Estrutura de parâmetros — sem recalibrar

**Fonte:** valores efetivamente implementados no lote B, capturados antes da refatoração. `AlgorithmParameters` é um dataclass congelado; a versão 1 mantém os valores anteriores, incluindo 7/14/30 dias, reforço de 3 dias abaixo de 60%, dose com coeficientes 10/5/5, incidência 0,5, exploração de 5%, mínimo padrão de 10 e diagnóstico de 20. Demais constantes de facilidade e triagem inicial também ficam nomeadas.

Um arquivo de regressão captura 14 cenários do código anterior: estados, métricas, intervalos, doses, prioridades e alocação em modos fixo e adaptativo. A versão 1 deve produzir os mesmos valores; os novos metadados de versão são intencionais. Preferências explícitas de mínimo e máximo entre contatos continuam pertencendo ao perfil do usuário. O retorno de sete dias de lotes é uma regra operacional da plataforma declarada pelo usuário, separada da calibração da memória.

Schema 12 acrescenta versões imutáveis em `algorithm_parameters`, seleções manuais em `algorithm_selections` e revisões em `weekly_reviews`. Só a configuração padrão v1 é inserida pela migração; não são criados estudos nem seleções fictícias. Registrar uma versão futura não a ativa. Selecionar exige ação manual e conferência de versão esperada. A interface não edita coeficientes, e o sistema não recomenda nem faz troca automática.

O plano JSON exportado mantém `algorithm_version` da política e acrescenta `parameter_version`. O perfil efetivo carrega os valores da versão selecionada; os perfis antigos não são sobrescritos. Versões e seleções participam do token das prévias, invalidando propostas antigas.

**Limites:** a organização em versões não calibra nem valida os coeficientes. Poucos blocos, questões correlacionadas, seleção de itens fáceis e ausência de identidade por questão impedem alegar um modelo pessoal validado. Mudanças futuras precisam de análise e avaliação fora da amostra; não basta escolher coeficientes que deixem um calendário mais agradável.
