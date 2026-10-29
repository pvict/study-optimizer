---
name: Osler — Bento, estudo e acompanhamento
description: Interface Bento local de estudo, acompanhamento, flashcards, arquivos e ajustes.
colors:
  primary: "#4F46E5"
  primary-deep: "#4338CA"
  page: "#F6F7FB"
  surface: "#FFFFFF"
  soft: "#F3F4F6"
  ink: "#111827"
  muted: "#4B5563"
  ink-tertiary: "#6B7280"
  line: "rgba(17,24,39,.08)"
  field-line: "#6B7280"
  field-bg: "#FFFFFF"
  selected: "#EEF2FF"
  selection: "#EEF2FF"
  success: "#111827"
  success-bg: "#F3F4F6"
  warning: "#111827"
  warning-bg: "#F3F4F6"
  danger: "#111827"
  danger-bg: "#F3F4F6"
  track: "#E5E7EB"
  neutral-outline: "#9CA3AF"
  sand: "#F5F1EA"
  sand-ink: "#5B4A32"
  clinica-fill: "#4F46E5"
  clinica-tint: "#EEF2FF"
  clinica-ink: "#3730A3"
  clinica-solid: "#4338CA"
  cirurgia-fill: "#FF6B6B"
  cirurgia-tint: "#FFF1F0"
  cirurgia-ink: "#B42318"
  cirurgia-solid: "#B42318"
  pediatria-fill: "#10B981"
  pediatria-tint: "#ECFDF5"
  pediatria-ink: "#047857"
  pediatria-solid: "#047857"
  go-fill: "#8B5CF6"
  go-tint: "#F5F3FF"
  go-ink: "#6D28D9"
  go-solid: "#6D28D9"
  preventiva-fill: "#F59E0B"
  preventiva-tint: "#FFFBEB"
  preventiva-ink: "#92400E"
  preventiva-solid: "#92400E"
  neutral-fill: "#6B7280"
  neutral-tint: "#F3F4F6"
  neutral-ink: "#374151"
  neutral-solid: "#374151"
typography:
  body:
    fontFamily: '"SF Pro Display","SF Pro Text",-apple-system,BlinkMacSystemFont,"Inter","Segoe UI",system-ui,sans-serif'
    fontSize: "15px"
    lineHeight: "22px"
    fontWeight: 400
  headline:
    fontSize: "32px"
    lineHeight: "38px"
    fontWeight: 700
    letterSpacing: "-.022em"
  headline-narrow:
    fontSize: "24px"
    lineHeight: "30px"
  title:
    fontSize: "20px"
    lineHeight: "26px"
    fontWeight: 650
    letterSpacing: "-.012em"
  caption:
    fontSize: "13px"
    lineHeight: "18px"
  eyebrow:
    fontSize: "11px"
    lineHeight: "16px"
    fontWeight: 700
  chip:
    fontSize: "12px"
    lineHeight: "16px"
    fontWeight: 600
  navigation:
    fontSize: "14px"
    lineHeight: "20px"
  mobile-field:
    fontSize: "16px"
    lineHeight: "22px"
  metric:
    fontSize: "40px"
    lineHeight: "44px"
    fontWeight: 700
  metric-compact:
    fontSize: "28px"
    lineHeight: "34px"
    fontWeight: 700
rounded:
  button: "14px"
  squircle: "34px"
  card: "24px"
  medium: "16px"
  small: "12px"
  pill: "999px"
spacing:
  gap: "16px"
  card-padding: "24px"
components:
  bento-card:
    backgroundColor: "{colors.surface}"
    rounded: "{rounded.card}"
  bento-status:
    backgroundColor: "{colors.soft}"
    textColor: "{colors.ink}"
    rounded: "{rounded.pill}"
---

# Design System: Osler — Bento (fases 1–5)

## Direção e escopo

**Clareza para estudar, um bloco de cada vez.** Interface Operate local para preparação de residência, em português simples, no computador e no celular. O briefing aprovado é `docs/redesign/PROMPT-CODEX-REDESIGN-BENTO-OSLER.md`; suas regras e valores vencem sugestões genéricas das skills.

As cinco fases estão aplicadas: fundação, navegação lateral, Hoje, Temas/Registrar, Calendário/Simulados/Evolução e Flashcards/Arquivos/Ajustes. O redesign preserva regras de estudo, prioridade e histórico. Versão 0.28.0.

