# Temas com vaga: corrigir exclusão e auditar cobertura

Pedido: realocar temas sem previsão usando incidência, desempenho e retenção existentes. Execução inline com Superpowers, testes antes da alteração; escolhas reversíveis autorizadas por AGENTS.

## Diagnóstico e desenho

O tema do print possui total1 no PDF de questões. Há um bloqueio repetido: allocate_day exige acervo>=min_block, category_allocation exige dose>=min_block e capacity_policy rejeita admissões menores. Portanto um tema específico com1–9 questões nunca recebe vaga, independentemente da duração. planning_frontier já conserva esses temas; o erro está nos pisos de alocação.

Ruling: mínimo de bloco continua10 para acervos normais; exceção limitada ao acervo total positivo menor que10. Esses temas usam todo o acervo disponível, sem atribuir domínio nem inventar inéditas. Não juntar temas filhos em categorias pais, não fabricar datas para preencher a tabela e não trocar a incidência recebida.

Ruling: manter prioridade de compromissos/retornos vencidos e a ordenação review_order já existente. Verificar cobertura do catálogo inteiro na previsão de próximos contatos; se a capacidade real, descanso, proporção estrita ou horizonte impedirem um encaixe, explicitar o motivo e oferecer reorganização concreta, preservando os limites configurados em vez de prometer uma vaga impossível.

## Passos

- [x] Testes RED: temas com1/9 questões em Hoje/calendário/tabela, prioridade entre incidências/riscos, acervo grande continua mínimo10, lotes/descanso/carga preservados.
- [x] Unificar piso de prática no dono da política, reutilizando nas três barreiras; não alterar posteriors/intervalos.
- [x] Cenário sintético de catálogo grande com tamanhos variados e carga semelhante: todos os temas elegíveis com data concreta dentro do horizonte quando há capacidade; diagnosticar demais exclusões sem maquiar resultado.
- [x] UI identifica acervo pequeno e lacuna de capacidade; encaminhar reorganização existente com prioridades calculadas, se necessário.
- [x] Testes focados, suíte completa, revisão independente e prova visual sintética8602; relatório/commit local. Somente leitura do banco real para diagnóstico, sem executar testes nem gravar planos nele.

## Diagnóstico ampliado e decisões

- O PDF todos selecionado tem1480folhas positivas,433com menos de10questões. Saúde do Trabalhador tem486no PDF e incidência36altíssima no conjunto institucional20/10; seu filho Segurança do Trabalhador tem1. A fonte foi conferida visualmente na página52.
- Há10temas específicos de terceiro nível com conteúdo além dos filhos. Foram restaurados como unidades praticáveis, mantendo is_leaf=False da fonte e evidência abrangente/non_additive. Não fabricar percentuais residuais nem atribuir histórico do pai ao filho. Área/especialidade continuam fora dos blocos automáticos.
- Essas unidades são contatos abrangentes, não acervos independentes dos filhos. Contagens originais e snapshots ficam intactos; a legenda explica sobreposição. A soma importada/convicção global da Evolução mantém a base conservadora sem adicionar novamente os pais, enquanto cobertura/erros/trocas/simulados reconhecem as unidades restauradas.
- Uma quota sem candidatos estava impedindo admissão de outros temas apesar de haver sobra. Foi aplicada na admissão a mesma cessão de sobra já existente na alocação, com limites futuros/descanso mantidos e preferências estritas0/100preservadas.
- Política4.3 invalida caches antigos de contatos. O golden estatístico V1 permanece intacto; seu teste passa a proteger exatamente posteriors/intervalos/metas, permitindo a nova alocação dos bancos pequenos. Teste antigo de piso foi ajustado deliberadamente à exceção de acervo pequeno.
- Diagnóstico do conjunto real via conexãoSQLmode=ro e cópia apenas em RAM:1490unidades,1490datas,0semvaga. Nenhum arquivo/banco original alterado por essa análise. Datas são condicionadas à carga e ao resultado; não há capacidade infinita nem garantia de retenção/nota.

## Fechamento

906passed,1skipped,1warning na suíte completa;18focados após a legenda final. Catálogo sintético1480/1480; diagnóstico protegido do conjunto atual1490/1490. Revisão independente e captura sintética desktop/celular concluídas. Relatório em docs/design/2026-10-28-cobertura-sem-exclusao.md. Nenhuma recalibração estatística, edição de originais ou escrita de estudo fictício.
