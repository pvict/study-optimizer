# Organização integral da rotina — proposta de integração

**Estado: requisito incorporado ao projeto, ainda não implementado.**

Solicitação de 21/10/2026: integrar a organização de sono, trabalho, deslocamento,
academia, questões, correção, flashcards, simulados e descanso, utilizando os dados
locais do Osler Otimizador. Nesta etapa, não alterar aplicativo, configurações,
banco, agenda, importações ou resultados. A rotina escrita fora do app é uma
referência de disponibilidade; seus números não substituem o planejamento ativo.

## Resultado esperado

Ao abrir Hoje, entender a sequência de ações, os horários, a carga restante e se
ela cabe no tempo disponível. A quantidade de questões e os temas vêm do mesmo
planejador usado pelo aplicativo. Calendário e Evolução devem refletir a mesma
rotina, sem agendas paralelas ou metas divergentes.

A pergunta principal é: **“O que cabe no meu dia, considerando o que já tenho
para fazer?”** Um teto escolhido não comprova capacidade, e uma prévia não é
estudo realizado. Nenhum calendário deve prometer alcançar 90% de acerto.

## Evidências e limites da análise atual

A análise utilizou a pasta ativa resolvida por `osler.workspace.active_data_dir`,
com acesso SQLite em `mode=ro` e `query_only=ON`. A prévia foi calculada com os
serviços existentes, sem chamar ações de gravação ou a interface que salva
propostas diárias. Os registros e números pessoais ficam em relatório local
ignorado pelo Git; não entram nesta especificação compartilhável.

Foram identificados três limites que a função precisa resolver:

1. A carga configurada e a quantidade realmente alocada podem ser diferentes.
   O plano adaptativo respeita doses e capacidade de repetição, deixando sobra.
2. O aplicativo pode não ter sessões datadas ou tempos medidos suficientes.
   Nessa situação, duração e capacidade continuam estimadas, com origem visível.
3. Flashcards, simulados, deslocamento e compromissos pessoais não estão todos
   representados como ocupação horária no planejador atual. Não é possível
   declarar uma carga diária completa só com `max_questions`.

O registro local da conversa (sono, plantão, academia e duração dos cartões) deve
ser apresentado como **informado pelo usuário**, não como medição já salva no app.
Capturas e exportações têm data de observação; não são uma consulta ao estado
atual da plataforma externa.

## Fontes de dados e precedência

| Dado | Fonte existente | Uso na rotina |
| --- | --- | --- |
| Pasta de dados ativa | `workspace.active_data_dir` | Respeitar variável de ambiente e preferência local; não fixar `data/`. |
| Perfil e teto | `StudyStore.profile`, `AdaptiveProfile` | Preservar versão, início, modo, meta por área, proporção e prova de referência. |
| Tarefas do dia | `AdaptiveService.overview`, `plan.items` | Fonte única dos blocos, doses, temas e quantidades. |
| Realizado | `StudyStore.active`, últimas versões válidas | Abater apenas resultados registrados, sem reconstruir sessões por diferença de acumulados. |
| Dia e exceções | `StudyStore.days`, `StudyDay` | Respeitar descanso, plantão, quantidade específica e revisões adicionadas. |
| Recuperações e políticas | `StudyAgenda.active` | Manter reservas, versões, vencimentos e conflitos; não somar duas vezes. |
| Questões sem convicção | `review_queue` | Integrar retornos identificados aos blocos existentes; não criar uma segunda meta. |
| Revisões futuras | `forecast_calendar`, `capacity_limits` | Recalcular com a capacidade real dos dias, incluindo plantões e simulados. |
| Provas | `exam_goals.active_exams`, `principal_exam` | Distinguir prova cadastrada de data de referência configurada. |
| Retratos Osler | `load_planner_contexts` e exports manuais | Apoiar prioridade com data e limites; nunca declarar fila diária completa. |
| Medições antigas de carga | `planning_measurements` | Contexto datado; não dividir uma soma de 90 dias para inventar a agenda diária. |
| Guia legado | `GuideSettings` | Fonte identificada do roteiro simples, sem sobrepor o perfil adaptativo. |
| Sono, academia e deslocamentos | Novo perfil de rotina, a partir de entrada manual | Calcular disponibilidade e proteger compromissos. |
| Cartões diários e duração | Nova entrada manual ou exportação suportada | Separar previstos, realizados, novos e de revisão; origem e data obrigatórias. |

