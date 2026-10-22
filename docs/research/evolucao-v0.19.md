# Evolução, cenários e conquistas — v0.19

**Atualização:** a limitação de intervalos congelados descrita abaixo foi corrigida na Evolução por [cenários de espaçamento condicional](evolucao-espacamento-condicional.md). O calendário operacional preserva a referência sem sucessos futuros presumidos.

## Volume e cobertura

A jornada usa o mesmo `forecast_calendar` do plano, com carga, descansos, agenda, cotas, doses e revisões vigentes. Executar o cenário não grava sessões, planos, perfil ou domínio. O horizonte é limitado pela prova de referência e por548dias; fim passado apresenta apenas a base atual. Datas muito distantes são identificadas como limite disponível, não como fim da preparação.

Respostas realizadas no app são a soma de blocos efetivamente informados até hoje, incluindo novas e repetidas. Respostas previstas são a soma dos blocos restantes/futuros do cenário. Elas não são questões distintas novas: não há identificação global para deduplicar itens entre tentativas ou temas. O total por tema documentado nos arquivos fica separado; PDFs e retratos sobrepostos não são somados ao progresso local.

Cobertura é a união de temas específicos com questões documentadas, blocos ou acumulados positivos. Um registro agregado de uma grande área não é distribuído automaticamente entre subtemas. Cards ou contato sem questões não significam cobertura por questões. Um contato projetado acrescenta cobertura se for o primeiro, mas não melhora acerto, convicção ou domínio. Conquistas de blocos e dias reais não usam acumulados ou sessões futuras; cobertura reconhecida em documentos recebe rótulo próprio.

O calendário conserva os intervalos atuais na projeção. Isso pode estabilizar a cobertura enquanto as revisões ocupam a capacidade. A tela mostra esse custo e permite simular outra carga-base sem modificar preferências. Os resultados reais recalculam a trajetória; não se fabricam sucessos para obter uma curva ascendente.

## Rendimento observado e referência condicional

Somente blocos de questões novas, com acertos exatos, alimentam a curva de rendimento. Repetidas, revisões vinculadas, percentuais aproximados e segurança recuperada da Osler não entram nessa série. A curva de convicção usa apenas o subconjunto que informou esse valor; os denominadores são preservados por série. Sem medição, o valor é ausente, nunca zero.

A segurança importada aparece como ponto de partida descritivo separado: média dos percentuais por tema ponderada pelas contagens documentadas. Não se reconstruíram acertos inteiros a partir de percentuais arredondados, nem se assumiu identificação global para deduplicar questões entre temas. Esse resumo não alimenta Wilson, regressão ou previsão de acerto.

Para descrever a incerteza da proporção observada, usa-se Wilson. Isso pressupõe amostragem binomial aproximada; a independência e a representatividade podem falhar com questões relacionadas, seleção de temas e mudanças de dificuldade. Não é intervalo da nota da prova. [NIST — intervalos para proporções](https://www.itl.nist.gov/div898/handbook/prc/section2/prc241.htm).

Uma referência estacionária requer pelo menos30questões em dois temas normalizados nos últimos28dias, pelo menos7dias reais entre medições recentes e medição mais recente em até21dias. A janela de diversidade/quantidade usa dias corridos, não as últimas semanas não vazias. O limite de horizonte é o menor entre56dias e a duração efetivamente observada na janela recente de56dias; períodos maiores mostram insuficiência em vez de nota inventada. Semanas iniciadas na segunda servem apenas para gráfico e agregação.

Opcionalmente o sistema avalia uma tendência exploratória: pelo menos8semanas com medição,300questões e3temas na janela recente de56dias, com49dias reais de duração. Ajusta uma reta ponderada por quantidade sobre `log((acertos+1)/(erros+1))`, limitando a expansão futura por amortecimento de28dias. Quatro testes com origem temporal crescente comparam erro absoluto à referência estacionária; a tendência só é usada se a soma dos erros for pelo menos10%menor. Tema, dificuldade e seleção podem confundir a tendência, portanto não há interpretação causal ou garantia de melhoria.

A avaliação temporal segue a separação entre passado de treino e observação futura; projeções de cenário não incorporam toda a incerteza de variáveis futuras. [Hyndman & Athanasopoulos — validação e cenários de previsão](https://otexts.com/fpp3/regression.html).

A faixa futura é **exploratória**, não um intervalo de predição calibrado: meia amplitude de Wilson na janela recente com piso de5pontos percentuais, alargada por `sqrt(1+horizonte/duração_recente)`, limitada a0–100%. Os limiares de amostra, duração, ganho e amortecimento são políticas conservadoras transparentes; não são calibração comprovada para questões de residência. A meta90% permanece distinta de probabilidade de aprovação.

## Pontos de atenção e gamificação

Até a data escolhida, identificar temas sem primeiro bloco/registro, última medição fraca, contato previsto além do limite configurado ou falta de medição utilizável. Ordenação combina incidência/prioridade com natureza do sinal; dados de incidência ausentes continuam identificados. A classificação descreve o cenário, não comprova esquecimento nem cria dívida. Uma fragilidade conhecida só desaparece com nova evidência real.

Conquistas são derivadas, não persistidas como XP: primeiro bloco,100respostas locais,3dias reais de prática e cobertura documentada de25%. Marcos previstos mostram data e rótulo próprios; nunca aparecem conquistados por abrir a projeção. A jornada pode ter cobertura alta reconhecida nos arquivos e zero blocos locais sem contradição entre contagens de escopos diferentes.

O cache usa token de dados, data local e carga simulada. Toda abertura continua read-only; mudança de dados ou passagem de data invalida a simulação. Os arquivos originais e versões são preservados, sem novas dependências de produção ou alteração de schema.
