# Relatório de calibração — somente leitura

**Fonte:** especificação C3, contagens exatas do histórico local e faixas Wilson já existentes no projeto. O script não calibra, não recomenda valores e não altera o banco.

`scripts/analise_calibracao.py` abre SQLite com `mode=ro` e `query_only`. Não inicializa Repository nem stores; funciona com banco vazio ou antigo. Gera Markdown e CSV fora da pasta do banco ativo, protege células CSV e recusa sobrescrever arquivos existentes. A saída padrão fica em `analises/calibracao`, ignorada pelo Git.

Para cada bloco de origem com acertos exatos, considera somente sua primeira revisão seguinte. Vínculos `review_of` têm preferência; sem vínculo, usa a origem anterior mais próxima no mesmo tema, identificando a associação como observacional. Havendo vínculo explícito, uma repetição não vinculada não ocupa o lugar dele. Correções usam a última versão ativa, sem somar versões, PDFs ou acumulados.

Mostra acerto em repetidas nas faixas inclusivas de 2–4, 5–9, 10–18, 19–25 e 26–35 dias, por modalidade de origem, faixa de desempenho inicial e tipo de vínculo. O CSV usa `lag_min_days` e `lag_max_days` para essas faixas e `lag_days` para o intervalo exato da análise de convicção. Cada resultado traz acertos, tentativas, sessões e combinações de tema e dia. Grupos com menos de 30 tentativas ou cinco combinações recebem aviso de amostra pequena. O desempenho anterior influencia o prazo de revisão, então a comparação entre faixas descreve as associações observadas.

Tempo por questão é a soma dos minutos dividida pela soma de questões em blocos com duração, por área e modalidade. Aderência usa o plano diário salvo mais recente, limita execução à quantidade prevista por tema/dia e dispensa programações especiais aplicadas. Ausência de plano não vira falta. Banco sem dados produz relatório com “Dados insuficientes”, sem inventar valores.

**Limites:** blocos não identificam cada questão, e tentativas do mesmo tema podem estar correlacionadas. Questões fáceis, consulta, seleção do aluno e duração omitida enviesam os resultados. A relação entre convicção e revisão não é causal. Dados futuros, fictícios e simulados externos não são acrescentados.

No app, abra **Ajustes → Meta e rotina → Avançado → Parâmetros do algoritmo e análise de calibração → Ver acerto por intervalo**. O botão consulta o histórico ativo no momento da solicitação. Para exportar o relatório completo, execute `python scripts/analise_calibracao.py`.