`new_share` representa questões **em temas novos**, e não necessariamente questões
inéditas do banco. Manter essa distinção ao dividir os horários. A mesma questão
não pode ser contada novamente porque apareceu na tela de lotes ou no calendário.

## Convivência com o planejamento atual

O organizador deve ser uma camada de disponibilidade e sequência sobre o motor
existente. Não substituir a prioridade dos temas por um currículo genérico fixo,
nem impor uma meta semanal escolhida em conversa independentemente dos dados.

Ordem da resolução de um dia:

1. Resolver perfil, prova de referência, fontes, resultados, agenda e exceções
   utilizando a mesma versão dos dados.
2. Bloquear sono, plantão, deslocamentos, refeições, pausas, academia e outros
   compromissos. Considerar também a véspera do plantão e o dia seguinte.
3. Reservar tempo para cartões e atividades sem quantidade de questões, com
   distinção entre dado medido, declarado e estimativa.
4. Deduzir o tempo das atividades já realizadas e dos compromissos ainda a fazer.
   Calcular janelas contíguas, sem sobreposição e sem usar a mesma margem duas vezes.
5. Converter as janelas restantes em um teto de questões, respeitando o teto
   configurado, o mínimo dos blocos, os temas por dia e as demandas de revisão.
6. Solicitar ao motor existente uma prévia com esse teto efetivo. Respeitar doses;
   não aumentar blocos para ocupar todo o horário.
7. Posicionar blocos e correções dentro das janelas. Se o lote não couber inteiro,
   adiar ou dividir apenas se a semântica do lote permitir, preservando sua origem.
8. Expor o que coube, o que ficou sem horário e o efeito sobre revisões/cobertura.
   O que não cabe não é marcado como feito, nem desaparece da pendência.

Quantidade desejada, capacidade horária, quantidade alocada e quantidade realizada
são campos diferentes. Alterar a agenda pessoal não deve sobrescrever
silenciosamente o teto global de questões.

### Tempo: contrato antes de calibrar

O campo atual `StudyEntry.minutes` é apresentado como “Minutos gastos neste
estudo”. Ele não distingue explicitamente resolução e correção. A mediana dos
últimos blocos usada em `overview` não deve ser interpretada como um cronômetro
exclusivo de resolução sem evidência.

Na futura implementação:

- Registrar o escopo do tempo: resolução, correção ou bloco completo.
- Se o custo por questão incluir correção, não reservar a mesma correção de novo.
- Se medir apenas resolução, reservar correção separadamente.
- Com escopo desconhecido, mostrar a incerteza e permitir ajuste manual; não
  converter uma estimativa antiga em medição individual.
- Aprender com tempos registrados e atualizados, sem misturar durações de cartões,
  simulados e questões de temas como se fossem o mesmo processo.
- Se faltarem dados, usar a configuração existente como hipótese explícita,
  e pedir calibração simples após os primeiros blocos reais.

O caminho legado de `overview(minutes=...)` usa `guide.daily_blocks`, que já
reserva cartões e pausas. Não o usar como conversão automática de uma janela da
nova rotina se cartões e pausas já foram descontados: isso duplicaria reservas.

### Plantão e capacidade zero

`StudyDay` já reconhece `plantao`, mas a alocação por quantidade não reduz
automaticamente a meta por esse rótulo. A rotina deve fornecer a capacidade
efetiva ao motor, e não apenas trocar o nome do dia.

O modelo atual exige uma quantidade positiva em `StudyDay.questions`. A futura
integração precisa suportar **zero capacidade de questões num dia de plantão**,
sem fingir que o usuário está de folga, inventar uma questão ou criar uma sessão
de zero respostas. A alteração de contrato deve ser explícita e compatível com
perfis antigos, sem modificar documentos ou resultados anteriores.

## Rotina semanal e anual

