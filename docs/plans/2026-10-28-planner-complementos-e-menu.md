# Complementos opcionais e correções de navegação

Usar Superpowers:executing-plans, Impeccable e Revenue-Centric Design. Escopo aprovado na solicitação; AGENTS dispensa novas aprovações para decisões reversíveis.

## Comportamento

- Reservar espaço real para o cabeçalho fixo do Streamlit em desktop e celular, com lateral aberta/fechada. Alinhar conteúdo interno dos botões do menu à esquerda, incluindo textos quebrados.
- Após registrar ao menos a quantidade documentada no Planner, oferecer Encerrar tema hoje para dispensar somente o complemento externo. Não oferecer com saldo de retorno vinculado devido, quantidade zero ou capacidade desconhecida. Mostrar antes da ação a quantidade dispensada e preservar a opção de buscar o complemento.
- Registrar a escolha na agenda imutável existente, com token de concorrência e capacidade/data de origem. Não escrever evento de estudo, inventar acertos nem reduzir dose/intervalo futuros. Correção ou exclusão que retire a quantidade mínima desfaz o efeito automaticamente; permitir desfazer manualmente.
- Retirar o tema apenas da lista do dia, preservando os demais blocos. Resolver reservas antigas desse encontro na agenda para não arrastar o complemento ao calendário; novas reservas e revisões futuras continuam válidas. Retornos por erros/convicção permanecem na fila.
- Exibir a dispensa separada das questões realizadas. A meta e o total respondido continuam reais; não preencher a folga automaticamente com outros temas.

## Implementação e prova

- [x] Reproduzir o cabeçalho/alinhamento com cenário sintético e medir antes; CSS ancorado em data-testid/keys.
- [x] Testes RED para serviço, persistência/reload, correção/exclusão, desfazer, concorrência, casos não elegíveis, reservas/calendário e ausência de alteração de desempenho/revisão.
- [x] Helper de decisão no domínio da agenda; integração no AdaptiveService/StudyAgenda sem migração. Atualizar quantidades/contadores da apresentação após retirar o complemento.
- [x] Controle reutilizado em Hoje/Calendário, histórico de dispensas e desfazer. AppTest do fluxo real.
- [x] Testes focados, suíte completa e navegador desktop/celular, menu aberto/fechado, foco e nome longo. Só dados sintéticos8602; temporários por TemporaryDirectory.
- [x] Revisão do diff, documentação e commit local; nenhuma operação na plataforma Osler.

## Verificação e revisão

Suíte893passed,1skipped,1warning;22focados após o ajuste final sem alteração de metadados quando não há decisão. Navegador com seis combinações de largura/lateral, sem corte/overflow, ação por Enter, desfazer e repetir. Revisão independente aprovada após correção dos quatro casos de borda. Relatório: docs/design/2026-10-28-planner-complementos-e-menu.md.
