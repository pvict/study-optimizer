# Decks inteiros e Psiquiatria — v0.26.1

O usuário prefere realizar decks completos. Confirmou em24/10/2026 que200 cards/dia são referência e que aceita passar um pouco para fechar um deck. Escolha de implementação declarada: até10% de margem. As prioridades de incidência, acertos/erros e contato continuam iguais; muda apenas o encaixe na carga diária. Não há evidência de que50 seja uma dose universal, e retirar esse corte não altera o algoritmo individual da Osler.

## Regra operacional

Percorrer a fila de prioridades e encaixar todo o saldo de cada tema. Parar ao atingir a referência, admitindo o último deck somente se couber até110% da referência. Se não couber, considerar os seguintes, preservando a quantidade inteira de cada um. Pode resultar em carga menor que a referência. Deck maior que a referência e a margem não é cortado nem imposto: fica identificado, com acesso ao ajuste para um dia ou seleção manual em Temas.

Exemplo real:72+22+17+35+35+27=208 cards em seis decks, sob referência200 e teto de planejamento220. Estudos Epidemiológicos entra com72, e Trauma Torácico não recebe somente1 card para completar a diferença.

Registro parcial continua permitido porque é estudo real. O saldo do deck iniciado hoje vem primeiro. Ao atingir200 em um deck de220, os20 restantes continuam disponíveis dentro da margem. A margem já consumida por outras respostas é descontada: registrar205 não deixa uma margem adicional de20. Quando a referência do dia é0, a pausa continua valendo.

Hoje e o primeiro dia do cenário usam o mesmo bônus de conexão com as questões; dias futuros não presumem quais questões ainda não realizadas serão propostas. O cenário continua somente de primeira passagem, sem melhora de domínio ou retornos individuais inventados. A carga de questões não é modificada.

## Complemento manual do print

O print fornecido identifica Álcool10 sob Transtorno por Abuso de Substâncias e Suicídio2, Transtorno Afetivo Bipolar6, Transtornos de Ansiedade14 e Transtornos Depressivos54 sob Transtornos do Humor.10+(2+6+14+54)=86. Os demais24 cards de Psiquiatria já estavam no HTML;110 é o total da área e não entra novamente.

O evento aditivo error_cards.expand complementa o mesmo snapshot, preserva o PNG original em exports/error-cards e mantém o histórico de estudo. Não reimporta o arquivo como um novo saldo. Os86 já pertenciam aos8153 e são apenas atribuídos aos filhos. Resultado:8153 identificados em268 temas, sem grupos pendentes. As somas devem coincidir com o pai antes de salvar e com o total após aplicar; caminhos originais exatos prevalecem quando há aliases normalizados. Reenvio idêntico é idempotente, escrita obsoleta é rejeitada e nenhum schema é migrado.

## Plano e validação

- [x] Reproduzir corte de decks, margem após200, divergência Hoje/cenário e expansão por aliases; testar antes de corrigir.
- [x] Selecionar decks inteiros e usar referência original ao descontar respostas realizadas; retirar sugestão manual de50.
- [x] Complemento de print preservando snapshot, progresso, fonte e total; testes de contagens incoerentes e reenvio.
- [x] Revisão independente dos achados e correções;31 regressões focadas aprovadas.
- [x] Suíte completa, conferência visual, auditoria dos dados, integração local e registro final da evidência.

Na cópia mínima dos dados reais, o plano de questões ficou idêntico, assim como snapshot e histórico de cards. A referência200 selecionou208 cards em seis decks completos; o complemento identificou todos os8153. O cenário de primeira passagem, começando no dia de estudo23/10 que termina às04h de24/10, chegou a07/12/2026, sob rotina constante e sem novos cards ou retornos individuais. É cenário, não garantia de acabar todas as revisões.

Suíte completa final:718 testes aprovados em200,62s, com o aviso intencional do teste de ZIP duplicado.31 testes focados aprovados. A revisão independente reproduziu três P2 (saldo de deck iniciado após atingir a referência, divergência entre Hoje/cenário e identidade de pai com aliases); quatro regressões confirmaram as correções, sem novo P1/P2 identificado. Auditoria das30 tabelas ativas confirmou que nenhuma linha anterior foi alterada ou removida: foi acrescentado apenas o evento de complemento do print. Schema12, perfil, sessões e metas de questões preservados.

O app local foi reiniciado para carregar a versão0.26.1 e respondeu normalmente. Na interface, Hoje mostrou208 cards em seis decks inteiros e Estudos Epidemiológicos72; Temas mostrou268 temas e o complemento de Psiquiatria. Detector dos arquivos de UI sem apontamentos. Nenhum estudo de teste foi gravado nos dados ativos; a cópia mínima foi removida automaticamente.
