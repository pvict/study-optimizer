# Evolução: cobertura com espaçamento condicional

## Correção

O primeiro modelo repetia os mesmos intervalos até o fim da preparação. O controle de capacidade mantinha as revisões dessa pequena carteira e restringia novos temas; o volume de respostas crescia, mas a cobertura permanecia quase constante. O seletor de períodos estava funcionando: a limitação era o cenário calculado.

Agora Evolução tem duas referências, identificadas em “Premissas e carga da simulação”:

- **Atingindo a meta nas revisões** (inicial): contatos completos supõem convicção suficiente para avançar os intervalos. Essa hipótese pode liberar espaço para novos temas.
- **Mantendo os intervalos atuais**: reproduz a referência anterior, sem presumir avanço.

O Calendário operacional continua usando a segunda referência por padrão. Somente resultados reais atualizam seu espaçamento observado. Comparar cenários não grava perfil, resultados, compromissos ou pendências.

## Política matemática e fronteira da evidência

A hipótese reaplica a política já usada em `topic_spacing.py`: após contatos qualificantes espaçados, intervalos-base de7e14dias, seguidos de `ceil(intervalo_base × facilidade)`. Sob o sucesso condicional, facilidade aumenta0,1, limitada a1,3–3. O intervalo-base fica limitado pelo máximo entre contatos configurado. Incidência contrai o intervalo pelo fator `1 + 0,5 × incidência_normalizada`; arredondamento é para cima. A fase final limita o intervalo a um quarto dos dias restantes, com mínimo1dia. Acompanhamento de cartões reduzidos mantém teto14dias.

Não se alonga o intervalo por um lote isolado de erros, bloco inferior ao mínimo, segundo contato no mesmo dia ou sinal adverso manual. O histórico de espaçamento observado inicializa o cenário; avanços futuros ficam em `projected_spacing` dentro de uma cópia, sem alterar a evidência original.

O [SM-2 original](https://super-memory.com/english/ol/sm2.htm) descreve progressão multiplicativa e ajuste heurístico de facilidade por resposta. Os7/14dias, agregação em temas e demais limites são a adaptação explícita **do aplicativo**, não a fórmula original nem uma dose clínica validada. O [FSRS oficial](https://github.com/open-spaced-repetition/awesome-fsrs/wiki/The-Algorithm) usa estados de memória e histórico por item; estes dados não existem integralmente nas tabelas importadas. Não se apresenta esta simulação como FSRS ou curva pessoal calibrada.

## Restrições e limites

- Alocação mantém questões/dia, máximo de temas/dia, doses, mínimos, saldos conhecidos, distribuição, descansos, início, agenda e prova. A projeção não preenche artificialmente todos os temas nem obriga cada período a crescer.
- Doses e medidas de rendimento conhecidas são mantidas. Nenhum número futuro de acertos, posterior, domínio ou conquista real é criado.
- Cobertura é a união de temas específicos documentados e contatos com questões previstos. Repetir o mesmo tema não aumenta a cobertura; segurança acumulada não é uma nova tentativa.
- A simulação considera atendida a quantidade dos lotes conhecidos quando alocada; não cria novos lotes ou resíduos hipotéticos de erros que retornariam em7dias. Erros/faltas futuros podem ocupar mais vagas e reduzir a cobertura. Portanto, **é um cenário condicionado à execução e ao sucesso, não uma previsão probabilística**.
- O máximo de dias entre contatos não é aumentado para fazer a curva subir. Com capacidade de manutenção esgotada, a cobertura pode estabilizar legitimamente; a interface explica os limites. Revisões/respostas conhecidas que aguardariam vaga na data são apresentadas nas premissas, sem criar dívida real.

## Verificação

Regressões cobrem: mais admissões com avanço; preservação do cenário operacional; limite de carga/temas; início/descanso/prova; exclusão de lotes isolados, blocos curtos, mesmo dia e sinais adversos; estado de origem intacto; serviço sem gravação; mudança de cenário invalida cache e mudança de período reutiliza a simulação completa.

AppTest usa dados sintéticos ou cópia isolada dos arquivos importados. Validação visual no navegador permanece indisponível pela restrição já registrada; não se afirma inspeção de renderização ou responsividade. O modelo não muda schema nem adiciona dependências.