Fontes normativas: `osler/bento.css` (tokens e base), `osler/bento.py` (primitivas puras e variações fixas), `osler/study.css` (estrutura existente), carregados nesta ordem por `study_style.py`. `.streamlit/config.toml` alinha o tema nativo e serve a fonte local. O sidecar `.impeccable/design.json` espelha estes valores; não cria rampas adicionais.

## Cores e estados

PáginaF6F7FB, superfíciesFFFFFF, tinta111827 e apoio4B5563. Índigo4F46E5 identifica seleção e ação; primário sólido4338CA permite texto branco. A fonte terciária6B7280 é reservada para branco: usar apoio4B5563 na página e em superfícies tintadas, pois o contraste depende do fundo.

Cada área usa quatro papéis: `fill` decorativo, `tint` de fundo, `ink` textual e `solid` para botão com texto branco. Valores exatos `--a-<slug>-<papel>` estão no CSS e espelhados no frontmatter. CoralFF6B6B e âmbarF59E0B nunca são texto. Slugs: clinica, cirurgia, pediatria, go, preventiva, neutral. Os nomes de origem são Clínica Médica, Clínica Cirúrgica, Pediatria, Ginecologia e Obstetrícia, Preventiva & Social. Não substituir por Cirurgia Geral.

Estado é texto em chip neutro: Dominado, Aprendendo, Em alerta e Sem estudo. Em alerta tem borda mais forte e fundo branco; não usa vermelho. Sem fonte Material local, o helper HTML omite o ícone e mantém o rótulo. Widgets que já usam Material continuam nativos. Mensagens técnicas nativas permanecem acessíveis; não confundir vermelho de erro do sistema com estado de aprendizagem.

Os aliases `--study-*` mantêm os módulos existentes funcionando. Sucesso/aviso/atraso de estudo têm tinta neutra nesta base. Os raios e agrupamentos legados são preservados; não aplicar a nova geometria Bento a telas ainda não migradas.

## Tipografia local

Pilha aprovada: SF Pro Display, SF Pro Text, -apple-system, BlinkMacSystemFont, Inter, Segoe UI, system-ui, sans-serif. Nenhuma fonte SF Pro é incluída ou servida pelo projeto. Se já estiver instalada no sistema, o navegador pode usá-la; em sua ausência, Inter local é a substituta, seguida dos fallbacks.

Inter4.1 variável, peso100–900, arquivo `static/fonts/InterVariable.woff2`, servido em `/app/static/fonts/InterVariable.woff2`; licença em `docs/third-party/Inter-OFL.txt`. Fonte oficial: https://github.com/rsms/inter/releases/tag/v4.1. SHA256:693b77d4f32ee9b8bfc995589b5fad5e99adf2832738661f5402f9978429a8e3. Download ocorre na preparação; nenhum recurso remoto em runtime. `font-display:swap` e configuração nativa `theme.fontFaces` preservam widgets e tabelas.

Título32/38, móvel24/30 até760px, peso700; seção/card20/26, peso650. Corpo15/22; apoio13/18, tinta4B5563. Até3tamanhos por card novo. Campos16px no celular. Números tabulares. O token de métrica40/44 está preparado para a composição futura; não aumenta automaticamente as métricas legadas.

Contraste é medido no resultado, não só na declaração: a base remove a opacidade nativa de60% do `stCaptionContainer`, que diluía o texto. Preservar opacidade reduzida de controles desabilitados e estados transitórios do Streamlit.

## Primitivas e segurança

`area_slug`, `eyebrow`, `chip`, `pct`, `ring`, `bar` e `area_styles` não consultam nem gravam dados. Textos/labels HTML são escapados; classes usam allowlists. Rejeitar números negativos, bool, strings, NaN e infinito. Excedente pode preencher o progresso visual até100%, conservando o numerador real no rótulo. Ausência é None/traço com indicação acessível; nunca resultado zero inventado. Metas visuais fora de0–1 e tamanho de anel fora de32–512px são inválidos.

HTML é estático; ações continuam em widgets nativos, com keys, callbacks e foco preservados. A barra não cria previsão, estimativa de aprovação ou dose de estudo. Cor de área só categoriza; estado de aprendizagem mantém origem no domínio.

O anel SVG usa `st.markdown(ring(...), unsafe_allow_html=True)` apenas para o HTML estático validado do helper. O sanitizador de `st.html` no Streamlit1.66 remove SVG; não habilitar JavaScript para contornar isso. Os estilos do anel aceitam as duas âncoras estáveis dos renderizadores. A fixture visual confirma arco e rótulo40/60 no navegador.

