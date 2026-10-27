# Revisões sustentáveis — política4.2

## Problema encontrado

O perfil atual usa a estratégia equilibrada. O cálculo somava lotes pendentes a um complemento obrigatório mínimo, mesmo quando as repetições já ocupavam a dose recomendada. O feedback também escolhia a data da revisão geral em vez do próximo retorno real, carregando pendências de datas anteriores para essa explicação.

No exemplo investigado, as tentativas foram15/22 e17/23, com7e11acertos convictos. Isso produz lotes reais de15e12questões; eles continuam preservados. As37do feedback eram27pendentes+10, não uma dose científica validada de37novas questões. A recomendação geral calculada era16. O próximo encontro real é o lote15em30/10; em03/11, o lote12pode integrar a revisão geral16, ficando4questões de complemento se os retornos anteriores tiverem sido feitos. Se houver retorno anterior ainda pendente, a tela usa os registros atuais e informa a carga restante; não pressupõe sua conclusão.

## Matemática implementada

Continua o posterior Beta(1,1) existente para cada modalidade estatística: média`(k+1)/(n+2)` e desvio-padrão correspondente. Questões novas, mistas e repetidas não são somadas indiscriminadamente; os retornos vinculados não viram tentativas novas. A faixa95% do produto é Wilson, não um intervalo de credibilidade Beta nem probabilidade de aprovação.

A dose do tema mantém os parâmetros atuais: piso configurado + parcela pela lacuna à meta + incerteza amostral + incidência. Usar a média agregada, em vez de escolher sempre a menor entre ela e o último bloco. Uma falha objetiva forte(<60%) ou queda com faixas Wilson não sobrepostas mantém proteção contra diluição pela média antiga. A não sobreposição é um sinal conservador de produto, não teste formal de hipótese.

O orçamento conjunto passa a ser`max(dose geral ainda necessária, lotes devidos)`, respeitando banco conhecido e carga diária. O complemento é a diferença positiva; não existe soma automática de dez. Quantidades de lotes são eventos pendentes reais, podendo crescer se surgirem mais erros. Não prometer redução monotônica após qualquer lista.

Falhas fortes mantêm reforço curto; resultados intermediários mantêm o primeiro intervalo. Bons resultados objetivos em encontros suficientemente espaçados permitem expansão progressiva, com limites configurados e horizonte da prova. A média antiga de uma fase ruim não mantém3dias depois de recuperação recente documentada. Nenhuma mudança nos dados de entrada ou no parâmetroV1 imutável.

Um retorno vinculado e seu complemento, quando suficientes perto da data geral, evitam dose duplicada imediata mesmo se registrados em dias adjacentes. Podem mover o próximo contato operacional pelo intervalo inicial, limitado pela prova; não aumentam estabilidade, streak, domínio nem posterior de novas. Considera-se o contato mais recente, e uma falha forte posterior impede o adiamento. Erro recente com faixa Wilson inteiramente abaixo do limiar de falha também é protegido, sem ser diluído por acertos em outro grupo/modalidade. Os erros remanescentes continuam com identidade e prazo próprios. Na previsão, a execução de um lote suficiente aguarda resultado real antes de sugerir outro bloco geral; não simula aprovação ou recuperação.

## Base científica e alcance

[Cepeda et al.,2008](https://doi.org/10.1111/j.1467-9280.2008.02209.x) investigaram mais de1350participantes, mostrando que o benefício do intervalo depende do horizonte de retenção e não cresce indefinidamente. [Texto disponibilizado pelo laboratório dos autores](https://laplab.ucsd.edu/articles/Cepeda%20et%20al%202008_psychsci.pdf).

[Rawson et al.,2018](https://pubmed.ncbi.nlm.nih.gov/29431462/) documentam ganhos de reaprendizagem em múltiplas sessões, apoiando a manutenção de contatos posteriores em vez de retirar um tema após uma boa lista.

[Eglington e Pavlik,2020](https://doi.org/10.1038/s41539-020-00074-4) investigam agendamento adaptativo e eficiência com medidas por item. O app dispõe de resultados agregados por tema, não das identidades/latências necessárias para calibrar esse tipo de modelo pessoal. O artigo apoia investigar eficiência; não valida os coeficientes deste produto para residência médica.

Estas são heurísticas explícitas de planejamento apoiadas nesses princípios, não uma fórmula ótima demonstrada para90% de acerto. Com68–74% em apenas dois blocos, não há evidência de domínio para impor espaçamentos longos. A meta90% permanece; aprovação não é estimada nem garantida.

## Verificação

Recálculo de1480temas por abertura somente-leitura do banco e cálculo em SQLite em memória. Nenhuma gravação de migração ou análise ocorreu no banco original. A comparação local registrou4intervalos maiores; doses gerais do retrato atual mantiveram seus valores. A retirada da soma obrigatória afeta os encontros futuros em que lotes e tema coincidem, e o feedback passa a mostrar a data/quantidade do encontro correto. Não afirmar que1480intervalos aumentaram.

Testes novos cobrem nomes arbitrários, datas distintas dos lotes, igualdade entre orçamento/capacidade/feedback, recuperação após resultado antigo ruim, oscilação amostral, retorno suficiente, falha posterior, limite da prova e projeção sem sucesso fictício. Expectativas antigas de soma obrigatória foram atualizadas intencionalmente em tests/test_balanced_reviews.py e tests/test_review_strategy_service.py.

QA visual em1366e390px: campo numérico sem outline interno/externo adicional, borda única1px; botão continua com foco de teclado3px; digitação e largura preservadas. Capturas de feedback e campo em evidencias/revisoes-sustentaveis são **sintéticas**; os cenários temporários foram removidos. Atenção na leitura do CSSOM: outline-width pode retornar3px mesmo com outline-style:none; a ausência do traço foi confirmada pela propriedade style e pela captura.

A revisão independente solicitada ao subagente não pôde ser concluída por limite de uso da ferramenta. Foi feita revisão direta dos fluxos e dos casos de falha, além da suíte automatizada e do navegador. Resultado final da suíte registrado no plano de execução.
