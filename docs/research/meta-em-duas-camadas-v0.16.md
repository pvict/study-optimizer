# Meta de aprendizagem e referência de prova — v0.16

**Fonte.** Especificação fornecida pelo usuário para o lote A e dados de corte informados no cadastro com fonte obrigatória. Nenhum corte foi buscado, inferido ou preenchido automaticamente. Mantêm-se os limites estatísticos descritos em [modelo estatístico](modelo-estatistico-proposto.md) e [revisões sucessivas](revisoes-sucessivas-v0.11.md).

**Hipótese de produto.** Um objetivo de aprendizagem por tema e uma referência histórica/documental de prova respondem a perguntas diferentes. A meta dos temas é comparada com acertos com convicção em questões novas, com amostra suficiente. É global, com substituição opcional por grande área. As fórmulas anteriores de espaçamento, dose e alocação são mantidas; a configuração por área resolve o parâmetro de meta antes das chamadas existentes. Sem substituições, o alvo e as regras permanecem compatíveis com os perfis antigos.

O corte de prova é armazenado na escala informada e pode ser apresentado como `100 × cutoff_score / max_score`. A fonte e o estado informado/conferido/estimado ficam explícitos, sem validar automaticamente a fonte. Editar e desconsiderar acrescentam eventos imutáveis; não apagam versões.

**Data de planejamento.** A prova principal selecionada prevalece. A seleção automática usa a futura mais próxima; se todas passaram, usa a mais recente e o app mantém o aviso de prazo passado. Sem cadastro ativo, preserva a data configurada no perfil (default30/11/2027). A data derivada é resolvida em leitura; não regrava versões antigas do perfil nem se torna o fallback ao salvar outra preferência.

**Limite.** Corte pode mudar entre edições, modalidades de acesso e etapas; a escala pode não representar apenas questões objetivas. A referência não incorpora concorrência, currículo, pesos ou dificuldade e não estima aprovação. A meta por tema não garante aquela nota e não transforma PDF, acumulado ou questões repetidas em primeiras tentativas. A confidência da fonte é uma declaração de procedência, não uma probabilidade calibrada. A configuração não fabrica estudos, contatos, convicção ou progresso.
