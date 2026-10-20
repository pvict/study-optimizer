# Fila inicial, prioridade e compromissos — v0.17

## Problema e correção de interpretação

Um retrato com último contato e percentual de segurança não contém compromissos de revisão pessoal. Somar7dias ao contato de centenas de temas e chamar todos de pendentes transformava informação histórica em dívida. Agora cada tema distingue fila inicial de revisão comprometida por bloco registrado, retorno identificável ou acompanhamento de redução manual de cartões. Propostas diárias realmente não realizadas continuam recuperáveis pelo histórico salvo.

O calendário distribui primeiros contatos dentro das cotas de questões, limite de temas, descanso e carga escolhidos. Temas ainda sem primeira vaga permanecem na fila de prioridade, sem gerar dívida inicial. Ao projetar um contato, a previsão cria os próximos encontros **condicionalmente** ao intervalo atual; não cria sessões, acertos ou aumento de domínio. Se essas repetições futuras não couberem, o risco continua visível com os temas específicos e as opções de redistribuição.

## Modelo explícito, sem precisão inventada

Segurança da Osler representa o estado recuperado de questões conhecidas, não primeiras tentativas independentes. O posterior de acerto em novas/mistas permanece separado. Não se infere curva pessoal ou chance de aprovação a partir do retrato. “Segurança alta na Osler”, com amostra de exposição suficiente, permanece distinta de “Domínio confirmado em blocos”.

Política inicial conservadora e ajustável pelos resultados posteriores: com pelo menos10 questões distintas, usar base7dias se segurança<60%,14se<80%,21se abaixo da meta,28se atinge a meta. Com menos de30 distintas, limitar essa base a14; dados insuficientes usam7. Pendências no retrato limitam a base a7, sem fabricar IDs ou vencimentos individuais. Aplicar `ceil(base / (1 + 0.5 × incidência_relativa))`, limitar ao máximo de contato configurado e à proximidade da prova. As bases e limiares são hipóteses operacionais, não intervalos ótimos demonstrados para residência.

A pontuação utiliza `incidência × (distância_da_meta + peso_de_incerteza × incerteza + 0.1 × pendência_importada + 0.01) × (1 + min(idade/intervalo, 2))`. Quando não há bloco local, a segurança acumulada pode orientar a distância descritiva da meta, sem reduzir artificialmente a incerteza de primeiras tentativas. Blocos posteriores ao retrato prevalecem. Dados ausentes de incidência continuam distintos de zero; a reserva exploratória existente é preservada.

Compromissos vencidos precedem a fila inicial. Dentro da fila inicial, sinais manuais de erros críticos ou recorrentes preservam alerta e precedência; os demais seguem a pontuação, sem urgência inventada apenas pela idade. O destaque alto cobre aproximadamente uma semana de vagas de revisão (`temas_por_dia × (1−fração_novos) × 7`); os demais continuam ordenados e com seu estado de evidência, sem serem todos urgentes. A cota de novos e a capacidade continuam limites reais, não são aumentadas automaticamente para limpar alertas.

Retratos fora da janela recente configurada ou superados por blocos novos/mistos mais recentes continuam visíveis como histórico datado, mas não reduzem a dose diagnóstica nem sustentam a classificação de segurança alta. A versão da política compõe o identificador das prévias: uma atualização do algoritmo invalida simulações antigas sem alterar sessões ou preferências.

Blocos iniciais usam o déficit descritivo de segurança para dimensionamento quando disponível. Alta segurança com pelo menos30 questões pode dispensar o piso diagnóstico20, preservando o mínimo configurado; dados escassos e fragilidade mantêm diagnóstico maior. Doses são política inicial, não otimização causal calibrada. Com blocos locais, o modelo adaptativo anterior permanece.

## Evidência consultada e limites de transferência

- [FSRS — documentação oficial do algoritmo](https://github.com/open-spaced-repetition/awesome-fsrs/wiki/The-Algorithm): distingue dificuldade, estabilidade e recuperabilidade, com atualizações por respostas datadas. Sustenta a necessidade de histórico para um modelo pessoal; não permite tratar um percentual recuperado de tema como estabilidade individual calibrada. Esta versão **não implementa FSRS por tema** nem copia seus parâmetros para pessoas sem histórico.
- [Cepeda et al., 2008 — Spacing effects in learning](https://pubmed.ncbi.nlm.nih.gov/19076480/): referência experimental sobre relação entre espaçamento e horizonte de retenção. O registro direto não pôde ser lido nesta sessão; não foram extraídos coeficientes nem atribuídos aos intervalos acima.
- [Karpicke & Roediger, 2008 — The critical importance of retrieval for learning](https://doi.org/10.1126/science.1152408): resumo da fonte primária encontrado na busca relata benefício da prática de recuperação. Conteúdo integral bloqueado; nenhum tamanho de efeito ou fórmula foi transplantado para questões de residência.

A escolha de7/14/21/28dias e os pesos são uma política transparente para iniciar uma rotina viável, não o resultado de ajuste estatístico aos dados do usuário. O objetivo é aprender com resultados reais a partir do início do cronograma. Não promete90% ou aprovação; convicção recuperada, retenção e desempenho em inéditas continuam medidas distintas.