O esquema inicial admite quatro dias de estudo, um de simulado, um leve e um
plantão. Trata-se de modelo editável: sua carga é calculada pelos dados, não
codificada como obrigação de fazer determinada quantidade por semana.

- Marcar o plantão pela data real, pois o dia da semana varia.
- Posicionar o dia leve após ele, inclusive atravessando o limite entre semanas.
- Reservar sono antecipado na véspera e recalcular estudo/treino daquele dia.
- Garantir quatro treinos e permitir um quinto opcional, conforme preferências
  confirmadas; não prescrever exercícios, intensidade ou tratamento.
- Um simulado substitui a carga ordinária de questões na sua janela. Não somar
  automaticamente “simulado + meta inteira do dia”. A correção tem seu próprio
  tempo, podendo continuar no dia leve.
- Distribuir temas específicos a partir de prioridade, evidência e pendências
  do aplicativo. A lista inicial não é congelada para os 12 meses.
- Se a escala não estiver disponível, mostrar “Plantão ainda não informado” e
  capacidade provisória. Não inventar uma quarta-feira de trabalho.

A visão anual preserva padrões de sono, trabalho, treino e descanso, enquanto
temas e doses são recalculados em horizonte curto. Reutilizar os 14 dias do
controle de capacidade atual como referência operacional, não como modelo
validado de memória. Mudanças em dados, agenda, tempos ou escala invalidam prévias
antigas.

Datas mais distantes são **cenários**, não uma lista confirmada de pendências.
O período solicitado de 12 meses e a data de prova de referência podem terminar
em dias diferentes; apresentar ambos sem alterar nenhum silenciosamente.

As etapas anuais podem organizar adaptação, consolidação, treino das bancas e
preparação próxima às provas. Não prever que em determinado mês haverá 80%, 85%
ou 90% de acerto. Usar apenas as provas efetivamente cadastradas para a logística
de uma prova real, sem transformar uma data padrão em inscrição confirmada.

## Experiência no aplicativo

Modo **Operate**: completar o dia com poucas decisões e português simples.
Reutilizar o sistema visual em `DESIGN.md`, sem redesenhar a aplicação.

- **Hoje:** sequência por horário, próxima ação e resumo de tempo disponível,
  tempo planejado e tarefas sem horário. Manter o botão já existente de registrar
  o resultado do bloco. Não criar outro contador de questões realizadas.
- **Calendário:** permitir consultar horários do dia e a semana completa;
  compromissos pessoais e blocos de estudo compartilham o mesmo relógio.
- **Ajustes → Meta e rotina:** acomodar preferências de sono, academia, cartões,
  plantão e deslocamento. Mostrar primeiro o essencial e recolher estimativas,
  fontes e detalhes avançados.
- **Evolução:** mostrar apenas medidas reais de execução e cenários identificados;
  eventos pessoais não viram avanço de conteúdo.
- **Conflito:** explicar concretamente quanto tempo falta e oferecer reduzir
  entrada de novos temas ou redistribuir blocos. Dormir menos não é solução
  automática, e pendências comprometidas continuam visíveis.
- **Sem evidência:** “Tempo estimado: ainda não há blocos cronometrados” ou
  “A quantidade de cartões de hoje não foi informada”. Ausência não equivale a zero.

Não adicionar uma sétima navegação de topo só para esta função, nem um segundo
planejador com dados desconectados. Um fluxo de salvar a rotina pode apresentar
a prévia e aplicar uma nova versão reversível; abrir a página não aplica nada.

## Persistência proposta, ainda sem migração

Separar preferências de vida pessoal, ocorrências de compromissos e medições de
tempo dos resultados de questões. Perfis e eventos devem ser versionados e
correções devem preservar o anterior.

`routine_profiles` já existe como armazenamento legado de cenários de redução.
Não reutilizar essa tabela silenciosamente para sono/academia: o contrato é
outro. Usar armazenamento aditivo próprio e integrar sua versão ao token de
consistência. Não incrementar o schema nesta etapa.

Ao aplicar uma semana no futuro, verificar perfil, agenda, escala e fontes ainda
atuais, salvar atomicamente os novos eventos e disponibilizar desfazer. Desfazer
uma programação não apaga estudo realizado depois dela. Conservar arquivos
originais e snapshots; não executar suspensões ou reativações externas.

