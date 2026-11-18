# Cobertura de temas e histórico portátil

> Execução: Superpowers executing-plans, com TDD e uma revisão independente ao final.

**Objetivo:** voltar a avançar em temas sem prática ou com pouca prática, dentro da carga configurada, sem perder histórico, reservas explícitas ou regras de retenção.

**Arquitetura:** corrigir a leitura de caminhos de exportações; distinguir exposição a questões de contato com flashcards; fazer remanejamentos automáticos concorrerem na alocação, preservando compromissos com data explicitamente escolhida. Temas novos continuam significando sem contato anterior: pouca prática recebe identificação própria e prioridade na parcela de retomadas, sem fabricar primeira exposição ou domínio.

**Restrições:** teto atual da retomada preservado; registros concluídos, excessos já registrados, trocas, extras e correções de simulados preservados; quantidades importadas não viram tentativas independentes; nenhuma automação da plataforma Osler.

## Design escolhido

- Ler caminhos relativos Windows e POSIX com validação comum contra caminhos absolutos, traversal e links externos. Não reescrever os arquivos originais ou os retratos históricos.
- Marcar pouca prática usando exposição documentada a questões abaixo da referência operacional já existente (30), com denominadores separados. Flashcards não bastam para dizer que houve prática de questões. Essa marca não declara domínio nem muda o posterior estatístico.
- Na parcela de revisões/diagnósticos, proteger a entrada de temas iniciais pouco praticados, usando incidência e a ordenação atual. A parcela estrita de temas novos permanece separada e respeita as datas de revisão.
- Remanejamentos automáticos deixam de ocupar previamente todo o orçamento. Continuam na fila, mantêm origem/data devida e recebem data quando selecionados no calendário. Datas manuais, correções e propostas preservadas após excedentes continuam protegidas.
- Mostrar rótulos curtos de primeiro contato e pouca prática nos cards; explicações e reserva adiada ficam recolhidas.

## Plano

- [x] Backup: branch privado anterior e ZIP íntegro do estado online atual; validar a base isolada da versão publicada.
- [x] Testes de caminhos Windows/POSIX; implementar normalização segura e testar exportações antigas.
- [x] Testes de classificação/seleção de pouca prática, sem somar fontes sobrepostas ou mudar o histórico; implementar proteção de entrada inicial.
- [x] Testes de remanejamentos automáticos vs compromissos explícitos, quotas e calendário; integrar seleção e sinalização.
- [x] Comparar antes/depois com cópia do backup real, testar telas/limites/revisões; revisar e preparar a publicação online sem reescrever os dados ativos.

## Verificações críticas

1. Caminhos Windows não podem abrir arquivos fora de exports em nenhum sistema.
2. Um tema com cards e zero questões não pode desaparecer da entrada em prática de questões.
3. Nova prioridade não pode reiniciar intervalos ou gerar acertos fictícios.
4. Reservas manuais e blocos preservados por excedentes não podem ser removidos.
5. Remanejamento não selecionado continua pendente e pode ser agendado em dia posterior.

## Registro

Base online: 367b6487b0889f7528e933f415dd8c7a1fb9e4db. Checkout anterior com alterações preservado. Trabalho isolado em codex/coverage-repair-20261118.
Usuário dispensou ciclos de aprovação nas instruções do projeto; escolhas reversíveis resolvidas dentro do escopo. Caveman não disponível: execução inline e comunicação enxuta.

### Decisões e evidências

- Backup do código em `codex/backup-cobertura-20261118`; backup de dados revisão 59, íntegro, 62 arquivos. Originais e árvore local antiga preservados.
- Quatro regressões inicialmente vermelhas: caminhos portáveis, exposição sem soma das fontes, mínimo de novos com reservas automáticas e admissão inicial de pouca prática. Todas passaram após as respectivas correções.
- Remanejamento automático mantém prioridade proporcional à incidência e ao atraso original; não ganha precedência absoluta sobre os outros candidatos.
- Saldo automático limita a quantidade alocada. O teste do saldo de três questões falhou antes da correção e passou depois, incluindo o consumo no calendário.
- Blocos automáticos parciais continuam elegíveis pelo saldo mesmo quando a próxima revisão já é futura. Apenas `allocation_due` muda na cópia de alocação; `next_review`, `theme_review_due` e o histórico permanecem intactos. Regressão reproduzida e corrigida.
- Simulação descartável do backup: contexto do Planner recuperado para 1.173 estados; temas novos hoje de 6 para 12 questões, dentro das mesmas 30 questões de blocos. Reservas de 30 revisões externas e 20 de treino por área preservadas, teto total 80. Histórico comparado antes/depois sem alterações.
- Referência de exposição inferior a 30 questões é operacional, configurada nos parâmetros existentes; não é um teste de domínio ou uma estimativa de aprovação. A classificação estrita de temas novos e os posteriores continuam separados.
- Cinco falhas anteriores confirmadas na base `367b648`: seletor de estratégia usava índice do controle de retornos; quatro expectativas de acervo pequeno ignoravam o complemento externo já previsto em `balanced_v2`. Testes atualizados para verificar o controle correto e separar acervo documentado de complemento, mantendo zero tentativas inventadas.
- Revisão independente sem problemas materiais confirmados; o revisor também executou os 16 testes novos e verificou a correção de alocação do saldo parcial.
- Validação visual pelo Computer Use interrompida automaticamente: não foi possível identificar a URL da janela com segurança. Sem nova tentativa ou automação dessa janela; validação funcional pelas telas automatizadas e pelos dados copiados.
- Suíte final integral: 1.219 testes passaram, 9 ignorados (symlink no Windows e PDFs pessoais ausentes), 5 subtestes passaram. Um aviso esperado do teste que cria propositalmente uma entrada ZIP duplicada. Cópias descartáveis removidas ao término; relatórios pequenos e backup verificado preservados fora do Git.
- Entrega preparada como avanço do branch `codex/cloud-mobile-20261109`, baseado na versão publicada e com backup anterior no GitHub. Não usar o construtor antigo a partir da árvore local desatualizada.
