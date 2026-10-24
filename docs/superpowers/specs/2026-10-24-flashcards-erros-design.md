# Recuperação dos flashcards de erros

O usuário escreve cards dos erros, mas acumula sua resolução. Quer um plano por tema específico, com prioridades compatíveis com questões, incidência e rotina. Escolheu200 cards/dia. Não automatizar a Osler.

## Abordagens e decisão
1. Somar a uma fila genérica de flashcards: mistura cards pessoais com os demais, perde origem e duplica pais/filhos. Rejeitada.
2. Programar cada card com FSRS: faltam identidades, vencimentos e histórico individual. Não é inferível deste HTML.
3. Lote local auditável, planejado por temas específicos, com registro de primeira passagem e repetições separadas. Escolha de implementação: entrega viável com a evidência existente, sem substituir o espaçamento individual da plataforma.

## Dados e limites
HTML recebido:384 nós,266 pontas visíveis,8153 cards;264 ocorrências terminais correspondem a263 temas normalizados (Trauma de face5 + Trauma de Face14 conciliados em19, mantendo fontes). Dois grupos de Psiquiatria estão recolhidos (86 cards). Pais não são somados aos descendentes. Grupos recolhidos e resíduos de pais não são distribuídos arbitrariamente entre filhos. Originais e todas as importações/registros ficam preservados. Conteúdo HTML nunca é executado. A última resposta do usuário confirmou que todos esses cards são não estudados ou pendentes; esse é o escopo do lote ativo.

O escopo do arquivo (somente pendentes ou todos os criados) será identificado pelo usuário. Sem confirmação, importar como inventário com pendência não verificada; nunca chamar o total de atraso comprovado. Um novo retrato substitui a base de contagem, sem somar o mesmo acervo nem deduzir novamente registros anteriores à sua importação. Reimportação idêntica é idempotente. Data do retrato não é contato de estudo.

## Planejamento
200 cards/dia é carga separada das questões. Respeitar descanso, início e datas de simulado do plano ativo; permitir limite próprio por dia. Blocos até50 cards, completando a carga quando houver saldo. Fila usa caminho exato para cruzar dados, incidência conhecida com peso limitado, risco suavizado por Beta(1,1) apenas de acertos/erros exatos, tempo desde atividade de cards e proximidade com questões do dia. Convicção acumulada não é usada como acerto. Ausência de incidência/desempenho fica explícita e recebe sinal neutro, não zero. Fórmula é heurística auditável, não fórmula validada de aprovação.

Registrar cards diferentes da primeira passagem e repetições separadamente; acerto de recuperação opcional. Primeira passagem não comprova domínio nem elimina retornos na Osler. Não criar contatos ou respostas no histórico de questões. Desfazer registro é um evento aditivo. Escrita rejeita tela obsoleta. Cenário de conclusão é somente primeira passagem a carga constante, respeita dias bloqueados e exclui novos cards e retornos individuais desconhecidos. Nunca prometer data para zerar todas as revisões.

## Interface
Extensão Operate da identidade existente (Revenue-Centric Design e Impeccable): Flashcards abre em “Erros acumulados”, com abas Hoje, Temas, Próximos dias e Importar e ajustar. Recurso anterior de redução fica acessível em “Reduzir outras revisões”. Resumo curto também em Hoje e detalhe de Calendário, sem misturar contadores de questões. Temas específicos visíveis, caminho completo em apoio, busca digitável, tabela e lista paginada. Português simples, ajustes recolhidos, sem progresso fictício, sem novo tema visual.

## Aceitação
Mapeamento conferível; não duplicar pais/filhos; não chamar grupo recolhido de tema específico; limite200 ajustável; nenhuma mudança de meta ou estatística das questões; histórico e originais preservados; próximos dias identificados como cenário; atualização por novos HTMLs; desfazer e concorrência; testes funcionais e inspeção visual em computador e celular.
