# Cobertura sem exclusão silenciosa

28/10/2026 · base33ef94c · política4.3.

## Fonte conferida

No PDF todos selecionado, página52: Saúde do Trabalhador tem486questões e seu filho Segurança do Trabalhador tem1. A tabela institucional de20/10 informa36questões e incidência altíssima para Saúde do Trabalhador. Quantidade no acervo não é incidência nas provas.

O catálogo original contém1480folhas positivas;433têm menos de10questões. Além disso,10temas específicos de terceiro nível têm conteúdo além dos filhos. Excluir qualquer pai removia, por exemplo, quase todo o conteúdo de Saúde do Trabalhador do planejamento. Originais, is_leaf, contagens e snapshots não foram reescritos.

## Correção

1. Piso operacional compartilhado em admissão e alocação: mínimo habitual10 preservado; acervo positivo menor recebe vaga com sua quantidade conhecida. Essa amostra não comprova domínio. Nenhum número de questões fictício.
2. Na admissão adaptativa, quota ociosa pode ceder sobra a temas aguardando, como o alocador já fazia. Carga, máximo de temas, capacidade futura, descanso e preferências estritas0/100 continuam respeitados.
3. Temas específicos com conteúdo além dos filhos são unidades praticáveis, mantendo a condição não terminal da fonte. Áreas e especialidades continuam fora dos blocos. Cadastro, seletor, registro, erros, conversão de simulados, trocas e cobertura usam a mesma definição.
4. O contato de Saúde do Trabalhador é abrangente. Sua contagem486 e seu histórico não são um acervo independente do filho nem uma taxa residual de485questões. Metadata inclusive_parent/non_additive e legenda na interface explicitam isso. Um bloco do pai não distribui respostas/acertos/convicção automaticamente aos filhos. Totais importados da Evolução não somam novamente essas bases sobrepostas; as fichas individuais preservam o original. A soma global continua conservadora.
5. Tabela mostra quantas unidades têm próximo contato com data. Sem capacidade matemática, descanso excessivo ou proporção estrita que exclua um grupo, o app mantém diagnóstico explícito, sem fabricar vaga. A versão4.3 invalida caches anteriores. Incidência, prioridades, posteriors, critérios de domínio e intervalos não foram recalibrados.

## Resultado no conjunto atual

Diagnóstico reproduzido em SQLite somente em RAM, carregado por conexão mode=ro no arquivo original: **1490unidades praticáveis,1490com data,0sem vaga** até o fim da preparação. A carga configurada continua120questões/dia. Nenhuma sessão, preferência ou plano foi gravado no banco original por essa análise. Não foram feitas cópias de dados em disco.

As datas são vagas condicionais, distintas do vencimento ideal. O modelo mantém Saúde do Trabalhador na fila inicial por evidência/incidência e capacidade, sem promovê-lo artificialmente a urgência. A data muda com os resultados reais. Ter vaga não significa execução nem melhora prevista do rendimento.

## Provas e revisão

- RED observado:11falhas iniciais cobrindo os pisos, catálogo grande e tema específico não terminal; posteriormente, erros/mock/swap/evolução/escopo receberam regressões focadas.
- Suíte completa final: `.venv/Scripts/python.exe -m pytest -q` → **906 passed,1 skipped,1 warning**,207.36s. Skip de symlink no Windows; warning do ZIP duplicado deliberado. Após apenas abreviar a legenda,18testes focados passaram em7.86s.
- Treze casos novos em test_coverage_inclusion.py: acervo1/9 nas duas estratégias e modos, prioridade, descanso, carga,1480temas com datas reais, catálogo/pai/filho, registro e cards, erros, simulados, evolução, troca e consistência dos metadados.
- Dois testes preexistentes alterados deliberadamente: test_topic_scheduling limita a exceção de piso ao acervo pequeno; test_algorithm_v1_regression continua comparando exatamente estados estatísticos, intervalos e metas ao golden original do loteB, permitindo a nova seleção de blocos. O arquivo algorithm_v1_baseline.json permanece intacto. A primeira suíte encontrou só essa incompatibilidade de contrato antigo; depois do ajuste explícito, a suíte inteira passou.
- Revisão independente coverage_priority_review apontou os consumidores que ainda exigiam is_leaf e o risco de sobreposição. Corrigidos; revisão incremental sem P1pendente. Março isoladamente não prova erro de prioridade e não motivou alteração arbitrária de score/intervalo.
- Navegador sintético em1366×768 e390×844: busca retorna os dois caminhos, ambos têm ações e datas, pai específico abre registro com legenda de escopo, ausência permanece traço, sem overflow. Capturas abertas e inspecionadas. Harness corrigido para não acumular sua própria simulação a cada rerun; isso não era um erro do catálogo de produção. TemporaryDirectory/servidor8602/fontes mínimas limpos ao terminar; zero requisições externas.
- Detector Impeccable executado uma vez nos cinco arquivos de apresentação alterados: lista vazia, retorno0. É análise estática; não certifica acessibilidade. Cores/fontes da fundação preservadas. Aparelho físico e leitor de tela não testados.

Evidências locais ignoradas pelo Git: evidencias/cobertura/diagnostico-somente-leitura.json, prioridades-somente-leitura.json, fonte-pagina52.png, temas-*, registro-*, qa-sintetico.json, detector.json. Validação funcional só com dados sintéticos; dados reais usados apenas para diagnóstico protegido em memória. Diretrizes não rastreadas do usuário preservadas fora do commit. Nenhum push.
