# Cabeçalho, menu e complemento opcional

28/10/2026 · base8cf63e8. Pedido: corrigir o Olá cortado, alinhar o menu e permitir encerrar o tema após cumprir o Planner, preservando revisão.

## Resultado

- Hoje reserva76px acima do conteúdo no desktop e72px no celular; cabeçalho nativo mede60px. O menu alinha o conteúdo interno e textos quebrados à esquerda, mantendo ícones/foco nativos.
- Encerrar tema hoje aparece em Hoje e Calendário quando há capacidade conhecida positiva no Planner, a quantidade registrada cumpre essa capacidade e só falta complemento. O app não identifica IDs de questões; o usuário confirma que concluiu a lista ao usar a ação.
- O tema sai da lista restante daquele dia; outros blocos continuam. A quantidade dispensada fica separada do total respondido, com Desfazer dispensa e data de revisão indicada pelo cálculo existente. A meta continua sendo a referência configurada; dispensadas não preenchem a barra.
- Retornos vinculados já devidos não podem ser dispensados. A fila futura de erros/convicção permanece; extras explícitos e novas reservas são respeitados. Dose e intervalo futuros usam acertos, amostra e contatos reais.
- A agenda existente recebe eventos imutáveis planner_complement.skip/restore, com token de concorrência, capacidade/data de origem e escopo de crédito da reserva. Reservas antigas desse encontro não arrastam o complemento ao futuro. Correção/exclusão que retire a quantidade mínima reativa o saldo. Nenhuma migração ou evento fictício de estudo.

Arquivos: planner_completion.py e planner_completion_ui.py, integrações em AdaptiveService/StudyAgenda, previsão e telas Hoje/Calendário, bento.css, dois arquivos novos de testes e um harness sintético. Nenhum teste preexistente alterado. Originais e diretrizes não rastreadas do usuário preservados; nenhum acesso à plataforma Osler.

## Prova

RED observado antes da implementação do serviço e botão; GREEN após integração. `.venv/Scripts/python.exe -m pytest -q` → **893 passed,1 skipped,1 warning**,271.59s. Skip: symlink indisponível no Windows. Warning: ZIP duplicado deliberado do teste de backup.

Após ajuste final para preservar metadados de planos sem dispensa ativa, testes focados de dispensa/UI/revisão final: **22 passed**,13.63s. Antes desse ajuste, dispensa/UI/compatibilidade do Planner: **25 passed**,8.24s. Cobrem recarga, desfazer/repetir, acertos/revisão inalterados, crédito de ontem, correção/exclusão, token/data inválidos, retornos devidos, reservas novas, extras explícitos, complemento respondido depois e ações nas duas telas.

Revisão independente planner_completion_review identificou e confirmou correções de reutilização do digest, crédito anterior da reserva, novas reservas do dia e histórico/desfazer no Calendário. Revisão incremental aprovada, sem achados pendentes.

`scripts/check_planner_completion.py depois` passou em Edge/Playwright:1366×768,1912×1045 e390×844, lateral aberta e fechada. Estado real confirmado por data-collapsed e geometria após transição. O botão nativo de recolher aparece ao passar o mouse. Olá em76/72px, cabeçalho termina em60px, sem overflow de página. Alinhamento esquerdo medido. Encerrar acionado por Enter; desfazer e repetir exercitados nas três larguras sem criar eventos de estudo. Capturas abertas e inspecionadas. As primeiras tentativas do harness não aguardavam o estado real da lateral; o harness final corrige isso.

Evidências locais ignoradas pelo Git: evidencias/planner-complementos/depois.json, depois-*, opcao-*, encerrado-*. Apenas cenários sintéticos temporários8602; zero requisições externas. Servidor e pasta descartável encerrados automaticamente. Nenhum teste no banco real8501. Emulação de navegador; aparelho físico/leitor de tela não testados.

Detector Impeccable executado uma vez neste ajuste: um warning overused-font em bento.css:3, Inter exigida pelo briefing. Retorno1 no conjunto Python/CSS; não se declara scan completo/limpo do Python. Contraste/foco reutilizam tokens já verificados. Sem fases4–5 do redesign neste ajuste.
