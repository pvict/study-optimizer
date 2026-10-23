# Relatório de calibração — somente leitura

**Fonte:** especificação C3, contagens exatas do histórico local e faixas Wilson já existentes no projeto. O script não calibra, não recomenda valores e não altera o banco.

`scripts/analise_calibracao.py` abre SQLite com `mode=ro` e `query_only`. Não inicializa Repository nem stores; funciona com banco vazio ou antigo. Gera Markdown e CSV fora da pasta do banco ativo, protege células CSV e recusa sobrescrever arquivos existentes. A saída padrão fica em `analises/calibracao`, ignorada pelo Git.

Para cada bloco de origem com acertos exatos, considera somente sua primeira revisão seguinte. Vínculos `review_of` têm preferência; sem vínculo, usa a origem anterior mais próxima no mesmo tema, identificando a associação como observacional. Havendo vínculo explícito, uma repetição não vinculada não ocupa o lugar dele. Correções usam a última versão ativa, sem somar versões, PDFs ou acumulados.

Mostra acerto de repetidas em intervalos exatos de 3, 7, 14, 21 e 30 dias, separados por modalidade de origem e faixa de desempenho inicial. Relaciona convicção inicial e acerto da revisão seguinte descritivamente. Expõe tentativas, sessões e combinações tema/dia; grupos com menos de 30 tentativas ou cinco tema/dias recebem aviso de insuficiência. Esses limites são critérios descritivos, não autorização para ajustar um modelo.

Tempo por questão é a soma dos minutos dividida pela soma de questões em blocos com duração, por área e modalidade. Aderência usa o plano diário salvo mais recente, limita execução à quantidade prevista por tema/dia e dispensa programações especiais aplicadas. Ausência de plano não vira falta. Banco sem dados produz relatório com “Dados insuficientes”, sem inventar valores.

**Limites:** blocos não identificam cada questão, e tentativas do mesmo tema podem estar correlacionadas. Questões fáceis, consulta, seleção do aluno e duração omitida enviesam os resultados. A relação entre convicção e revisão não é causal. Dados futuros, fictícios e simulados externos não são acrescentados.

Próximo passo: usar o app diariamente por 6 a 8 semanas e então executar `python scripts/analise_calibracao.py`. O relatório serve para avaliar a informação disponível antes de qualquer proposta futura de mudança manual.
