# Simulados locais — lote B

**Fonte.** Especificação B2 fornecida pelo usuário em [lote B](../roadmap/lote-B-dados-novos.md), registros manuais do estudante e referências de prova cadastradas com fonte. Nenhuma nota, corte, banca ou questão é buscada em plataformas. A referência de desenho é a skill Revenue-Centric Design instalada, particularmente `checkout-and-forms` (reduzir esforço percebido pedindo apenas o necessário) e `dashboards-and-data-viz` (um painel deve orientar a próxima ação). Essas referências orientam a interface; não demonstram eficácia educacional desta política.

**Hipótese de produto.** Data, nome, total e acertos permitem registrar um simulado rapidamente. Tipo de prova, instituição, vínculo com prova-alvo, tempo, nota, condições, observação e resultados por área/tema ficam recolhidos. A intenção é um registro básico em menos de um minuto; os testes funcionais não medem tempo real de uso. Resultados por grande área ajudam a escolher o que revisar, sem inferir o desempenho dos subtemas.

## Fontes e denominadores

O resultado de cada simulado aparece separado dos PDFs, dos acumulados e das tentativas de estudo. O gráfico apresenta cada simulado como um ponto e identifica a instituição; não agrega resultados de bancas diferentes numa média. Questões em branco contam no total e não nos acertos. Nota e nota máxima são opcionais e fornecidas juntas; o acerto simples não substitui uma nota ponderada.

A referência de corte só aparece quando existe vínculo explícito com uma prova cadastrada e a instituição informada coincide após normalização. A diferença em pontos percentuais exige nota e nota máxima do simulado. A comparação não corrige dificuldade, edição, modalidade de acesso, pesos ou condições; o alerta sobre bancas e prova real permanece visível. Sem nota na escala da prova, o corte é apenas referência documental, sem subtrair a taxa de acerto das questões.

## Conversão explícita e correções

Salvar um simulado não cria contatos nem blocos. A ação **Adicionar como blocos de questões novas** só aceita uma declaração explícita de questões inéditas e resultados por tema específico reconhecido de forma única como folha no catálogo atual. Uma grande área ou um tema desconhecido não é repartido em subtemas. Cada bloco recebe `mode='novas'`, origem `Simulado <nome>` e convicção desconhecida. O usuário deve evitar lançar as mesmas questões outra vez no Registro; não há identificação individual das questões para detectar sobreposição com outras fontes.

Os IDs dos blocos derivam da chave do simulado e do caminho normalizado de cada tema. Validar todos os temas, conferir a versão do simulado e inserir os eventos ocorre numa transação. Repetir a conversão conserva os mesmos eventos; restaurar o backup preserva essa idempotência. Se um bloco foi corrigido manualmente, a conversão não sobrescreve a correção.

Correção e desconsideração de um simulado criam nova versão e preservam o original. Enquanto houver blocos ativos daquela conversão, ambas são bloqueadas. A ação **Retirar blocos desta conversão** desconsidera explicitamente esses blocos antes da correção, dentro de uma transação e com verificação de revisões dependentes. Os eventos anteriores permanecem. Blocos alterados manualmente exigem conferência e desconsideração no Registro, para não perder ajustes do usuário. Depois de retirar os anteriores, a nova versão pode ser convertida sem manter blocos obsoletos, inclusive quando muda a lista de temas.

## Rotina e calendário

O intervalo sugerido é opcional, em dias; zero desativa a sugestão. Ele usa a data do último simulado ativo e não cria agendamento, dívida ou atraso automaticamente. **Considerar este dia como feito** exige prévia e aplicação explícita, com opção de desfazer pelo histórico de calendário. As questões do simulado não entram por essa ação no denominador de desempenho dos blocos.

**Limites.** Um simulado não é a prova real; bancas e condições diferem. Meta de 90% e corte informado não são probabilidades nem garantias de aprovação. Resultados por tema são declarações do usuário, sem acesso ao enunciado ou à identidade individual da questão. Resultados incompletos por área/tema não são completados por inferência. Não houve alteração nas fórmulas de espaçamento. AppTest verifica os fluxos funcionais; inspeção visual em celular e medição do tempo de registro exigem avaliação de uso separada.