## Componentes e composição por fase

Novos containers `.st-key-bento-*`: raio24px, padding24px, gap16px e sombra suave exatos do briefing. Variantes por área são geradas por laço Python referenciando tokens, sem duplicar valores. Primário14px no contexto Bento, altura44px, um por contexto. `corner-shape:squircle` é melhoria progressiva com raio34px; sem suporte, mantém24px. Não depender dela para funcionamento.

Na fase1 as páginas existentes continuam com seus agrupamentos, largura máxima1240px, formulários, grids de calendário e listas paginadas. Não mudar a sequência das ações nem montar o layout completo das prévias. Raio12px das superfícies legadas permanece até sua migração. Não inserir identidade pessoal ou progresso demonstrativo no app real.

## Acessibilidade e responsividade

Seletores novos são ancorados em keys ou `data-testid`; nenhum seletor de classe gerada. Foco visível3px índigo, afastamento3px. Botões nativos têm alvo mínimo44x44px, inclusive incrementos e ícones auxiliares. Campos com rótulo e borda clara; estados acompanhados por texto. O CSS não altera a família de spans de ícones Material.

Campos numéricos, texto e textarea usam a borda de foco do próprio Streamlit, sem outline interno adicional. Botões, links e escolhas mantêm o foco3px de teclado. Não remover a seleção de texto nem o indicador de foco nativo do container do campo.

Hoje reserva76px de topo no desktop e72px até900px para o cabeçalho fixo nativo de60px, incluindo lateral recolhida. O menu alinha também o wrapper interno nativo e textos quebrados à esquerda.

Cobertura: o mínimo habitual de questões admite exceção para acervo positivo menor. Temas específicos com conteúdo próprio além dos filhos são praticáveis, sem reclassificar is_leaf da fonte; a ficha informa escopo abrangente e sobreposição. Registro no pai não atualiza filhos automaticamente. Contagens importadas sobrepostas não são somadas à base global. A tabela informa quantas unidades têm data prevista; nunca criar data fictícia para ocultar falta de capacidade. Evidência: docs/design/2026-10-28-cobertura-sem-exclusao.md.

Respeitar `prefers-reduced-motion`; remover transição e deslocamento decorativo nos componentes Bento. As regras existentes de empilhamento e tabelas continuam; composição nova em uma coluna até900px pertence à migração das telas. Testar390,768,1366 e1440px; zoom200% e teclado. Sem declaração de conformidade WCAG completa a partir de CSS/AppTest.

## Dados, evidência e limites

Na fase4, Calendário abre na Semana quando ainda não há preferência salva. Navegação mensal mantém o dia quando possível, respeitando os limites do seletor. Sete colunas no desktop e duas até760px. Hoje tem contorno e a seleção tem fundo índigo claro; previsão tem borda tracejada e rótulo. "Com registro" indica estudo lançado, sem alegar meta diária concluída. A faixa Reorganizar e as opções de prevenção preservam prévias, aplicar e desfazer; atalhos abrem seu destino automaticamente.

Simulados mantém Programação/Resultados: resumo antes do formulário, métricas informadas e amostra perto do percentual. Corte exige vínculo e instituição compatível; somente nota com escala informada é comparada. Barras por área trazem Wilson95% descritivo, sem inferir temas ou nota de prova.

Evolução abre em Histórico (registros reais) e preserva Cenários como navegação secundária. A amostra de acerto usa apenas novas com acertos exatos; convicção usa o subconjunto com convicção informada, incluindo zero. Volume inclui blocos novos/repetidos/mistos. Referência semanal aplica a rotina atual somente aos dias decorridos, com legenda explícita de que metas históricas podem ter sido outras. Não converter arquivo importado em tentativas novas nem projetar ganho de nota no histórico.

Métricas compactas de acompanhamento usam28/34px, peso700, com labels/apoio13/18px. A fonte do valor alcança o parágrafo interno nativo do Streamlit. A jornada dos Cenários usa lista HTML estática e adaptável, pois st.html sanitiza SVG; cada marco mantém data e rótulo realizado/previsto. O helper SVG antigo continua disponível por compatibilidade.

As quatro larguras desta fase são1440,1366,768 e390px. Dados e servidores de QA são sintéticos, temporários, na8602. Evidências, rubrica e limites: docs/design/bento-fase4-entrega.md.

