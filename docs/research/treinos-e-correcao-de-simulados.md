# Treinos por área e prática de correção — v0.29

## O que mudou

Simulados conserva Programação e Resultados e acrescenta Treinos por área e Correção. Treinos são instituição × grande área, com rodízio pelas cinco áreas. Um treino de 20 questões/semana é a referência inicial, configurável para dois, outras quantidades e datas individuais; não é uma frequência cientificamente ótima. Datas passadas e resultados são preservados ao alterar a configuração. Não se alteram pesos globais de instituições.

As questões do treino são parte da carga diária. Exemplo: meta 120, treino 20, rotina por temas 100. Se fizer 22 no treino, os 100 comuns permanecem. Um resultado de área não dispensa a rotina do dia inteiro. O volume entra uma vez em Hoje, Calendário e Evolução, mesmo após conversão em blocos específicos. Sem subtemas informados, não se distribuem acertos de área por temas fictícios.

Quarta-feira após o simulado é uma sugestão de organização para corrigir e praticar erros. É editável antes do resultado. Sem temas informados, o calendário mostra a orientação e conserva a rotina comum. Após mapear erros, o usuário vê uma prévia com tema, dose e data, reservas substituídas e eventuais limites. A prática de correção usa parte da meta normal; referência até 40/dia. Doses úteis não são reduzidas arbitrariamente para caber. Só é possível aplicar quando todos os temas da seleção têm vaga no horizonte de até 90 dias. O usuário pode antecipar o início ou aumentar o limite da correção.

## Evidência versus regra operacional

Prática de recuperação distribuída e feedback têm respaldo na educação em saúde. Isso não determina, isoladamente, uma quantidade ótima de simulados semanais ou de questões por erro. [Trumble et al.](https://pubmed.ncbi.nlm.nih.gov/37615780/)

Testar-se e conferir respostas favorece a aprendizagem; condições e momento do feedback variam entre estudos. O app separa a conferência do simulado da prática posterior dos erros. Simulados não são a única forma de recuperação e não substituem o estudo regular com feedback. [Fraundorf et al.](https://pmc.ncbi.nlm.nih.gov/articles/PMC10409703/)

O intervalo adequado depende do horizonte de retenção, entre outros fatores. A quarta-feira e os pesos abaixo são decisões de organização, não intervalos cientificamente personalizados ou fórmulas validadas para alcançar 90%. As revisões gerais continuam usando a política adaptativa existente. [Cepeda et al.](https://pubmed.ncbi.nlm.nih.gov/19076480/)

## Distribuição das doses

Para cada tema errado, o peso operacional usa:

`peso = (0,1 + incidência / maior incidência do catálogo) × (1 + déficit estimado para a meta) × √erros`

Sem contagem de erros, o fator de quantidade vale 1, identificado como desconhecido. O déficit usa a média posterior já calculada quando disponível; ausência de desempenho não vira zero de acerto. A dose interpola entre o mínimo útil e a recomendação atual, proporcionalmente ao peso relativo, limitada à recomendação e ao banco conhecido. O peso não é probabilidade de erro, benefício causal ou previsão de nota. A raiz quadrada limita o domínio de um tema somente por sua contagem bruta de erros.

Se existir incidência importada exclusivamente da instituição do simulado, essa fonte é usada para a distribuição da correção. Caso contrário, o app identifica a incidência conjunta disponível. Sem fonte importada, informa isso e não atribui frequência à prova. Nenhum peso global do cronograma é modificado.

Contagens de erros sem denominador não geram taxas de acerto. Acertos com segurança recuperados na Osler não viram acertos inéditos. A anotação de erros tem versão própria, separada da nota e das conversões. Se a nota mudar, a anotação precisa de reconferência antes de uma nova distribuição.

## Integridade e limites

- Prévia recalculada e token transacional impedem aplicação sobre dados alterados.
- Planos e anotações são registros versionados no banco existente, sem migração de schema.
- As questões do próprio simulado, convertidas depois, não completam o reforço que ele originou.
- Reforço concluído não apaga o erro original nem comprova domínio.
- Simulado completo ou descanso protegido prevalece sobre treino de área. A prévia tenta encaixar conflitos em até sete dias da sugestão, dentro da série, sem duplicar datas e com separação de pelo menos dois dias das datas já ocupadas durante o encaixe. Primeiro minimiza o deslocamento; entre datas igualmente próximas prefere menor pressão de revisões (questões multiplicadas por 4 para urgente, 2 para alta e 1 para normal). São critérios operacionais de desempate, não estimativas científicas de retenção nem solução global ótima. Datas originalmente livres são preservadas.
- A prévia mostra sugestão original, data proposta e razão do remanejamento. Datas manuais de treinos precisam estar livres; o usuário pode ajustar também um tema previsto nos próximos 90 dias. A dose completa deve caber na data escolhida segundo o mesmo simulador do calendário. A nova reserva preserva a origem da correção e substitui somente a reserva daquele tema. O app mostra os efeitos nos demais temas antes de aplicar tudo num único registro reversível.
- Se não houver vaga próxima para algum treino, a prévia impede aplicar o rodízio inteiro até ajustar período, carga ou datas. Não há promessa de encaixe quando a capacidade é insuficiente. Mudanças posteriores na agenda exigem nova prévia; não há remanejamento silencioso de um plano já aprovado.
- O rodízio é cobertura de prática, não uma previsão de incidência. Não se infere domínio de uma amostra pequena nem se promete aprovação.

## Validação

Fixtures sintéticas para rodízio, capacidade, edição futura com histórico, prévias vencidas, duplicação, conversão, erros posteriores, resultado alterado e aplicação pelo formulário. QA visual isolado na porta 8602, nos tamanhos 1440, 1366, 768 e 390 pixels; dados temporários removidos. O app não acessa a plataforma Osler.
