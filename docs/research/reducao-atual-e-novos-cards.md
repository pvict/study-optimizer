# Redução atual e novos cards dos blocos — desenho e execução

Pedido24/10/2026: atualizar a lista de redução com evidência atual, torná-la curta e simples e integrar os cards criados na Osler durante o estudo. Usuário escolheu informar a quantidade criada ao registrar cada bloco. Execução autorizada, sem ciclos de aprovação. Uso local, sem acessar ou automatizar conta Osler.

## Decisões

Reutilizar o diário versionado de questões: StudyEntry.cards_created, inteiro não negativo, padrão0, permitido apenas em blocos de tema específico. O número é informado pelo usuário, não inferido de erros. Salvar/editar/desconsiderar o bloco altera uma única fonte de verdade e a fila de cards é projetada a partir das versões ativas. Não se cria sessão de estudo de flashcards, não aumenta acertos nem altera convicção. Campo e feedback no fluxo já usado; nenhum novo formulário obrigatório por card.

O HTML original continua sendo uma fonte separada. A fila efetiva soma os novos cards criados em sessões ainda não abrangidas pelo retrato. Novas importações capturam o corte de eventos; sessões já existentes, cujo primeiro registro tem dia até o dia do retrato, presumem-se incluídas no novo arquivo e não entram duas vezes. Um arquivo de ontem não absorve cards de blocos de hoje. Para retratos legados, usar timestamp UTC auditado da importação para obter o corte. Versões/correções de sessões novas contam uma vez; sessões já absorvidas pelo retrato não são reintroduzidas. Sem HTML, cards informados nos blocos podem formar fila própria. Originais e progresso ficam intactos; divergência entre quantidade criada corrigida e estudo já realizado gera aviso, sem apagar estudo ou descontar o saldo de outros temas.

A capacidade de novas primeiras passagens continua pausada em0, escolha atual de proteção da rotina. Registrar novos cards não reativa a meta200. Questões mantêm meta e algoritmo. Isso é integração automática após a entrada curta do usuário, não sincronização em tempo real ou cópia do texto dos cards da plataforma.

## Sugestões de redução

Criar uma leitura atual em PracticalReductionService sem retirar APIs e registros legados. Dados: catálogo e estados do planejador atual, fontes com data, incidência conhecida nas instituições, acertos/erros recentes, observações manuais, convicção separada e novos cards dos blocos. PDF isolado não supera um sinal atual adverso.

Poucas sugestões visíveis (até3) e lista completa acessível. Separar pausa curta de manutenção por capacidade de domínio comprovado. Ações na Osler continuam manuais; apenas registrar a ação realmente feita. Não estimar economia de revisões/dia a partir de cartões estudados no PDF. Proteger lacunas atuais, erros críticos/recorrentes, criação recente de cards de erros e temas de prioridade elevada. Ausência de dados não significa domínio ou baixa incidência. Sem sugestão justificável, explicar a insuficiência e manter candidatos condicionais sem chamá-los seguros.

Pausa curta por capacidade pode usar evidência indireta (pouca incidência relativa conhecida, convicção recuperada>=80% em>=20 distintas e nenhum sinal adverso atual), explicitamente sem inferir acerto ou domínio. Evidência objetiva recente tem precedência: percentual inferior a85% não é substituído por PDF melhor. A preferência é por incidência relativa<=15% do maior sinal conhecido; isso e o horizonte7dias são políticas operacionais, não limiares científicos universais. Pausa não recomenda retirar cards High Yield ou conceitos em que ainda há erros; na falta de seleção por tipo, não chamar o deck inteiro de seguro.

Evidência forte de manutenção: acertos exatos recentes n>=30, taxa>=85%, limite inferior Wilson95%>=75%, estudo em>=2dias, incidência relativa baixa e nenhum sinal adverso. Não calcular intervalo binomial a partir de convicção acumulada ou percentual aproximado. Recomendações fracas ficam explicitamente condicionais. O intervalo de Wilson resume essa amostra; não controla dificuldade, dependência entre questões do mesmo conceito ou representatividade de prova, nem valida suspender todo o deck.

