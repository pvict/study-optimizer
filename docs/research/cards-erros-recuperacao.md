# Recuperação dos cards pessoais de erros — v0.26.0

**Atualização0.26.1:** o plano agora usa decks inteiros, com referência diária e até10% de margem, substituindo as rodadas de50 abaixo. O print adicional de Psiquiatria completou os86 cards antes sem subtema: todos os8153 agora têm identificação entre268 temas. Veja [a atualização e suas verificações](decks-inteiros-psiquiatria.md). O restante deste documento registra a entrega original0.26.0.

Em24/10/2026, o usuário confirmou200 cards/dia, separados das questões, e esclareceu por último que todos os cards do HTML recebido são não estudados ou pendentes. Essa correção substitui a resposta anterior de que haveria cards já revisados misturados. O arquivo é tratado como lote a realizar, sem alegar que todos venceram na mesma data.

## Arquivo recebido

384 nós,266 pontas visíveis e8153 cards.264 ocorrências terminais viram263 temas normalizados, pois “Trauma de face” (5) e “Trauma de Face” (14) pertencem ao mesmo caminho normalizado:19 cards, com as duas grafias preservadas.8067 cards têm tema específico.Os86 restantes estão em dois grupos recolhidos de Psiquiatria: Transtorno por Abuso de Substâncias (10) e Transtornos do Humor (76). Não são atribuídos aos filhos por estimativa. Pais conferem com a soma dos filhos e nunca entram uma segunda vez.

O parser lê somente texto, rótulos e níveis do DOM; não executa scripts, recursos externos ou instruções contidas no arquivo. O original imutável é guardado em exports/error-cards/<sha256>.html e incluído no backup normal do app. A árvore e as ações ficam no diário aditivo study_plan_runs, com namespace error_cards.*, sem migração do schema12 e sem criar sessões de questões.

## O que o plano mede

Primeira passagem significa cards diferentes desse lote que o usuário respondeu e registrou. Não é domínio nem prova de retenção. Repetições contam na carga diária, mas não são descontadas novamente do saldo do lote. Quantos foram lembrados antes de virar é opcional e permanece um resultado de recuperação de cards, separado dos acertos em questões. O algoritmo individual da Osler continua cuidando das reapresentações; o HTML não contém IDs de cards, vencimentos, estabilidade de memória ou resultados individuais que permitiriam substituí-lo com rigor.

O saldo próprio começa no retrato importado. Um novo retrato substitui a base e não deduz novamente estudos anteriores à importação; o histórico permanece consultável. Reimportar o mesmo conteúdo e escopo não reinicia a contagem. Alterações usam token de eventos consistente com o retrato mostrado e rejeitam telas obsoletas. Desfazer acrescenta um evento e não apaga o registro original.

## Prioridade e carga

Usam-se apenas caminhos exatos normalizados. Para acertos/erros exatos nas questões, p=(acertos+1)/(n+2), correspondente a uma suavização Beta(1,1). Sem amostra exata, o sinal fica desconhecido e neutro. A convicção recuperada da Osler nunca é convertida em acerto.

Score=(0,5+0,5×incidência normalizada)×(1+risco)×(1+min(dias sem registro de cards,28)/28). Risco=1−p quando há amostra; caso contrário0,5. Incidência desconhecida recebe0,5; conhecida usa o sinal já calculado pelo planejador, limitado a[0,1]. Temas presentes nas questões de hoje recebem multiplicador1,15. Empates usam saldo e caminho. Esses pesos, o limite de50 por bloco e o multiplicador são **heurísticas de triagem**, sem validação como dose ótima ou probabilidade de aprovação. A data do retrato serve só de marco da fila: não é declarada contato de estudo.

A alocação percorre a fila em rodadas de até50 cards por tema e completa a carga com múltiplos blocos quando há poucos temas. Os temas concluídos continuam acessíveis para registro de repetições. Não há teto silencioso de um bloco por tema. A carga padrão é200, ajustável globalmente ou em um dia;0 pausa. Descansos, início da preparação, fim do período, simulados e descanso final vêm da rotina existente. Um ajuste explícito de cards para um dia tem precedência. A meta e as prioridades das questões não são alteradas.

## Cenário e evidência

A previsão simula apenas esgotar a primeira passagem pelo lote identificado, sob carga constante e rotina salva, com dias não realizados ainda como hipóteses. Não grava estudo, melhora, cards dominados ou retornos individuais fictícios. No teste com a cópia mínima dos dados reais,8067 cards a200 por dia de estudo chegaram a09/12/2026, com pausas da rotina. Isso começa no dia de estudo23/10, que vai até04h de24/10; novos cards, repetições, mudanças de carga e dias não realizados alteram o cenário. Os86 cards sem subtema ficam fora dessa data. Não é uma promessa de zerar todas as revisões.

[Trumble et al.,2024](https://pubmed.ncbi.nlm.nih.gov/37615780/) e a [revisão de educação digital espaçada,2024](https://www.jmir.org/2024/1/e57760/) apoiam prática de recuperação e distribuição temporal na formação em saúde. Elas não determinam nossos pesos de fila ou uma carga universal de200 cards. Nenhuma skill encontrada para autoria/Anki foi instalada como se fornecesse esse modelo estatístico.

## Uso

Flashcards → Erros acumulados → Hoje: abra os temas indicados na Osler e registre o que fez. Temas oferece busca, lista e tabela; inclui temas com primeira passagem já registrada para lançar repetições. Próximos dias mostra o cenário e permite baixar o planejamento. Importar e ajustar recebe novos HTMLs, mostra prévia e permite alterar a carga. A ferramenta anterior continua em Reduzir outras revisões. Hoje e o detalhe do Calendário apresentam um resumo separado dos cards.

## Verificação da entrega

Suíte completa:707 testes passaram em187,04s, com um aviso intencional sobre ZIP duplicado. Uma regressão adicional de registro de repetições em tema concluído passou separadamente; a validação focada com os recursos anteriores de redução passou47 casos. A revisão independente reproduziu três P2 e conferiu as correções com suas três regressões aprovadas, sem outro P1/P2 identificado.

A cópia mínima dos dados reais confirmou200 cards propostos,8067 de saldo identificado,86 sem subtema e manutenção exata do plano de questões, dos eventos de estudo e dos perfis. O estudo de teste existiu apenas na cópia descartável, removida automaticamente. A auditoria do banco ativo conferiu as30 tabelas e não encontrou alteração ou remoção de linhas anteriores; foram acrescentados somente o retrato e a configuração de cards. Nenhum resultado fictício foi gravado. O original do HTML foi preservado e o schema continua12.

Inspeção do app real em1280×720 e390×844: blocos e navegação legíveis, superfícies existentes, ações acessíveis; busca por Diverticulite trouxe14 cards no caminho completo; Próximos dias mostrou09/12/2026 com premissas e exclusão dos86 sem subtema. Abas no celular mantêm a rolagem horizontal nativa. Viewport restaurado após o teste. Isso não é uma auditoria completa de acessibilidade, toque físico ou todos os dispositivos.

O detector não encontrou apontamentos nos arquivos de UI Python. Ao incluir o CSS compartilhado, sinalizou dois itens preexistentes: o traço inferior das abas e o tamanho legado1,55rem já descritos no DESIGN.md. Não foram alterados estilos alheios a esta função para eliminar esses avisos.
