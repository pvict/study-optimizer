# Segurança acumulada e desempenho em questões novas

Fonte: definições do usuário para o Planner Osler. O denominador corresponde a questões distintas já vistas. Erros ou acertos sem convicção retornam para revisão; acertar com convicção numa revisão melhora o percentual sem aumentar o denominador. Contato inclui questões novas e revisões. Essas definições foram confirmadas em20/10/2026; não houve acesso à plataforma.

Interpretação: percentual descritivo do estado recuperado de questões conhecidas, não taxa de sucesso de tentativas independentes ou de primeiras tentativas. Valores arredondados são preservados; não se reconstrói um número inteiro de acertos, não se soma o retrato a sessões e não se calcula posterior binomial ou chance de aprovação a partir dele. Segurança acumulada alta, isoladamente, não comprova domínio em questões inéditas.

Integração: somente retratos com semântica confirmada, hash íntegro, caminho local permitido, data não futura e relatório de referência compatível. Associação por caminho exato; pais não transmitem desempenho a filhos. Retratos subsequentes substituem os caminhos presentes, sem somar versões. Ausência de métrica permanece desconhecida. Um retrato corrompido é ignorado com aviso.

Segurança abaixo da meta, com pelo menos5 questões distintas, sinaliza prioridade; abaixo de60%, com pelo menos10, sinaliza urgência. São regras de triagem explícitas, não limiares validados de aprovação. O sinal expira após a janela recente configurada e cede a blocos novos/mistos posteriores ao retrato. Percentuais altos não reduzem a incerteza do posterior de questões novas. As fórmulas de repetição espaçada e dose não foram alteradas.

Contato é derivado da data confirmada do retrato menos os dias informados e combinado por máximo com contatos registrados. Isso registra evidência de contato sem inventar uma sessão ou um horário. O saldo de inéditas usa o retrato mais recente que o PDF e subtrai apenas blocos novos estritamente posteriores. Blocos no mesmo dia deixam o saldo sinalizado como incerto, pois não há horário para saber se já estavam incluídos.

Pendências da tabela são apresentadas como pendências no retrato. Sem IDs de questões e datas de entrada na fila, não se fabricam vínculos nem vencimentos individuais de7dias e não se somam essas contagens à fila de sessões do aplicativo. Em particular, “dias sem contato” não informa a data em que cada questão entrou na revisão.

Na tabela, Segurança acumulada Osler fica separada de acerto/convicção do período. Questões distintas, data e pendências são detalhes opcionais. A data do retrato acompanha o contexto, que não deve ser interpretado como medição realizada dentro do período filtrado.