Uso local, sem acesso à conta Osler. Suspensão/reativação manuais. Questões novas, repetidas, mistas, simulados, PDFs e cards continuam separados; todo percentual exige amostra ou rótulo correspondente. Data de PDF não vira contato e percentual revisado não vira acerto. Meta90% não é previsão de nota ou aprovação.

`scripts/seed_demo_data.py` cria apenas dados sintéticos em pasta temporária nova e recusa data, banco preexistente, pasta existente e caminhos indiretos. `scripts/capture_bento.py` inicia servidor próprio na porta8602, usa esse cenário e bloqueia recursos remotos. Capturas identificadas como sintéticas em `evidencias/bento/fase1/`; banco de produção não é usado na validação. Playwright é dependência de desenvolvimento, navegador instalado reutilizado.

Resultado, rubrica, contrastes e limitações desta fase: `docs/design/bento-fase1-entrega.md`. As prévias orientam a linguagem; seus números e textos pedagógicos não são fatos do produto. As páginas de fases futuras continuam sem alegação de redesign concluído.


## Fase2 — navegação e Hoje

Menu lateral único com marca própria, Registrar bloco, cinco destinos de estudo, Flashcards/Arquivos e Ajustes. main_view e adaptive_view continuam como chaves de sessão; os dois radios de navegação foram retirados. Os demais seletores pertencem às suas telas.

Hoje: saudaçãoOlá enquanto não existe nome configurado, subtítuloUm bloco de cada vez, data do dia de estudo (corte04h), hero do primeiro item real e cor de área, anelHoje, ritmo de sete dias, Para fazer/Feito hoje, pausa opcional e faixaSua semana. Nome em Ajustes continua na fase5. Dados de exemplo só aparecem nos cenários de teste, nunca no aplicativo real.

Hero e restante da lista compartilham controles antigos de registro, troca e complementos. Lotes preservam session_id/review_of; apenas a primeira ação é primária. Quando são retornos/complementos, os rótulos específicos continuam no lugar deRegistrar este bloco. Detalhes de erros e trajetória ficam emVer próximas revisões; Planner parcial continua visível. Volume acima da meta não oculta temas restantes. Meta registrada só substitui o hero se não há blocos pendentes.

O estado de descanso usa areia. Simulado oferece o destinoSimulados; descanso de revisão final aponta paraCalendário. Sem relatório, háImportar relatório; antes do início, não há cobrança. Nenhum caso sem meta escreveX de0: mostra o número registrado e explica a ausência de meta.

Resumos da semana são somente leitura: volume de blocos registrados (inclui repetições); acerto apenas em novas com contagens exatas e n; dominados sem pais históricos; distância até prova efetivamente cadastrada. Simulados contam como dia com estudo, mas não entram nos denominadores de blocos. Hora emFeito hoje é a hora de registro/atualização em Brasília, não hora de conclusão inferida.

Pausa de10min após pelo menos um bloco hoje, dispensável, em fragmento Streamlit. Guarda deadline monotônico só na sessão; não escreve estudo, não bloqueia nem altera o cronograma.

Bento: colunas2:1 com gap16px; até900px uma coluna. Lateral recolhida no celular, sem largura mínima imposta ao estado fechado. Formulários e campos mantêm o foco discreto existente. Hero/lista usam11/13/20px; o apoio compacto é13px. Fontes e tokens continuam os da fase1; estado HTML mantém rótulo textual sem ligatura Material não empacotada.

Evidência desta fase: docs/design/bento-fase2-entrega.md e evidencias/bento/fase2. Somente dados sintéticos e porta8602 em QA. Nome/cadastro e redesenho das outras telas permanecem fora do escopo.

Variantes documentadas: raio14px de botões,34px apenas com corner-shape, fonte14px de navegação,16px de campos móveis, E5E7EB como trilho decorativo e9CA3AF como contorno decorativo de dias. O estado continua expresso por texto/símbolo, sem depender do trilho ou contorno para leitura.

## Fase3 — Temas e Registro

Temas mantém Tabela como entrada e oferece Lista em cards de duas colunas,12 por página e uma coluna até900px. Busca e filtros nativos conservam chaves; atalhos neutros por estado e pills por área com contagens. Cards mostram tema específico, acerto exato na modalidade identificada com n, convicção principal com fonte, meta e próxima revisão do calendário. Em Todas, o card usa novas para o acerto; a tabela e os totais mantêm o recorte original. PDF, retrato Osler, acumulado e tentativas nunca são somados como evidência independente. Ausência é traço; zero informado continua zero.

