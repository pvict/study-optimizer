# Pesos por prova e próxima revisão — v0.24.1

## Correção e fontes

A implementação anterior substituía o conjunto de instituições pelos nomes das provas com peso personalizado. Com apenas uma tabela conjunta, a seleção de uma única prova deixava a fonte sem aplicação: a distribuição passava à exploração uniforme e o plano de hoje mudava. O peso incompatível foi retirado criando uma nova versão do perfil, sem restaurar o banco inteiro, alterar resultados ou retirar simulados programados.

Agora pesos modificam a importância das provas e preservam as demais instituições do conjunto. Para habilitar a ponderação, todas as instituições participantes precisam ter tabelas individuais aplicáveis, com data até o dia de estudo e massa positiva em temas associados. Uma tabela conjunta nunca vira incidência individual. Arquivos futuros, vazios ou apenas com linhas sem associação não habilitam pesos. O bloqueio existe no armazenamento, além da tela.

Perfis antigos incompatíveis usam o conjunto original com pesos neutros e um aviso. A simples chegada de arquivos individuais não reativa pesos antigos: é necessária uma nova prévia. A confirmação vincula os pesos às provas e às instituições, impedindo ativação silenciosa após renomear uma prova ou mudar o conjunto. Pesos antigos salvos diretamente nas instituições podem ser retirados pela mesma prévia, mesmo se não houver mais provas ativas; os nomes permanecem selecionados.

## Prévia antes de aplicar

Em Ajustes → Minhas provas → Importância das provas e aviso de aproximação, o usuário confere:

- instituições e pesos antes/depois, incluindo retirada de pesos antigos;
- fonte, data e unidade das tabelas individuais;
- cobertura da incidência, carga diária, data de referência e aviso de aproximação;
- temas e quantidades do plano de hoje antes/depois;
- incidência, prioridade e estado dos temas que mudam;
- próximos contatos que mudam de data, quantidade, entram ou perdem vaga na janela comparada.

A comparação detalhada dos próximos contatos cobre até 28 dias, limitada ao fim da preparação. Mudanças posteriores à janela não são listadas ali; os pesos aplicados passam a valer nos cálculos futuros. Acerto, convicção, registros de estudo e parâmetros de repetição não são reescritos. A prévia não grava resultados ou reservas fictícias. O token do planejamento é revalidado no momento de salvar, dentro da transação: novos dados exigem recalcular a prévia.

## Próxima revisão em Temas

A coluna Próxima revisão aparece junto ao tema e ao estado, tanto em Histórico da Osler quanto em Blocos registrados no app, também em Lista e no CSV filtrado. A busca por um tema mantém essa coluna visível.

A data vem do próximo bloco com vaga no calendário operacional. O cálculo respeita capacidade, simulados, descanso, retornos conhecidos e reservas explícitas, até o fim da preparação, limitado a 548 dias. Para temas não vistos, essa é a data do primeiro contato. Não é a data ideal de vencimento: Revisão devida e Tipo do próximo bloco ficam em Mais filtros → Exibir mais estatísticas.

Se não houver vaga no horizonte, o app mostra “Sem vaga prevista até …”; não inventa data nem considera o tema apagado. Fora do catálogo e preparação encerrada também têm textos próprios. Resultados futuros podem alterar as datas. O cache usa dia e versão dos dados; mudanças entre a construção da visão e o cálculo invalidam a consulta e oferecem atualizar a tabela.

## Preservação e validação

Schema permanece em 12. O perfil ganha apenas o campo opcional de confirmação `exam_weight_basis`; nenhuma fórmula ou parâmetro estatístico foi recalibrado. Backup anterior à retirada do peso preservado em `data/backups/osler_20261023T194645Z_d579c35429fe2cd1.zip`. Para reverter código e planejamento integralmente, preserve o banco atual e use o backup com o código correspondente em outra pasta. Uma volta isolada do código pode ignorar as novas proteções ou não reconhecer o campo do perfil.

Regressões cobrem fontes conjuntas/individuais, datas futuras, massa zero, conjunto preservado, perfis antigos, prévia sem escrita, alteração concorrente durante aplicação, limpeza de pesos legados, consulta de tema em ambas as fontes e separação entre data devida e vaga real. AppTest valida bloqueio e recuperação; a cópia mínima dos dados reais preserva estudos e simulados, com tabela pesquisável e previsão calculada. A avaliação visual em navegador local não substitui teste de toque em aparelho físico.

Entrega de 23/10/2026: **645 testes passaram em 189,70 segundos**, com um aviso intencional do teste de ZIP duplicado. Revisão independente apontou bloqueio de limpeza de pesos legados e corrida entre visão/cache; ambos foram reproduzidos por regressões RED/GREEN e corrigidos. Detector estático dos arquivos de UI sem apontamentos e whitespace conferido.

A previsão completa levou aproximadamente 10,6 segundos na cópia mínima real e fica em cache até os dados ou o dia mudarem. Navegador local em largura de 614 px mostrou pesos desabilitados com instruções legíveis e a busca de Estudos Epidemiológicos com próxima revisão em 24/10/2026. A comparação do banco ativo com o backup preservou todas as linhas anteriores, incluindo os novos estudos feitos pelo usuário durante a entrega. As cópias descartáveis foram removidas automaticamente; evidências pequenas ficam em `tmp/weights-contacts-*`, fora do Git.
