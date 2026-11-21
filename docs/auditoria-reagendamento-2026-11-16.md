# Auditoria do reagendamento — 16/11/2026

## Parecer

O reagendamento é utilizável como **organizador de carga e reservas**. Não é um modelo validado de memória, uma prescrição de carga ideal ou uma previsão de aprovação. A base científica sustenta praticar recuperação com feedback e distribuir contatos ao longo do tempo; não estabelece que a fórmula deste app, blocos fixos ou um prazo universal de recuperação sejam ótimos.

Esta alteração torna a situação verificável em Hoje: atraso de estudo, reserva com data atual e necessidade de nova data são estados distintos. O atalho busca primeiras vagas para pendências sem reserva atual, mantendo as reservas dos outros temas. Uma prévia pode ser descartada, aplicada ou desfeita; não registra estudo.

## O que a implementação faz

| Regra examinada | Avaliação e limite |
|---|---|
| Atraso exige contato vencido ou bloco salvo e não realizado | Apropriado para não transformar data do relatório ou inventário de cards em falta de estudo. Não prova que não houve estudo fora do app. |
| Repetidas faltas não somam automaticamente doses idênticas | Evita dívida artificial; `collect_backlog` usa o maior saldo/dose reconhecido, descontando registros reais e conclusões. |
| Vencimento original é preservado ao reservar nova data | Correto: reservar não equivale a aprender, concluir ou apagar atraso. |
| Prioridade combina atraso relativo, incidência e desempenho | Heurística plausível de triagem. Os multiplicadores não foram calibrados contra esquecimento ou acerto em prova. A variável interna `risk` não é probabilidade. |
| Primeira vaga com cota e bloco completo | Decisão logística simples, não otimização global de aprendizagem. Pode deixar vaga ociosa quando o bloco não cabe inteiro. |
| Cotas de novos/revisões, total, temas e dias protegidos | Controles operacionais adequados. Preservam descansos, simulados, reservas e resultados já registrados. Não demonstram que a carga cabe em cinco horas. |
| Sem espaço, a prévia lista temas não encaixados | Correto. Ao aplicar uma redistribuição, reservas anteriores dos temas selecionados são substituídas, inclusive dos que ficaram sem vaga; isso aparece antes de confirmar e é reversível. |
| Dados mudaram depois da prévia | Token e recálculo no serviço impedem aplicar um resultado antigo silenciosamente. Não depende apenas do botão. |
| Desfazer | Acrescenta evento de cancelamento; não apaga resultados reais nem o histórico de reservas. |
| Retornos de questões em sete dias | Regra informada pelo usuário sobre a Osler. Não é um intervalo cientificamente ótimo para todo item. Não confundir com FSRS dos flashcards ou revisão por tema. |

Arquivos examinados: `study_replanning.py`, `adaptive_service.py`, `study_agenda.py`, `adaptive_planning.py`, módulos de recuperação por quantidades e a apresentação de Hoje/Calendário. Não há migração ou alteração direta de tabelas nesta entrega. O app continua salvando eventos pelo armazenamento já conectado ao Supabase. Não houve alteração dos dados de produção para testar o redesenho.

## Correções desta entrega

1. Contar **temas** com data atual, em vez de comparar temas atrasados com quantidade de reservas (um tema pode ter várias).
2. Data passada e reserva concluída não contam como uma nova data válida. Mostrar a data efetivamente salva e a situação.
3. Remover a afirmação de que todos os atrasados “pedem nova data”. Um tema pode estar atrasado e já ter vaga futura.
4. Atalho em Hoje: buscar até 90 dias, sem aumentar a carga, priorizando somente quem precisa de data. Os 90 dias são um horizonte máximo de busca; não uma recomendação de adiar cada revisão por 90 dias. Quando todos têm data, refazer a distribuição é opcional e explícito.
5. Reduzir informação sempre aberta e usar cores suaves com rótulos textuais, mantendo acesso ao histórico e aos controles externos ao final.
6. Corrigir dois defeitos do motor identificados na revisão: modos avançados descartavam reservas externas/de treinos ao calcular cotas, e trocas manuais não descontavam vagas da prévia. Agora as reservas derivadas participam do cálculo sem ficarem congeladas no evento; dias exclusivos externos ficam protegidos e trocas ocupam suas questões e vagas.
7. Vincular desfazer ao ID e ao token originalmente exibidos, inclusive se outra sessão criar um reagendamento antes do clique. A confirmação identifica o evento.
8. Impedir reservas em temas afastados/substitutos de uma troca no mesmo dia e em retornos declarados indisponíveis. Descontar o treino por área concluído uma única vez: sua reserva já reduziu a cota ordinária.

