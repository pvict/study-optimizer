# Meta efetiva por dia

Objetivo: editar o total efetivamente disponível no dia, incluindo reservas de revisões externas e treino, com prévia e confirmação. Preservar os limites automáticos dos outros dias e os dados registrados.

Execução inline com Superpowers, TDD e uma revisão independente ao final. Usuário dispensou ciclos de aprovação. Revenue-Centric Design: um controle claro, resumo numérico curto e detalhes recolhidos.

## Decisões

- Campo opcional `effective_goal` em StudyDay, falso por padrão: dados antigos mantêm a retomada. Aplicação explícita permite substituir o teto apenas nessa data, inclusive a redução por deck grande; a prévia informa a exceção.
- O cálculo da retomada e o alocador usam a mesma meta. Revisões externas pendentes podem ser redistribuídas; registros realizados e treinos explicitamente reservados não podem ser apagados por uma meta menor.
- Prévia em cópia SQLite em memória, sem duplicar arquivos, sem escrita nos dados ativos; resumo antes/depois e temas alterados. Aplicação revalida token, revisão e conteúdo da prévia, e grava o dia e a auditoria numa única transação.
- Dias exclusivos (simulado, revisão final, descanso final, dia externo) têm mensagem específica e rota para o ajuste responsável; não aceitar outra alteração inefetiva.
- Mesmo componente em Hoje e Calendário; mostrar a meta efetiva atual, prévia antes do diálogo de confirmação, toast após salvar; manter detalhes recolhidos.

## Etapas

- [x] Conferir árvore isolada e backup no GitHub: codex/backup-meta-dia-20261118, base 518a7e5.
- [x] Reproduzir em testes: teto automático vs meta explícita, isolamento da data, reservas e concorrência.
- [x] Implementar cálculo compartilhado e serviço de prévia/aplicação auditada.
- [x] Integrar Hoje e Calendário e testar fluxo com AppTest.
- [x] Testar cenários reais em cópia descartável, revisão independente, suíte apropriada e preparar publicação no branch online.

## Evidências e decisões da execução

- Backend e UI reproduzidos com testes vermelhos antes da implementação. Fluxo antigo de salvar diretamente substituído por prévia, confirmação existente e toast após gravar.
- A prévia usa somente uma cópia do SQLite em memória. A aplicação revalida a proposta e grava configurações e auditoria na mesma transação, protegida também pelo token dentro do bloqueio de escrita.
- O resumo usa capacidade e contagens ordinárias, separando treino por área e revisões externas. Descanso mostra zero em todas as categorias.
- Teste com a cópia do backup revisão 59: antes 80 no total (30 temas, 20 treino, 30 externas); proposta de 100 reserva 50 para temas, 20 para treino e 30 externas. Com os temas/doses atuais, 46 das 50 de temas são distribuídas; a UI informa as quatro vagas livres. Perfil, resultados e teto de 80 no dia seguinte preservados. Nenhuma meta foi alterada no servidor durante esta validação.
- Revisão independente encontrou conflitos com adicionais temporários, extras escondidos pela retomada e crédito de questões de treino em extras. Todos reproduzidos em testes e corrigidos. Uma meta explícita substitui o adicional temporário; os extras cabem dentro do total; créditos de treino continuam separados.
- Crédito de extras extraído do alocador sem mudar sua lógica, reutilizado pela prévia e pela reserva externa, respeitando evento de criação, sessão, caminho e créditos de troca. Temas ausentes do catálogo conservam reserva até o usuário resolver a configuração.
- Saldo de extras protege o mínimo mesmo quando o plano antigo de retomada não mostrava esses itens. Datas exclusivas direcionam ao menu responsável; treino e extras pendentes exigem remanejamento/retirada antes de descanso.
- Campos antigos continuam sem `effective_goal`; o novo campo é falso por padrão. Exceções são ativadas só por uma aplicação explícita na data escolhida. Adicionar extras depois de uma meta explícita continua ampliando o total pela ação do usuário; removê-los reduz a parcela correspondente.
- Revisão incremental final sem problemas materiais adicionais; 12 testes novos de meta diária/UI passaram, e 74 testes dos fluxos de meta, retomada, excesso, trocas e treinos passaram na verificação focada.
- Navegação Hoje → outra tela → Hoje reproduziu retorno indevido ao valor 1; inicialização dos widgets ausentes corrigida. Teste ficou vermelho antes e verde após a correção; 27 testes de meta/UI/navegação/calendário passaram na verificação focada final.
- Suíte integral: 1.231 testes passaram, 9 ignorados por symlink no Windows e PDFs pessoais ausentes, 5 subtestes passaram. Aviso esperado do teste de entrada duplicada no ZIP. Diretórios descartáveis removidos; relatórios pequenos e backup anterior mantidos fora do Git.