Falhas recentes não são diluídas pela média da janela: qualquer bloco objetivo abaixo de85% no último dia com resultados daquela modalidade protege o tema, mesmo em amostra pequena. É uma regra conservadora de triagem, sem declarar domínio ou esquecimento a partir de um único bloco. Novas medições posteriores podem substituir esse sinal; a média recente continua considerada. Reforço indicado pelo planejador, erros abertos, risco alto informado e cobertura insuficiente também protegem. Observações corrigidas substituem a versão anterior da mesma origem. Segurança acumulada só sustenta indicação indireta enquanto o planejador considerar o retrato atual; um bloco posterior pode superá-lo.

Aplicações legadas ficam identificadas separadamente, com sua data prevista de reavaliação, sem criar eventos retroativos. Uma escolha local de reabrir não significa reativar cartões na Osler. Ações posteriores precisam conservar a precedência do lote a que pertencem.

## Como usar

1. Em Registrar, preencha o resultado do bloco e **Quantos flashcards de erros você criou?**. Zero é válido; não é necessário copiar o conteúdo dos cards.
2. Ao salvar, a confirmação informa a incorporação à fila daquele tema. Corrigir ou desconsiderar o lançamento recalcula essa contribuição, sem apagar as versões anteriores.
3. Em Flashcards → Erros acumulados, consulte a fila, registre somente o estudo realmente feito e ajuste a carga quando couber na rotina. Criar cards não produz questões respondidas, retenção nem primeira passagem concluída.
4. Em Flashcards → Reduzir outras revisões, veja as sugestões atuais. Qualquer suspensão ou reativação continua manual. Atualizações por HTML são opcionais; antes de importar, confira se o arquivo já abrange os cards dos blocos anteriores, pois o arquivo passa a ser a referência dessas sessões.

Um HTML de inventário, incluindo cards já revisados, não vira uma dívida a estudar. Apenas novas criações não absorvidas formam fila a partir dele. A previsão local continua sendo de primeira passagem: não inclui erros futuros, reaprendizagens nem criação futura de cards. Ela não prevê quando todas as revisões da Osler terminarão. A carga de primeira passagem ocupa parte da capacidade total de flashcards; não deve ser somada por cima do teto diário dos retornos.

## Plano

- [x] TDD: política atual de redução e proteções; serviço/assinaturas/registro com guarda de concorrência; UI curta preservando recursos legados.
- [x] TDD: campo cards_created e integração na fila efetiva, com edição/void/idempotência e absorção por novo HTML; origem e estatísticas separadas.
- [x] Campo no formulário existente e feedback de integração, sem reativar meta pausada. HTML permanece opcional para atualizações cotidianas.
- [x] QA em cópia mínima, revisão independente, testes apropriados e suíte final, preservação ativa e interface desktop/mobile; versionar e integrar localmente sem push.

## Invariantes e foco da revisão

Nenhum registro fictício; nenhum acesso à Osler; não somar novamente acervo ou registros absorvidos; não confundir quantidade criada com estudada; não transformar convicção em acerto; capturar fonte e token juntos; não converter três sugestões em suspensão comprovadamente segura de todo o tema; atualizar critério após correção/void; conservar pausas e ações anteriores.

## Validação da entrega 0.27.0

Suíte completa final:780 testes passaram. Também passaram100 testes direcionados após a correção da precedência de lotes legados e ajustes de texto. Revisões independentes de fila/registro e política de redução concluídas sem achados pendentes. O aviso da suíte sobre nome duplicado em ZIP vem do teste que rejeita backups duplicados.

Validação com cópia mínima de banco e apenas os JSONs de contexto necessários, removida automaticamente ao concluir: criar cards, recalcular fila, proteger tema, desconsiderar bloco e restaurar plano sem perda. Todas as tabelas ativas conservaram contagens e hashes; não foram gravadas sessões fictícias nos dados do usuário. Originais continuam separados e imutáveis.

Formulário conferido no navegador em computador e largura390px, sem rolagem horizontal. O app permanece local na porta8501. A inspeção estática dos quatro módulos de interface não encontrou padrões sinalizados, mas usa apenas correspondência textual para Python; a verificação visual e os testes de interação complementam essa limitação. Não houve envio ao GitHub nem acesso à conta Osler.