## Pontos de integração previstos

| Área | Arquivos existentes | Mudança futura necessária |
| --- | --- | --- |
| Entradas e estado | `study_models.py`, `study_storage.py`, `study_agenda.py` | Eventos de rotina e orçamento efetivo por data; preservar histórico. |
| Orquestração | `adaptive_service.py` | Resolver uma única fotografia e encaminhar teto efetivo ao planejador. |
| Capacidade | `study_capacity.py`, `capacity_service.py` | Usar plantões, simulados e horários nas vagas dos próximos dias. |
| Calendário | `study_calendar.py`, `study_calendar_ui.py` | Reconciliar capacidade de horas com questões e janelas reais. |
| Hoje | `study_day_ui.py` | Mostrar sequência e origem da estimativa, mantendo registro atual de blocos. |
| Ajustes | `adaptive_ui.py` e componentes de ajustes pertinentes | Preferências simples e prévia reversível. |
| Histórico de tempo | `StudyEntry.minutes`, `study_statistics.py` | Identificar escopo e qualidade das durações, sem alterar registros antigos. |
| Simulados | Novo contrato integrado ao registro existente | Vínculo único entre prova, correção e questões registradas, sem duplicar tentativas. |

Os nomes acima descrevem pontos de contato, não arquivos alterados nesta entrega.

## Critérios de aceitação para implementação

1. Perfil e dados anteriores continuam íntegros e o modo sem rotina pessoal
   conserva o comportamento existente.
2. Mesmo estado de dados gera a mesma quantidade em Hoje, Calendário e Rotina.
3. Em dias anteriores ao início, não aparecem metas ou cobranças artificiais.
4. Teto configurado, alocado, realizado e pendente são reconciliáveis por bloco.
5. Cartões da plataforma e cartões próprios têm orçamento, origem e data;
   a legenda antiga com referência fixa não é usada como demanda medida.
6. Uma questão do simulado ou lote de erros não pode contar duas vezes.
7. Correção incluída no tempo de bloco não é cobrada novamente.
8. Plantão e deslocamento não recebem estudo sobreposto; capacidade de questões
   zero é válida quando não houver janela.
9. Véspera e pós-plantão funcionam entre semanas e meses sem duplicar ocorrências.
10. Um conflito não remove sono/refeições silenciosamente nem esconde revisões.
11. Salvar horários não registra acertos, convicção, contatos ou estudo concluído.
12. Uma medição antiga, um acumulado e uma pendência sem data não viram carga
    diária atual confirmada.
13. Prévia fica inválida quando perfil, sessão, fonte, rotina ou escala muda.
14. Salvar/desfazer é versionado; resultados realizados continuam preservados.
15. Visão de 12 meses é condicional e não inventa melhora, retenção ou aprovação.
16. Computador e celular mantêm ordem, rótulos, teclado e ações essenciais; detalhes
    avançados ficam recolhidos, com teste visual quando houver implementação.

## Base de design e referências internas

- Revenue-Centric Design: **camada acionável** — o painel orienta o próximo passo
  a partir dos dados, com menos indicadores concorrentes. [Richard, 10/07/2026](https://x.com/richardrx/status/2075623473565647202).
- Revenue-Centric Design: **filtro de funcionalidades / Swiss Knife Index** —
  ampliar o fluxo principal em vez de criar um organizador genérico paralelo.
  [Richard, 26/05/2026](https://x.com/richardrx/status/2059236567533650119).
- [Rotina adaptativa e limites](capacidade-adaptativa-v0.18.md).
- [Fila inicial sem dívida artificial](priorizacao-inicial-v0.17.md).
- [Segurança acumulada não é primeira tentativa](seguranca-acumulada-osler-v0.16.1.md).
- [Evolução: cenários e resultados](evolucao-v0.19.md).

## Escopo desta entrega

Somente documentação do requisito e análise local de carga. Sem alterações em
`app.py`, `osler/`, testes, dependências, estilos, banco, configurações ou agenda.
Sem acesso à plataforma Osler. A implementação permanece para uma etapa posterior,
conforme a instrução de não mudar o aplicativo agora.