As datas são reservas baseadas no estado conhecido: se outro compromisso não for concluído, surgirem novas revisões ou a rotina mudar, a execução deve ser conferida novamente. Não são garantia imutável de disponibilidade futura.

## Evidência e o que ela não permite concluir

**Maye e Hurley, 2026.** Revisão sistemática e metanálise de educação médica encontrou desempenho superior com repetição espaçada. As intervenções e avaliações variaram; os autores ainda pedem estudos sobre desenho e efeitos duradouros. Isso apoia o princípio do espaçamento, não valida este agendador, nem converte efeito médio em pontos percentuais pessoais ou chance de aprovação. [Artigo e DOI](https://doi.org/10.1111/tct.70353).

**Trumble et al., edição 2024, publicação online 2023.** Revisão em profissões da saúde encontrou benefícios frequentes de prática distribuída e recuperação. A heterogeneidade e a necessidade de medir tempo dedicado impedem tratar uma quantidade única de revisões como dose ótima universal. [Texto integral](https://pmc.ncbi.nlm.nih.gov/articles/PMC11078833/) · [DOI](https://doi.org/10.1007/s10459-023-10274-3).

**Cepeda et al., 2008.** Experimento de retenção com intervalos longos mostra que o espaçamento mais favorável depende do tempo até a avaliação. Não autoriza impor sete dias, 45 dias ou 60 dias a todos os conteúdos e alunos. [Publicação original](https://www.psychologicalscience.org/journals/psychological-science/j.1467-9280.2008.02209.x/).

**Documentação oficial do Anki/FSRS.** Retenção desejada e carga interagem; limites e reagendamento são opções de um produto específico. São documentação técnica, não ensaio de eficácia clínica/pedagógica e não prova de que a Osler possua os mesmos controles. [Manual](https://docs.ankiweb.net/manual/deck-options).

Fontes verificadas em 16/11/2026. Esta é uma auditoria focal do método e do código, com referências selecionadas; não uma revisão sistemática exaustiva de toda a literatura. Nenhuma das fontes valida uma meta pessoal de 90% de acerto no conjunto de provas de residência brasileiras.

## Sustentabilidade matemática

Para uma fila de revisões, uma aproximação contábil é `B(t+1) = max(0, B(t) + A(t) - C(t))`: saldo anterior, novas revisões que vencem/retornam e revisões efetivamente concluídas. Se a entrada média se iguala ou supera a capacidade efetiva, espalhar datas não elimina a fila. As respostas de hoje ainda podem gerar revisões futuras.

O teto de 550 cards prontos é uma capacidade declarada, não uma taxa cientificamente ótima. O cálculo `saldo / 550` só seria prazo de esvaziamento se não houvesse entradas, novos vencimentos ou reaprendizagem. A meta de questões é separada dos cards e deve incluir revisões externas e treinos; não se deve somar esses componentes novamente.

**Cinco horas ainda não são um teto rígido do app.** A estimativa de minutos por questão não abrange de forma confiável todos os cards, correções, simulados e pausas. Até existir medição suficiente e reserva conjunta de tempo, a quantidade planejada não pode ser apresentada como garantia de caber em 300 minutos. Nem reagendar pode garantir ausência de esquecimento.

## Próximos passos prioritários

- Medir tempo real dos componentes, incluindo correção e cards; depois construir orçamento conjunto de 300 minutos com margem e incerteza, em vez de simplesmente elevar cotas.
- Validar prioridades em dados futuros: acerto em questões novas e simulados comparáveis, separado de questões repetidas e reconhecimento nos cards. Analisar carga, atrasos e aderência junto do resultado.
- Examinar doses que não cabem e necessidade de fracionamento por tema antes de ampliar metas. Não suspender grandes áreas só pelo rótulo HY/não-HY.
- Manter resultados, erros e registros originais. Alterar uma variável de rotina de cada vez e comparar períodos com exposição e tempo conhecidos; não inferir causalidade de uma melhora isolada.

O redesenho facilita o uso e a inspeção de datas. A validação longitudinal e o orçamento real de tempo continuam pendências explícitas.
