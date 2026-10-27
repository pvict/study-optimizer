# Revisão sustentável para todos os temas

Escopo autorizado: regra central da estratégia equilibrada usada no perfil atual, todas as folhas do catálogo; correção de foco dos campos. Execução direta (AGENTS), investigação Superpowers, testes antes da correção. Sem mudar dados pessoais, meta90%, respostas, pendências reais ou parâmetrosV1 imutáveis. Sem acesso à plataforma.

## Causas e desenho

1. Retornos pendentes eram somados a um piso extra de10, em feedback, orçamento e previsão. O exemplo37 é27pendentes+10;15das27têm prazo anterior ao retorno do último bloco. Reutilizar `practice_state` como cálculo único: orçamento conjunto=max(dose restante do tema, lotes devidos), não soma. Conservar identidades/datas dos lotes; sem declarar que repetições provam domínio geral.
2. Feedback deve mostrar o próximo encontro real (mínimo entre tema e todos os lotes), distinguindo retorno dirigido de revisão geral. Um lote futuro não absorve silenciosamente pendências de datas anteriores.
3. Doses usam posterior Beta(1,1) existente, lacuna à meta, incerteza e incidência. Remover o mínimo pessimista entre média acumulada e último bloco quando só há oscilação amostral; manter proteção para falha forte(<60%) ou queda com intervalos95% não sobrepostos. Nenhuma nova contagem/pseudotentativa.
4. Intervalos: falha forte<60% pede recuperação curta;60–80% mantém prática inicial semanal; bons resultados≥80% em encontros espaçados permitem expansão progressiva já existente, limitada pelo máximo configurado e prova. Uma média antiga<70% não deve impor3dias eternamente após recuperação objetiva. Sem alongar intervalos só para ocultar carga. Incidência ordena prioridades e dose, sem reduzir automaticamente o intervalo da estratégia equilibrada.
5. Retornos dirigidos e complemento suficientes próximos da revisão, inclusive em dias adjacentes, contam como contato operacional e evitam bloco duplicado imediato; não aumentam streak/estabilidade nem alteram posterior de novas. Novo contato geral é indicado após o intervalo básico, conservando os erros em sua data. Falha posterior relevante impede adiamento. Não pressupor recuperação futura.
6. Campos: retirar o outline adicional do input, mantendo borda nativa discreta e foco visível de teclado em controles. Não desabilitar seleção de texto ou acessibilidade.

## Execução e provas

- [x] Reproduzir os dois blocos22/15e23/17 e pendências15/12; testes gerais para nomes/áreas arbitrários, piora/sem medida/repetidas, limite diário, consumo de lotes, feedback/calendário e não duplicação.
- [x] Consolidar orçamento em study_capacity; usar o mesmo cálculo em feedback e previsão. Ajustar suavização/intervalo central balanced_reviews e proteção em adaptive_planning. Incrementar POLICY_VERSION para invalidar prévias antigas.
- [x] Ajustar foco em bento.css, validar clique/teclado em navegador sintético e celular. UI/retenção de campos e registro permanecem.
- [x] Auditar recálculo de todos os temas por leitura de dados, com resumo antes/depois; QA automatizada somente em cenários sintéticos. Suíte e revisão do diff.

## Evidência e limites científicos

Cepeda et al.2008, n>1350, mostram relação entre intervalo de prática e horizonte de retenção, com piora para intervalos curtos ou longos demais: https://doi.org/10.1111/j.1467-9280.2008.02209.x ; cópia no laboratório dos autores: https://laplab.ucsd.edu/articles/Cepeda%20et%20al%202008_psychsci.pdf . Rawson et al.2018 mostram benefícios de reaprendizagem em múltiplas sessões: https://pubmed.ncbi.nlm.nih.gov/29431462/ . Eglington/Pavlik2020 estudam eficiência adaptativa com dados por item: https://doi.org/10.1038/s41539-020-00074-4 . Não possuímos identidades/latências por item para calibrar uma curva de esquecimento pessoal.

As fórmulas de dose e limiares de produto são heurísticas transparentes, não resultados numéricos derivados desses artigos nem garantia de90%/aprovação. Não prometer que toda revisão diminui: piora real pode exigir reforço. Corrigir duplicação de trabalho e reação a ruído não equivale a suspender retenção.

## Verificação final

`.venv/Scripts/python.exe -m pytest -q` → **845passed,1skipped,1warning em205.56s**. Skip de symlink neste Windows; warning de ZIP duplicado deliberadamente em teste de backups, já existentes. Testes novos:13casos em tests/test_sustainable_reviews.py. Expectativas de orçamento compartilhado atualizadas intencionalmente em tests/test_balanced_reviews.py e tests/test_review_strategy_service.py. A fundação visual também passou em verificação específica:6passed.

Auditoria em1480temas, sem escrita na origem:4intervalos aumentaram; a dose geral do retrato atual permaneceu estável. O orçamento conjunto dos encontros e a escolha da próxima data foram corrigidos. Queimaduras: próximo lote15em30/10; revisão geral16em03/11, contendo o lote12daquela data após os retornos anteriores serem cumpridos. Não alongar o intervalo desse tema só por ter duas listas abaixo de75%.

QA visual sintética:1366e390px, registro concluído, feedback com próximo encontro real e revisão geral distinta, sem37extras; campos numéricos e busca sem outline adicional, borda única1px, foco de botão3px e digitação preservados. Cenários descartados automaticamente. Evidências pequenas mantidas em evidencias/revisoes-sustentaveis. Fundamentação e limites em docs/research/revisoes-sustentaveis-2026-10-27.md.

Revisão direta do diff concluída. Revisão independente tentada, mas o subagente encerrou por limite de uso da ferramenta; não declarada como concluída. A revisão direta acrescentou regressões para limite da prova, falha posterior e revisão terminada em partes. Base local d9c4eac, commit separado e integração local sem push. Dados, originais, versões de parâmetros e arquivo não rastreado de diretrizes preservados.
