# Prioridade dos próximos contatos do histórico importado

Pedido: corrigir Saúde do Trabalhador com vaga em março de 2027 e aplicar a correção à fila inteira.

## Diagnóstico

O tema tinha contato conhecido em 02/10/2026, intervalo de referência de 17 dias e alta incidência. A fila inicial usava o score de lacuna e incerteza, com urgência temporal saturada, sem proteção operacional pelo afastamento máximo. A ordem calculada na consulta também era reaproveitada pelas admissões futuras, embora o calendário avançasse de dia. O resultado era 02/03/2027 para esse tema e 12/04/2027 para Contracepção.

O limite conservador de admissões continua existente: agenda regular, carga, proporção novos/revisões, descanso e simulados são restrições reais. Remover todas essas restrições ou atribuir datas ideais sem vaga produziria uma previsão enganosa. Não foi necessário alterar intervalos nem ajustar a incidência importada para corrigir a postergação.

## Decisão de implementação

Usar a política existente de ordenação, compartilhada entre os consumidores, em vez de criar um segundo calendário ou forçar datas para nomes específicos.

- [x] Reproduzir a postergação em teste com muitos temas fracos concorrentes.
- [x] Para tema estudado, sem compromisso recorrente do app e com contato conhecido, calcular `initial_contact_deadline = last_contact + max_contact_gap`.
- [x] Ao atingir essa data, usar `score + importance` para ordenar a fila inicial. Antes dela, usar o score existente.
- [x] Recalcular a ordem no dia da admissão e da alocação. A prevenção também usa a mesma chave.
- [x] Preservar compromissos vencidos e sinais adversos explícitos antes da fila ordinária. Preservar reservas e escolhas manuais.
- [x] Incrementar a versão da política para invalidar previsões em cache.
- [x] Revisão independente: corrigida a exceção da prevenção, com reprodução vermelha e teste verde. Sem outros riscos P1/P2 identificados.
- [x] Repetir o diagnóstico do conjunto atual após a correção da prevenção: mesmas datas e cobertura completa.
- [x] Reiniciar o servidor local com o código atual e conferir `/_stcore/health`: `ok`.
- [x] Suíte final: 910 testes passaram, 1 ignorado (symlink indisponível no Windows), 1 aviso esperado no teste de ZIP duplicado, em 262,17 segundos.

A verificação visual adicional ficou indisponível por falha do controle do navegador (`browser.user is unavailable`). As datas foram verificadas no mesmo cálculo usado pela tabela, com dados atuais em RAM e origem somente leitura. Não foi apresentada uma captura antiga como evidência do código novo.

## Limites da interpretação

O bônus é uma regra operacional proporcional à incidência, não uma fórmula científica de esquecimento nem uma estimativa de probabilidade de acerto. Aumenta a preferência por contato, mas não garante um prazo rígido se a capacidade estiver ocupada. Um tema remoto de baixa incidência não ultrapassa automaticamente um tema muito mais incidente com dificuldades relevantes.

O histórico continua como fila inicial, sem centenas de atrasos inventados. PDFs não passam a informar contato ou fornecer amostra binomial. Não foram alterados denominadores, resultados, incidência, parâmetros de espaçamento ou registros do usuário. A data exibida continua sendo a vaga produzida pelo calendário, condicionada aos próximos resultados.

## Prova e auditoria

Teste sintético: um tema importante com último contato em 02/10 chega ao limite de 30 dias em 01/11; com descanso nesse dia, recebe vaga real em 02/11, apesar de 60 diagnósticos fracos concorrentes. Outros casos cobrem incidência/desempenho, ausência de contato conhecido, compromisso real, reagendamento e prevenção.

Diagnóstico do conjunto atual: conexão de origem SQLite em `mode=ro`, snapshot somente em RAM, originais apenas lidos. Evidências pequenas em `evidencias/cobertura/prioridade-rastreamento.json` e `prioridade-depois.json` (fora do Git). Nenhuma cópia integral em disco foi criada.

No primeiro cálculo corrigido: 1.490 temas com vaga, zero sem data, máximo de 120 questões regulares; Saúde do Trabalhador em 10/11/2026 e Contracepção em 18/11/2026. Nos 20 temas de maior incidência da fila inicial, o maior prazo passou de 168 para 34 dias e a mediana de 31,5 para 19 dias. Esses valores descrevem o cenário calculado, não estudo concluído.
