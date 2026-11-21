# Registro e capacidade do plano

Base `74b2044`. Escopo aprovado após a auditoria de Hoje. Aplicar mudanças de interface e de leitura, com Superpowers e Revenue-Centric Design.

- Registro: apresentar primeiro tema e campos do bloco. Recolher mudanças de tipo e percentuais, manter edição, importação e registro vinculado. Preservar a quantidade do bloco contextual. Na entrada global, manter o registro avulso editável.
- Agenda e rendimento: mostrar sinais separados em Hoje e Temas. Extrair acerto baixo da evidência objetiva que o planejador já calculou. Usar a data de revisão para prazo. Conservar o estado interno e a ordem da fila.
- Capacidade: listar revisões devidas que ficaram fora de Hoje e sinalizar atrasos ainda sem data de recuperação. Respeitar a indisponibilidade declarada e a conclusão parcial. Mostrar a data reservada, quando conhecida.
- Cards: indicar carga mínima por deck para um dia inteiro. Distinguir margem habitual, limite explícito e retomada. Conferir o efeito dos dias de deck grande sobre questões.
- Validar com cenários sintéticos, testes de UI e checagem no navegador. Manter pesos, intervalos e doses durante a etapa.

## Verificação

- Registro aberto a partir do bloco de Hoje em um cenário sintético. Em tela de 390 px, o tema precede o formulário, a quantidade proposta vem preenchida e a opção de mudar o tipo fica recolhida.
- A revisão de código verificou a reserva futura para um atraso já confirmado e o limite mínimo de cada deck. O valor do deck considera a carga já feita e pode exigir espaço adicional quando há outros decks prioritários.
- A retomada aplica até 30 questões nos dias de deck grande, respeitando um teto configurado menor ou uma meta efetiva do dia.
- Os 117 testes dos fluxos afetados passaram. A suíte geral teve 1.235 aprovados e 9 ignorados. As três falhas eram de expectativas de texto de simulados herdadas da remoção do rótulo redundante de amostra. Após ajustar essas expectativas, o arquivo de simulados passou com 10 testes.
