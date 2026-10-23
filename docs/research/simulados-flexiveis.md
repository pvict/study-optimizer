# Simulados com datas flexíveis — 0.24.0

## Funcionamento

Em **Simulados → Programação** ou **Calendário → Programar ou mudar datas dos simulados**, escolha a primeira data e o intervalo inicial. A série reserva os dias até a prova de referência, limitada ao horizonte de 18 meses. O intervalo sugerido salvo em Ajustes serve como padrão de criação; mudá-lo não desloca silenciosamente datas de uma série existente.

Cada ocorrência mantém sua identidade original. Mover 25/10 para 27/10 deixa 01/11, 08/11 e as demais datas intactas. É possível retirar somente uma ocorrência ou restaurá-la em outra data. A prévia precisa ser aplicada para mudar o calendário. Datas duplicadas, anteriores ao início da preparação ou fora do horizonte são recusadas.

O dia reservado substitui a meta de blocos normais. Não exige fazer o simulado mais 120 questões e não aumenta a carga de outros dias. “Simulado programado” é reserva, não realização. Os resultados reais continuam em **Simulados → Resultados**, com seu próprio denominador. Havendo resultado registrado na data, o calendário informa a realização; datas passadas ou já registradas não podem ser movidas como se ainda fossem planos futuros.

## Temas e capacidade

A prévia calcula os próximos contatos antes e depois de retirar a capacidade dos dias reservados. Mostra tema específico, data anterior, nova data prevista, quantidade e prioridade. Usa as regras já existentes de incidência, desempenho, tempo sem contato, cotas de novos/revisões, doses e retornos conhecidos. Nenhum parâmetro estatístico foi alterado.

Reservas explícitas afetadas são remanejadas no StudyAgenda. Antes de exibir datas, o cálculo recompõe a ordem exata das reservas que será aplicada e simula novamente. Temas sem reserva explícita permanecem na fila dinâmica, com a nova data prevista no cenário; não se cria uma dívida por cada contato hipotético. Lotes conhecidos mantêm sua data de origem e vencimento: o plano pode indicar falta de vaga, sem fingir que a revisão foi feita.

A comparação começa com 28 dias; uma ocorrência distante amplia a análise até 14 dias após a data afetada, respeitando fim da preparação e limite de 18 meses. Toda a série reserva capacidade no calendário e na Evolução; a tabela detalhada se limita ao período identificado na prévia. Temas que perderem vaga nesse horizonte ficam explicitamente sem data ali. Isso não significa que foram apagados ou suspensos.

Datas e doses futuras são condicionais: resultados, mudanças de rotina e novas incidências podem reorganizar a agenda. A prévia aplicada é uma fotografia auditável, não uma garantia de vaga imutável nem de retenção. O calendário operacional recalcula após resultados reais.

## Conflitos, histórico e reversão

Datas de prova cadastradas e programação especial de revisão final/descanso/simulado realizado são protegidas. Ocorrências padrão que coincidam com esses dias aparecem como não reservadas; uma mudança manual para um conflito é recusada. Ao montar revisão final, um simulado na véspera precisa ser movido antes de reservar o descanso final.

A programação usa somente eventos versionados `reschedule.apply`, escopo `mock_schedule`, no StudyAgenda existente, com token, prévia, aplicar e desfazer. Não há nova tabela ou migração de schema; o banco continua na versão 12. A versão substituta referencia a anterior, sem apagá-la. Desfazer restaura a versão efetiva anterior, inclusive em cadeias de várias mudanças. Se isso alteraria datas passadas ou com resultados, a reversão em bloco é recusada: ajuste somente as próximas ocorrências.

Para reverter a implementação completa e o planejamento, preserve os dados atuais e use o backup anterior em outra pasta com o código anterior. Apenas voltar o código pode ignorar o novo tipo de reserva e reabrir metas que haviam sido dispensadas.

## Verificação

Testes cobrem datas independentes, colisões, retirada, passado, cronograma, resultados já registrados, troca de versão, desfazer em cadeia, aderência, conflitos de revisão final, retorno de sete dias, limites diários, comparação de prévia com reservas concorrentes e AppTest de programação/mudança. Validação real é feita em cópia mínima do banco, sem inserir estudos fictícios no banco ativo.

Entrega de 23/10/2026: **626 testes passaram em 164,03 segundos**, com o aviso intencional já existente de ZIP duplicado. A revisão independente reproduziu conflitos de ordem entre reservas concorrentes, reversão de datas passadas e sobreposição com a véspera de prova; todos foram cobertos por regressões RED/GREEN e corrigidos. Detector do Impeccable sem achados e verificação de whitespace limpa.

Na cópia mínima dos dados reais, criação da série, mudança de 25/10 para 27/10 e AppTest de Simulados/Calendário passaram sem exceções, preservando eventos e a meta de 120. A programação real autorizada foi aplicada: **58 ocorrências a partir de 25/10/2026, a cada sete dias**. Todas as linhas anteriores foram preservadas; 57 arquivos de origem conferidos por hash. Nenhum resultado de simulado ou estudo fictício foi criado.

Backup anterior à programação real: `data/backups/osler_20261023T185819Z_7f9e67d062c6db1a.zip` (5.829.169 bytes, schema 12). Evidências pequenas em `tmp/mock-schedule-*`, fora do Git. A prévia real compara até 19/11/2026: 141 próximos contatos mudam de data, 23 ficam sem data nessa janela; permanecem na fila dinâmica, sem virar dívida artificial. Isso é o custo de retirar dias de capacidade, não uma previsão de fracasso ou esquecimento.

Conferência visual no navegador local: Calendário exibe “Simulado programado” em 25/10; Simulados → Programação mostra a próxima data e os controles de mudança individual, com texto inteiro. Hoje continua com 120 questões. Não foram alteradas datas reais só para produzir capturas. Verificação em aparelhos físicos permanece pendente.
