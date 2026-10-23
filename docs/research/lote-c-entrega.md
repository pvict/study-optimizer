# Lote C — entrega 0.23.0

Implementação local em 23/10/2026, a partir do lote B (`8f5884b`). Schema 12 aditivo. A execução seguiu Superpowers, Revenue-Centric Design e Impeccable no modo Operate, mantendo o sistema visual existente.

## Onde usar

- **Temas → Plano de corte:** demanda condicional de revisões comprometidas e capacidade da rotina; prévia, aplicar e desfazer. Protege fragilidade, erros abertos, incidência desconhecida, falta de medição e compromissos explícitos.
- **Temas → Minha meta:** corte documental, fontes, amostras e faixas observadas de simulados e questões novas. Não há previsão de aprovação. Incidência conjunta não vira estimativa individual de banca.
- **Hoje → Revisão da semana:** conversa curta opcional, comparação descritiva, versões preservadas; sugestão de carga exige decisão do usuário.
- **Ajustes → Meta e rotina → Parâmetros:** versão em uso e seleção manual entre versões cadastradas. Só v1 está cadastrada no banco ativo; nenhum coeficiente foi calibrado.
- **Temas → Exportar histórico:** CSV de sessões, erros e simulados, com tipos, versões, fontes e proteção de fórmulas.
- **`scripts/analise_calibracao.py`:** análise somente leitura, Markdown e CSV, preservando relatórios anteriores. Funciona também com banco vazio e declara insuficiência de dados.

## Decisões e limites

Preservados os sete destinos principais existentes, embora o texto original mencionasse cinco. As funções novas ficam dentro das telas existentes. Nenhum campo obrigatório foi acrescentado ao registro rápido; a modalidade anterior é lembrada, salvo quando o bloco já declara uma modalidade específica.

A demanda do corte não transforma todos os 1.480 temas em revisões recorrentes. Inclui temas já comprometidos e retornos conhecidos; estreias e diagnósticos iniciais sem compromisso permanecem na fila inicial. A capacidade exibida é a carga total, que também atende temas novos. Não é garantia de vagas para todas as revisões nem quantidade necessária para aprender. Uma proposta sem redução segura continua vazia.

Wilson é uma faixa nominal sobre as contagens registradas, sujeita a correlação, seleção de questões e amostra pequena. Lacunas de banca são parciais quando falta incidência ou desempenho de temas. Reservas exploratórias da agenda não são incidências observadas. Fontes distintas mantêm seus denominadores.

## Evidências

- Suíte inicial do lote B: **563 testes passaram**, um aviso intencional do teste de ZIP duplicado.
- Suíte final: **611 testes passaram em 153,90 segundos**, com o mesmo aviso intencional de ZIP duplicado. Nenhuma falha.
- Regressão congelada antes da refatoração: **14 cenários** de estados, doses, intervalos, prioridades e alocação; v1 preservada.
- Testes novos cobrem proteção do corte, prévia/aplicar/desfazer, reconstrução diária, expiração, lotes consumidos, catálogo sem dívida, comparabilidade e bordas de Wilson, incidência parcial, leitura sem SQL mutante, parâmetros imutáveis/CAS, backup/restauração populados, revisão semanal, exportação e AppTest das novas telas.
- Revisão independente encontrou três falhas: adiamento perdido na reconstrução diária, lote consumido ressuscitado na simulação e peso exploratório interpretado como incidência. As três foram reproduzidas por testes falhando e corrigidas. A conferência visual também identificou e corrigiu o catálogo contado como dívida recorrente.
- Validação em cópia mínima dos dados reais: 1.480 temas, plano de 23/10 com **120 questões**, seis blocos, nenhuma exceção AppTest, banco original inalterado pela validação.
- Preservação após migração: todas as linhas anteriores presentes, **57 arquivos de origem com hashes conferidos**, novas tabelas de revisão semanal e seleção de parâmetros vazias. Nenhum estudo de demonstração foi inserido.
- Detector estático do Impeccable sem achados; `git diff --check` limpo. Inspeção visual no navegador local confirmou abas, leitura do corte e plano diário. Toque e viewports de aparelhos físicos continuam pendentes.

Os relatórios pequenos de execução e preservação ficam em `tmp/lote-c-*`, fora do Git. As cópias descartáveis usadas na validação foram removidas pelos respectivos contextos temporários.

## Preservação e reversão

Backup anterior ao schema 12: `data/backups/osler_20261023T175033Z_1086104e5c47c56c.zip` (5.827.436 bytes). Originais e outros backups foram preservados.

Para desfazer uma política de corte, use a ação **Desfazer plano de corte**; histórico e resultados permanecem. Para uma revisão semanal, correções criam nova versão. Uma seleção manual de parâmetros pode voltar a uma versão cadastrada anterior, preservando o histórico.

Para reverter todo o lote, restaure o backup anterior em **outra pasta** e use também o código anterior. Não sobrescreva a pasta atual nem diminua `user_version`: o código do lote B não abre schema 12.

Próximo passo: usar o app diariamente por **6 a 8 semanas** e só então executar `scripts/analise_calibracao.py`. O relatório não calibra nem troca parâmetros sozinho.
