# FluidMed: achados em fontes públicas oficiais

Consulta: 15/10/2026. Escopo: páginas oficiais e screenshots promocionais nelas vinculadas. Sem login, inscrição, envio de formulário, compra, contato, endpoints privados ou análise de dados de alunos. Este documento complementa a investigação estática; não contém fórmula recuperada.

## Observações documentais

### Perfil e lógica declarada

A [Jornada](https://www.fluidmed.com.br/jornadaresidenciamedica) declara personalização por ponto inicial, nota alvo, banca e pesos (exemplo 50/30/20), performance por tema/grande área/global, histórico de incidência e estágio da preparação. A lista priorizada informa tema, quantidade e momento. A página cita alocação do tempo disponível, e prefere três revisões extensas a muitas pequenas; o próprio texto enquadra sua evidência como observacional. O ganho divulgado de 17 pontos extras é uma alegação do fornecedor, sem demonstração causal verificável nesta pesquisa. A página menciona aproximadamente 40 variáveis sem enumerar ou publicar os coeficientes.

### Fluxos e interface visíveis

A [página do Super Planner](https://www.fluidmed.com.br/superplannerfluidmed) confirma: cadastro de temas e data da teoria; primeira/segunda/terceira revisões; provas completas; nota alvo por banca, estágio e margem de segurança. O modo por quantidade recebe questões/semana e recalcula até a prova. A nota FluidMed é apresentada como probabilidade de atingir a meta, sem calibração publicada.

Screenshots oficiais da mesma página mostram:

- [Teoria](https://static.wixstatic.com/media/d226d4_70baf5e94ad347a7a6621296d35546fe~mv2.png): tema, área, data e exclusão.
- [Revisões](https://static.wixstatic.com/media/d226d4_b2ae4bc62e5a4254bbed7cf8e92a93ab~mv2.jpg): datas, colunas `N° T`/`N° A`, sugestão, janela de revisão e estado `Atrasado`.
- [Prioridades](https://static.wixstatic.com/media/d226d4_82c92982f1c24c3289c29f19522d378e~mv2.png): tema, área, quantidade e média semanal até a prova.
- [Configuração](https://static.wixstatic.com/media/d226d4_f561307c32d64581b998abbf03b95868~mv2.jpg): banca e nota pretendida.
- [Quantidade](https://static.wixstatic.com/media/d226d4_a601bd95e7494167b6254490062efa8e~mv2.jpg): questões/semana, cálculo e intensidade percentual correspondente.
- [Estatísticas](https://static.wixstatic.com/media/d226d4_19cc7833f5654d84afb353c6de120145~mv2.png): percentuais por revisão/global, total, nota FluidMed, gráficos mensais/área e pesos das bancas.

### Incidência não equivale à intensidade

A [explicação da calculadora](https://www.fluidmed.com.br/bancas-calculadora-intensidade) separa duas bases: questões antigas identificam incidência; notas dos candidatos, concorrência e cortes permitem estimar dificuldade da meta. Uma banca pode existir no direcionamento temático e faltar na calculadora quando não divulga resultados. A orientação pública é estimar intensidade usando outras bancas e cortes; não é publicada a equação de conversão.

### Revisão final

O [guia oficial](https://www.fluidmed.com.br/revisao-final) detalha a sequência: início da revisão, data da prova, banca quando personalizada, questões/dia, quantidade de favoritas por tema, cálculo do cronograma. Recomenda 7–14 dias e informa que o planner reserva a véspera para descanso. Favoritas são a base; faltando questões, completar com novas; esgotadas favoritas inéditas, repetir. O algoritmo é descrito como proporcional quando há favoritas demais. Orienta mesclar temas de diferentes importâncias e planejar revisões separadas ou combinadas conforme distância e prioridade das provas. A referência à média de todas as bancas para ENAMED é explicitamente contextualizada em 2025; não comprova a política de 2026.

### Mudança de classificação de temas

A [atualização R+](https://www.fluidmed.com.br/atualizacao-rmais) documenta Configurações → Definir novo curso, seguido de recadastro de intensidade, data da prova e aba Estudos. Mudanças de taxonomia não tiveram migração automática por ausência de correspondência exata. Isso evidencia dependência entre a classificação de temas e o planejamento, sem revelar sua implementação.

## Inferências e limites

- `N° T`/`N° A` provavelmente representam total e acertos, mas o recorte público não traz a legenda: tratar essa expansão como inferência.
- Incidência ponderada combinada com desempenho é uma base plausível para uma implementação independente; pesos, multiplicadores, curvas e limites seriam decisões próprias.
- Não foram encontrados nas páginas oficiais consultadas campos explicitamente denominados novas/repetidas, data do último contato ou um estado geral de inéditos. A menção a favoritas inéditas é específica da revisão final.
- Não foram observados intervalos matemáticos das revisões, fórmula de prioridade, gatilhos completos de alerta, distribuição diária exata fora da revisão final ou cálculo da nota FluidMed.
- Meta de 90% pode ser configurada como objetivo conceitual; não há evidência pública suficiente para prometer uma carga específica, probabilidade real de aprovação ou réplica do algoritmo.
- Busca pública encontrou cópias de supostos cadernos em terceiros; foram excluídas por não serem fontes oficiais verificadas. Vídeos com transcrição oficial não foram obtidos nesta pesquisa. A página atual da Jornada pede inscrição para as aulas; nenhum formulário foi enviado.

## Cobertura

### Investigação estática com Reverse Engineer Anything

A análise estática usou exclusivamente o HTML e o JavaScript públicos de `https://portal.fluidmed.com.br/relatorios/`, encontrado em link oficial. O bundle foi armazenado sem execução em `fluidmed-public-artifacts/index-tyA-8Z2o.js` (587.104 bytes; SHA-256 `0ad02dbc88f4dc675b054074a029546fbaf80e4b5ff85cfeeda2831cfcde65ca`). O manifesto local registra origens e hashes. Não houve login, consulta privada ou acesso a dados de alunos.

REA registrou um arquivo JavaScript analisado, 120.466 nós AST e 85 achados, sem erro de parsing. A análise semântica atingiu o limite de memória: cobertura parcial, sem recuperação verificável do algoritmo do Planner. Isso fornece evidência sobre o artefato público de relatórios, não sobre todas as rotinas do produto privado. Resumo e identificadores de evidência preservados em [fluidmed-rea-evidence.json](fluidmed-rea-evidence.json). A implementação local é independente, detalhada em [planejador-implementado-v0.8.md](planejador-implementado-v0.8.md).

Respondidos: variáveis declaradas de perfil; etapas teoria/revisões; prioridades visíveis; alerta de atraso; modo semanal/replanejamento; revisão final; distinção incidência/intensidade.

Parciais: nomes exatos de todos os inputs de estudos; distribuição diária; performance/nota.

Não resolvidos publicamente: fórmula e coeficientes; semântica exata de inéditos e último contato; questões novas/repetidas por revisão habitual.