Registrar é um card central de no máximo680px. Escolha de tema recolhida quando há tema específico, tipo do registro visível, três contagens em linha ou empilhadas até900px. Erro do modelo aparece junto ao campo, preservando valores. Aproximado, metadados, cards criados, importação e correção continuam disponíveis. Após salvar: toast, total real do dia, Próximo bloco e Voltar ao plano. Próximo usa o primeiro item atual e a alocação existente de lotes, sem gravar estudo nem perder review_of. Sem meta, o resumo informa essa ausência.

Abas Erros, Plano de corte e Minha meta preservadas. Erros paginados12; atalho por tema limpa motivo residual. Corte, confiança da fonte e Wilson são dados cadastrados/observados; nenhuma previsão de aprovação. CSV consolidado permanece com fontes separadas. Feedback do registro usa superfície e texto neutros, sem alterar sua mensagem ou regra.

Escala dos cards11/13/20px; padding24 e gap16; fontes e tokens da fundação. Estado neutro, cor apenas da área nos elementos previstos. Detector manual desta fase listou Inter, exigida pelo briefing, e retornou código1 no conjunto misto Python/CSS: não é prova de cobertura completa do código Python. Evidência e limitações: docs/design/bento-fase3-entrega.md. As entregas posteriores estão documentadas nos relatórios das fases4–5.

## Fase5 — Flashcards, Arquivos e Ajustes

Cards de erros apresentam respostas de hoje, saldo da primeira passagem e referência diária em grandezas distintas. A barra mede apenas a passagem do lote; explicações ficam em Entender o saldo e a carga. Decks inteiros têm registro visível antes de Por que este deck. Importação, repetição, desfazer e dias especiais conservam as regras anteriores.

Redução de revisões mostra três fontes separadas: total estudado declarado no PDF selecionado; cartões estudados nos temas sugeridos para avaliação seletiva; média da consulta de revisões por período informada pelo usuário, datada e com origem. Nenhuma dessas medidas é economia de revisões, cartões a suspender ou domínio. Ausência permanece traço; zero informado permanece zero. Recomendações e salvaguardas vêm da política existente.

Arquivos abre pela Biblioteca e Importar relatórios. Inspeção, auditoria, cruzamento e classificação ficam no expander Avançado; seleção de relatório e ferramentas legadas permanecem em outro Avançado. Backup tem atalho e retorno à Biblioteca. Nomes completos continuam disponíveis junto às fontes, além da tabela rolável.

Ajustes organiza Meta e rotina, Minhas provas e Instituições e incidências em superfícies Bento. A meta diária e a proporção vêm primeiro. Nome opcional fica recolhido e vale somente na sessão, sem gravar ou alterar o perfil estatístico. A saudação escapa Markdown. Na seção de incidência, tempos do roteiro legado ficam preservados em sua ferramenta original; o formulário atual salva as instituições conservando os demais campos. Revisões, simulados e calibração continuam acessíveis em Avançado.

Mesmo raio24, padding24, gap16 e escala compacta28/34; empilhamento até900px, campos móveis16px, foco discreto e teclado preservado. A biblioteca usa tabela com rolagem interna e alternativa de nomes completos. Auditoria geral e limitações de navegador, fonte, contraste e zoom: docs/design/bento-fase5-entrega.md. Não confundir viewport emulado com aparelho físico nem zoom CSS com zoom nativo.

## Treinos por área e correção — v0.29

Simulados acrescenta duas abas nativas, Treinos por área e Correção. Preserva tokens, fonte local, lateral e superfícies Bento. O primeiro passo é configurar o rodízio; depois aparecem agenda, mudanças por ocorrência e registro curto do resultado. Correção oferece busca digitada/hierárquica pelo tema específico, quantidade opcional de erros e prévia datada antes de reservar a prática. Fontes e regras avançadas ficam recolhidas.

Hoje mostra o treino reservado e o dia de correção junto ao plano; Calendário identifica ambos sem inventar estudo concluído. Tabelas têm rolagem própria e controles conservam os alvos nativos de teclado/toque. QA sintético com Edge em 1440, 1366, 768 e 390px, sem estouro horizontal do documento ou exceções nas 16 combinações de tela/tamanho. Capturas não equivalem a teste em aparelho físico. Método e limites em docs/research/treinos-e-correcao-de-simulados.md.
