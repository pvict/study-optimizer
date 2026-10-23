# Plano de corte — demanda e capacidade

**Fonte:** especificação do lote C, política de espaçamento existente e limites de [dose por tema](dose-adaptativa-por-tema.md). Esta é uma política operacional opcional, não uma fórmula validada para retenção ou aprovação.

**Cenário:** a demanda mantém a dose e o intervalo atuais dos temas com revisão recorrente já comprometida até o horizonte escolhido. Temas ainda na fila inicial, vistos apenas no retrato importado ou nunca iniciados, não viram compromissos recorrentes por existirem no catálogo. Retornos já conhecidos entram na data correspondente; quando coincidem com o contato integral, usa-se o maior bloco, sem somar duas vezes. Retornos futuros ainda desconhecidos não são inventados. A capacidade em questões é a carga total, que também precisa atender os novos temas: soma das metas disponíveis, descontando descanso e questões já feitas hoje. Vagas efetivas também dependem do limite de temas, cotas e compromissos: por isso a prévia mostra separadamente as tentativas que o calendário consegue alocar.

A diferença entre demanda condicional e carga permanece visível, inclusive quando não há corte seguro. Não se chama esse total de quantidade necessária para aprender. A trajetória individual continua recomendando apenas o próximo bloco real.

**Proteção:** manter temas com qualquer erro aberto, sinal adverso manual, baixa convicção, alerta de desempenho, incidência desconhecida, compromisso explícito ou evidência insuficiente. Uma redução exige convicção na meta, ao menos 30 tentativas de inéditas e Wilson inferior de 80%. Repetidas, PDFs e segurança recuperada não substituem essa evidência.

Entre candidatos seguros, ordenar por menor incidência, maior convicção, maior amostra e volume já praticado. A proposta amplia o intervalo planejado pelo fator escolhido (padrão 1,5), respeitando o máximo entre contatos configurado. Adiamento do contato futuro é opcional, de 0 a 14 dias, dentro desse mesmo máximo. Contato já devido não é empurrado; lotes de respostas conservam suas datas. Reservas, extras e revisão final têm precedência.

Prévia não cria estudo. Aplicar confere token e conteúdo novamente e acrescenta `reschedule.apply`, escopo `triage`. Desfazer acrescenta cancelamento. A política é temporária; dados reais adversos passam a proteger o tema mesmo durante sua vigência. Os intervalos observados em `spacing` e os parâmetros do algoritmo não são reescritos. Intervalos planejados e observados ficam distintos.

**Limites:** um Wilson alto não garante generalização, representatividade ou independência. Menor frequência pode prejudicar retenção; a prévia não presume melhora, nem garante resolver todo déficit. Incidência histórica não prevê a composição da prova. Pode ser mais honesto mostrar que não há corte seguro do que fabricar uma rotina aparentemente viável.

