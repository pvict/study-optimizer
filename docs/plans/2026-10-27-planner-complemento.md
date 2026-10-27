# Questões do Planner e complemento no banco completo

Execução direta com Superpowers (investigação, TDD e verificação), conforme autorização do usuário e AGENTS. Revisão da apresentação com Revenue-Centric Design e Impeccable, preservando a base visual existente.

## Comportamento aprovado

O Planner é uma fonte parcial: sua contagem não reduz a dose da revisão nem limita o acesso futuro ao tema. Mostrar a recomendação total, a quantidade documental do Planner com data, o que foi registrado e o complemento a buscar no banco completo. Não presumir que há questões inéditas no banco completo: recomendar a busca e manter a origem/limitação explícita.

Para o caso investigado somente por leitura: Planner10/6, reservas20/15, registros10/6. Permanecem complementos10/9, mas não são falhas de execução da parcela coberta pelo Planner. Não apagar nem reescrever reservas, PDFs ou registros. Não modificar inferência estatística, critérios de domínio ou intervalos.

## Implementação e provas

- [x] Helper puro em planner_snapshot.py compara a recomendação e o realizado com a quantidade do retrato; desconhecido/futuro não vira zero. A cobertura é quantitativa, sem inferir identidades ou questões distintas a partir de tentativas.
- [x] Alocação mantém dose/questões; acrescenta contexto à revisão e às reservas antigas. Pendência externa permanece registrável.
- [x] Atraso de plano perdido considera somente a parcela coberta pelo Planner. Prazos de revisão reais e lotes de erros continuam válidos; não declarar tema dominado nem revisão integralmente feita.
- [x] Hoje, Calendário e feedback explicam o complemento; não mostram a diferença indisponível como recuperação atrasada.
- [x] Testes sintéticos:10/20,6/15; parcial real; fonte ausente/zero/futura; correção/desconsideração; repetição futura; calendário e apresentação. Rodar regressões relevantes e suíte completa. QA sem escrita no banco real.

Arquivos responsáveis: planner_snapshot.py (leitura/comparação documental); adaptive_planning.py (anotação do bloco); study_replanning.py (atraso real); study_components.py e consumidores (mensagem). Sem novo schema, dependência ou acesso à Osler. Testes em diretórios temporários próprios; preservar arquivo não rastreado de diretrizes e os dados do usuário.

## Registro da implementação

Confirmado por leitura do SQLite e dos retratos importados: PDF de14/10/2026 com27/15questões; Planner de20/10/2026 com10/6; reservas20/15 e registros10/6. Não trocar total do banco completo por total do Planner: são capacidades diferentes. A solução mantém os complementos10/9 e sua ação de registro; muda sua explicação e a contabilização de atraso por indisponibilidade.

`study_agenda.py` passa a preservar o contexto de disponibilidade nos novos planos diários, usando o payload já existente. Assim uma importação posterior não muda a capacidade documental daquela proposta. Correções/desconsiderações recalculam o saldo com os registros ativos; não usam a contagem antiga do aviso como evidência de estudo. A inferência estatística, os limiares de domínio, a política de intervalo e a dose não foram alterados.

Regressões específicas:73testes aprovados, incluindo agenda, trocas, excedentes diários e feedback. Depois foram acrescentadas duas regressões de preservação da disponibilidade entre importações. Suíte final: `.venv/Scripts/python.exe -m pytest -q` → **832passed,1skipped,1warning em230.91s**. O skip é a criação física de symlink indisponível neste Windows; warning de ZIP duplicado deliberadamente no teste de backups, já existente. Nenhum teste preexistente alterado. Os13novos casos estão em tests/test_planner_supply.py. Diff sem erro de whitespace. Commit separado, integração local, sem push.

QA em Edge instalado: cartão sintético com20recomendadas,10noPlanner e10registradas. Em1366e390px, sem overflow, aviso visível e botão Registrar complemento; sem texto de atraso original. Capturas inspecionadas: `evidencias/planner-complemento/complemento-1366.png` e `complemento-390.png`; resultado em `qa.json`. Cenários temporários removidos automaticamente, sem cópia dos dados ativos. As imagens são de teste, não mostram estudos do usuário.

Limites: quantidade importada é retrato datado, não consulta em tempo real. A comparação por volume não identifica questões distintas nem garante que o banco completo terá exemplares inéditos suficientes. A orientação é buscar o complemento, preservando a liberdade de revisitar o tema. Uma revisão que vencer no futuro continua sendo revisão devida; não confundir isso com a antiga diferença de disponibilidade.
