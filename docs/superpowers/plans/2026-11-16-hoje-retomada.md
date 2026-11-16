# Hoje: clareza, cores e recuperação dentro da carga

Escopo autorizado pelo usuário: redesenhar Hoje, expor atrasos e reagendamento no próprio dia e auditar o método com referências científicas. Execução direta conforme AGENTS.md. Base: 3881882696119b32532f7232801c7832e25cbbb7. Cópia isolada dos arquivos verificados; esta máquina não tem checkout Git nem acesso de rede por shell. Publicação pelo conector GitHub.

## Especificação

- Hoje começa com uma síntese de atrasos e datas reais. Separar temas atrasados com reserva atual daqueles sem data atual; não confundir número de reservas com número de temas.
- Ação curta: encontrar primeiras vagas para os temas sem data atual, em até 90 dias, dentro da carga atual. Preservar reservas de outros temas, descansos e simulados. Mostrar prévia antes de aplicar e permitir desfazer.
- Nenhum atraso aumenta automaticamente a meta. Não inventar resultados, contato ou probabilidade de retenção. O prazo de 90 dias é horizonte de busca, não intervalo pedagógico validado.
- Paleta pastel, contraste legível e identificação por texto. Detalhes e ajustes recolhidos; controles externos extensos permanecem ao final.
- Nenhuma migração do banco: eventos existentes, concorrência e histórico continuam sendo a fonte de verdade.

## Passos e validação

1. Testes de datas vencidas/atuais, deduplicação e prévia curta sem mover reservas existentes. Confirmar RED antes da implementação.
2. Síntese compartilhada de datas, painel Hoje, prévia/aplicar/desfazer e correção dos contadores do Calendário.
3. Paleta suave e redução da informação sempre aberta; manter registro de blocos e recuperação externa acessíveis.
4. Auditoria documentada: separar evidência sobre recuperação/espaçamento de heurísticas de prioridade e limites operacionais. Explicitar que o app ainda não impõe teto de cinco horas.
5. Testes locais de domínio e CI completa com comparação das falhas anteriores; AppTest do fluxo curto. Revisão independente da alteração antes de integrar.

## Critérios de aceite

Datas reais e necessidade de reagendamento visíveis em Hoje; prévia concreta; nenhum resultado alterado por reagendar; reservas futuras preservadas; impossibilidade de encaixe explícita; meta e dias protegidos respeitados; fontes primárias rastreáveis; não prometer 90% de acerto/aprovação.
