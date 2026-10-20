# Rotina adaptativa — v0.18

## O que mudou

Perfis existentes seguem no modo fixo, por compatibilidade. O modo adaptativo pode ser ativado em uma ação no Calendário ou em Ajustes; a ativação salva nova versão e preserva questões/dia, proporção de referência, início e demais preferências. Não há migração de schema, reimportação de resultados ou acesso à Osler.

Na rotina adaptativa, o orçamento de novos é o menor entre a proporção escolhida e as questões restantes após a demanda de revisão comprometida devida. A entrada inicial de temas novos e de diagnósticos já vistos verifica suas repetições nos próximos14dias contra carga e vagas de temas disponíveis, incluindo descansos, metas por dia e adicionais temporários. Intervalos atuais permanecem constantes nessa verificação. Isso é controle conservador de entrada, não previsão calibrada de memória ou otimização global. Compromissos existentes e solicitações explícitas do usuário podem continuar excedendo capacidade; o risco permanece contabilizado.

Doses seguem necessidade, exposição, incerteza e incidência. No modo fixo, o preenchimento anterior das cotas permanece; no adaptativo, os blocos automáticos são limitados à dose recomendada e não crescem apenas para preencher a meta. A carga escolhida é teto, não promessa de preencher todas as questões todos os dias. Extras manuais e recuperações agendadas preservam sua quantidade dentro das restrições diárias.

## Questão e tema têm retornos diferentes

Um lote identificável de erros/acertos sem convicção mantém o retorno de7dias. O lote é vinculado à tentativa original e apenas acertos com convicção saem dessa fila. Esses resultados continuam fora da amostra de primeiras tentativas. Qualquer prática atualiza o último contato, conforme informado pelo usuário.

Um bloco de revisão vinculado a lote não é nova evidência independente para reiniciar o intervalo integral do tema. A data integral usa o último bloco pertinente, inclusive quando o bloco de origem foi menor que o mínimo; não usa o contato do lote como substituto. Quando apenas o lote está devido, o bloco recebe a quantidade de respostas pendentes, respeitando o mínimo configurado, sem adiar a revisão completa. Vários lotes no mesmo dia têm suas quantidades somadas.

Blocos reais não vinculados, com convicção informada e quantidade suficiente, continuam atualizando o SM-2 adaptado a temas: sucessos espaçados permitem7,14e expansão limitada pelo máximo configurado; rendimento fraco reduz o intervalo. Incidência ajusta a frequência. Essas regras são políticas operacionais, não parâmetros ajustados estatisticamente ao indivíduo. A previsão não inventa sucessos ou expansão futura dos intervalos.

## Transparência da comparação

O Calendário compara os dois modos desde o estado atual até a mesma janela, contando revisões em risco, questões programadas, temas novos e dias com redução de novos. Menos entradas pode reduzir cobertura; essa troca fica visível. Nenhum cenário é aplicado só por abrir a comparação. Ativação usa a versão atual do perfil; prévias antigas são invalidadas por dados e versão3.0 da política. A simulação mantém o desempenho atual: longas pausas de novos precisam ser revistas conforme os resultados reais, não tratadas como recomendação permanente.

## Base e limites

- [FSRS, documentação oficial](https://github.com/open-spaced-repetition/awesome-fsrs/wiki/The-Algorithm): dificuldade, estabilidade e recuperabilidade são atualizadas a partir de respostas datadas. Um percentual acumulado de segurança por tema não fornece esse histórico individual; não afirmamos implementar FSRS por tema.
- [Manual oficial do Anki: retenção, carga e simulador](https://docs.ankiweb.net/manual/deck-options): explicita a relação entre frequência, retenção desejada e carga, além do uso de histórico para ajuste. Isso fundamenta tratar carga como restrição; não valida os coeficientes de dose ou os14dias escolhidos aqui.
- [Política inicial e fontes anteriores](priorizacao-inicial-v0.17.md): percentuais recuperados da Osler são descritivos e separados dos posteriores de primeiras tentativas.

Os14dias, doses e limites são hipóteses de operação transparentes. Não garantem retenção, cobertura completa ou90% em prova. Para estimar curvas pessoais e benefício marginal por tema, faltam séries de resultados em contatos espaçados; a implementação não preenche essa lacuna com dados simulados.
