# Atualização guiada de dados — 02/11/2026

O destino **Atualizar dados**, na lateral, reúne duas fontes independentes. O fluxo é enviar/colar, informar a data e finalidade, conferir e confirmar. Usam-se widgets e confirmações nativos existentes, com toast após a gravação. Explicações, passos da exportação e histórico ficam recolhidos. A aba não selecionada não executa seus cálculos.

## Planner de questões

O leitor reconhece ThemeTitle/ThemePath e PrimaryText/SecondaryText, inclusive hierarquias separadas por » ou →. Ele exige os cabeçalhos de progresso e valida questões distintas/disponíveis, segurança acumulada, dias sem contato e pendências. Zero informado é preservado; ausência permanece ausente. HTML não é executado. Limite de20MiB/10.000linhas, UTF-8, rejeição de caminhos repetidos, percentuais inválidos e numeradores maiores que o total.

Associações usam o caminho normalizado, exato e único do acervo PDF atual. Temas desconhecidos são identificados e preservados no original; não recebem estatísticas de outro assunto por semelhança de nome. Sem correspondências, a importação é recusada e a tela orienta atualizar o PDF. Na prévia do arquivo real Planner-table.html foram lidas1.174linhas e reconhecidas1.173, sem aplicar ou importar dados de produção.

O contato é derivado da data declarada menos a quantidade de dias sem contato. Hoje vale zero; ontem, um. A data usa o dia de estudo com virada às04h. Uma nova captura atualiza apenas os caminhos recebidos, sem zerar os ausentes. Acumulados de convicção e questões distintas ficam em planner_snapshot e nunca viram eventos de tentativas independentes.

Por padrão a captura tem incidence_included=false: os leitores de incidência ignoram esse conjunto, enquanto o leitor de progresso continua consumindo o snapshot. Isso evita que atualizar progresso elimine os pesos institucionais anteriores. Atualizar incidência exige opção explícita, instituições declaradas e coluna completa; a comparação inclui valores antes/depois. Se uma fonte institucional já conhecida perder linhas, a opção de substituir incidência é recusada como parcial. A interface orienta atualizar só o progresso ou enviar a consulta completa. Não se inferem pesos por instituição de uma tabela conjunta.

## Flashcards pessoais de erros

A prévia reutiliza o parser e a fila existentes. O usuário distingue pendentes, inventário e nova passagem. Totais de pais não se somam aos filhos; grupos recolhidos permanecem sem alocação específica e são sinalizados. Desaparecimento de grupos-raiz exige confirmação adicional de que o arquivo representa toda a fila desejada.

O saldo comparado é o efetivo de hoje. Uma fila hipotética usa o mesmo cutoff de criações que será aplicado na importação. Se a captura é anterior a cards já criados e registrados, esses cards continuam na fila e são somados explicitamente na prévia. Exemplo sintético testado:200cards no HTML de ontem e quatro criados hoje produzem204na prévia e após a importação.

O novo HTML substitui o saldo da passagem, sem descontar outra vez os estudos antigos. Criações anteriores abrangidas pelo HTML deixam de ser somadas de novo; cabe ao usuário exportar a árvore que já as inclua, como informa a tela. O histórico permanece. O serviço recusa dados desatualizados por token; uma cópia já importada com a mesma finalidade não reinicia a passagem.

## Preservação e concorrência

Prévia não grava arquivos ou registros. Na aplicação, o Planner relê e valida a fonte/opções e confere o token antes de inserir; o armazenamento mantém a comparação em transação imediata. Originais e snapshots são imutáveis, com hashes. A importação não muda perfis ou agrupa automaticamente temas. Não foi aplicado nenhum arquivo novo aos dados ativos nesta tarefa.

Os arquivos originais de código anteriores à alteração estão em evidencias/atualizacao-guiada-2026-11-02/codigo-antes.zip. As versões e fontes de dados já existentes continuam guardadas; não se criam grandes backups recursivos a cada prévia.

## Validação

Testes de serviço e UI cobrem semântica dos acumulados, datas e ausências, duplicação, exportação parcial, rejeição de incidência parcial, token concorrente, saldo de cards, criações posteriores, confirmação antes de gravar, rascunhos entre abas e data vazia. Navegador verifica upload real dos dois arquivos e as duas confirmações em cenário sintético descartável, sem acesso à plataforma Osler. Evidências em evidencias/atualizacao-guiada-2026-11-02, incluindo checks.json de navegação e o log da suíte completa.

A suíte completa concluiu com **1.102 testes passados, um pulado e um aviso**, em376,46s. O pulado depende de links simbólicos indisponíveis no Windows; o aviso é intencional no teste de ZIP duplicado. As duas telas foram verificadas em1440,1366,768e390px, sem exceções ou transbordamento horizontal da página; tabelas usam rolagem própria. Não é declaração de auditoria completa de leitor de tela ou teste em aparelho físico.

A revisão independente identificou a diferença entre captura antiga e criações posteriores. A correção usa a fila efetiva existente e foi reproduzida em teste antes/depois; a nova revisão não apontou pendências nas alterações reavaliadas. Pastas temporárias da suíte e das medições foram removidas. As importações pelo navegador aconteceram apenas no cenário sintético da porta8602; nenhum novo HTML foi aplicado ao banco de produção.
