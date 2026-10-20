# Planejador implementado — 15/10/2026

Registro histórico da versão0.8. A versão0.9 usa quantidade diária de questões, sem limite por minutos, e nova UI/tabela com períodos. Atualização em [progresso-ui-questoes.md](../progresso-ui-questoes.md) e no [guia atual](../../README.md).

Este documento descreve o comportamento efetivamente entregue. A [pesquisa estatística](modelo-estatistico-proposto.md) contém alternativas e requisitos conceituais; não deve ser confundida com uma fórmula do FluidMed ou com todas as escolhas finais do app.

## Fontes e estimativa de desempenho

O catálogo usa folhas únicas do relatório Qbank completo disponível e o contexto do relatório de flashcards. PDFs são fotografias cumulativas: acerto com tentativa não identificada, respondidas não necessariamente distintas, data do PDF não usada como contato. O desempenho principal prioriza blocos novos da janela recente (90 dias inicialmente); na ausência deles usa blocos mistos, depois um acumulado manual, depois observação manual compatível e recente. O PDF só fornece contexto provisório. As fontes nunca são somadas cegamente.

Acertos exatos usam Beta(1+s,1+n−s), média e desvio. O intervalo de Wilson de 95% é calculado separadamente, com interpretação frequentista. Percentuais aproximados não viram acertos inteiros: sem contagem exata não há Wilson; o desvio exploratório 0,25 é uma hipótese de planejamento, não incerteza estimada desses dados. Havendo exatos e aproximados na mesma série, o posterior usa apenas os exatos, e a taxa informada identifica a presença de aproximação. Repetidas ficam em série própria. A evolução global de novas usa apenas blocos novos com contagem exata.

As hipóteses binomiais são limitadas por seleção, dificuldade, correlação e repetição de questões. As estimativas não são probabilidades de aprovação. Referências primárias: [Beta/binomial — NIST](https://www.itl.nist.gov/div898/handbook/apr/section2/apr1a.htm) e [Wilson — NIST](https://www.itl.nist.gov/div898/handbook/prc/section2/prc241.htm).

## Incidência e prioridade

Cada conjunto institucional é normalizado antes dos pesos relativos do usuário. Tabelas individuais completas têm preferência; uma tabela conjunta equivalente é usada isoladamente, sem duplicar seus membros. Alvos sem tabela recebem parcela uniforme sinalizada; sem alvos explícitos usa-se apenas o conjunto mais recente. Partes do mesmo contexto/data/unidade seguem a mesclagem existente. Incidência antiga não prevê a composição futura da prova.

A contagem de um pai é repartida entre suas folhas sem detalhamento, descontando filhos documentados. Os pesos finais são relativos aos dados utilizáveis. Folhas sem correspondência recebem uma reserva exploratória sinalizada, correspondente a 5% da massa mapeada antes da normalização. Zero explícito permanece diferente de ausência. Cobertura mede correspondência com o catálogo, não porcentagem de toda a prova. Uma consulta parcial não permite estimar a incidência dos temas faltantes como fato.

O escore usa peso × (lacuna até a meta + 0,5 × desvio + 0,01) × urgência. A urgência cresce até três vezes com idade/intervalo quando a data é conhecida. Sinais adversos das modalidades separadas podem ampliar a lacuna usada para agendamento sem misturar seus denominadores no posterior.

Intervalos iniciais: 3 dias para rendimento abaixo de 70%, 14 abaixo da meta, 30 com amostra exata de pelo menos 30 e bom rendimento, ou 7 nos demais casos. Redução de cartões limita a 14 dias; um novo contato reinicia esse prazo. Aproximação da prova pode encurtá-los. São regras heurísticas, não estimativas de esquecimento nem calendário individual validado.

Urgente: menos de 60% com pelo menos dez questões na série considerada, duas vezes o intervalo sem contato, ou sinal manual de erro crítico/recorrente. Alta: reforço por erro em uma modalidade com pelo menos cinco questões, atraso conhecido ou revisão após redução de cartões. Desempenho recente é calculado por modalidade; resultados repetidos/mistos adversos não ficam ocultos por uma pequena amostra de novas. Data desconhecida gera diagnóstico, sem atraso fictício. “Sem estudo registrado” não afirma que o aluno nunca viu o tema.

## Quantidades e atualização

O orçamento de questões inclui resolução e correção; os blocos anteriores do guia reservam flashcards e pausas. Inicialmente há 120 minutos num dia normal, 30 no plantão, teto de 60 questões, custo de três minutos por questão e até quatro temas. O custo passa à mediana dos últimos 20 blocos datados com duração informada. Os registros do dia descontam questões e tempo, sem aumentar a meta original. Descanso produz zero. Estudo efetivamente registrado acima do orçamento é mostrado, sem criar carga restante negativa ou compensação automática.

Revisões urgentes ocupam vagas primeiro. Havendo espaço e reserva positiva, entra um tema sem estudo registrado; a reserva inicial de 20% é mínima quando há capacidade no seu banco. O restante é distribuído por escore/(quantidade+1), uma política gulosa com retorno decrescente. Reserva zero desativa seleção forçada de novos. Não é uma otimização causal do ganho de nota.

As quantidades inteiras respeitam tempo, teto diário e limite por banco. O saldo de novas é documental: total menos respondidas no PDF e blocos novos estritamente posteriores à sua data. No mesmo dia pode existir sobreposição desconhecida. Sem data no PDF, descontam-se conservadoramente todos os blocos novos e mostra-se a incerteza. O app não tem identificadores individuais de questões e não comprova unicidade. Esgotado o saldo documental, a saída identifica repetição sugerida.

Sessões têm identidade e versões. CSV validado integralmente antes de salvar; reenvio idêntico reconhecido. Duas sessões realmente diferentes podem ter números iguais. Acumulados não são somados às sessões. Correção/desconsideração preserva eventos. Exportar um plano conserva fontes, versões das sessões, perfil efetivo, instituições/datas/IDs de incidência e versão da política. As configurações usam a versão exibida para detectar edições concorrentes.

## Evidência de pesquisa e validação

Fluxos públicos do FluidMed embasaram a utilidade; não houve acesso ao produto privado ou recuperação da sua fórmula. REA analisou o bundle público do portal de relatórios, sem executá-lo. A cobertura semântica foi parcial por limite de memória. Os limites estão em [fontes públicas](fluidmed-fontes-publicas.md) e [evidência REA](fluidmed-rea-evidence.json).

Validação real: 1.480 folhas reconhecidas, 31 questões em quatro temas para 120 minutos, com 25 minutos reservados e 118 minutos totais planejados. Os seis fluxos novos foram exercitados por AppTest. Referência de 500 revisões de flashcards mantida. Nenhuma sessão, perfil ou aplicação de cartões fictícia foi inserida. Banco migrado aditivamente para schema8; restauração verificada com tabelas, originais e exports idênticos. Resultado detalhado em [validação](../validacao-planejador-adaptativo.json).
