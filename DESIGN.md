---
name: Osler — estudos locais
description: Interface de estudo azul, clara e direta para computador e celular.
colors:
  primary: "#2563eb"
  primary-deep: "#1d4ed8"
  page: "#f5f7fb"
  surface: "#ffffff"
  ink: "#172b4d"
  muted: "#52627a"
  line: "#dce3ed"
  selected: "#e8efff"
  selection: "#dbeafe"
  success: "#166534"
  success-bg: "#f0fdf4"
  warning: "#9a3412"
  warning-bg: "#fff7ed"
  danger: "#991b1b"
  danger-bg: "#fef2f2"
typography:
  body:
    fontFamily: "sans-serif"
    lineHeight: 1.55
  headline:
    fontSize: "1.9rem"
    fontWeight: 700
    lineHeight: 1.2
    letterSpacing: "-.025em"
  title:
    fontSize: "1.3rem"
    fontWeight: 650
    lineHeight: 1.3
    letterSpacing: "-.015em"
  title-small:
    fontSize: "1.1rem"
    fontWeight: 650
    lineHeight: 1.4
  caption:
    fontSize: ".875rem"
  label:
    fontSize: ".9rem"
    fontWeight: 600
  chip:
    fontSize: ".8rem"
    fontWeight: 600
  dose:
    fontSize: ".9rem"
    fontWeight: 650
  metric:
    fontSize: "1.85rem"
    fontWeight: 650
rounded:
  badge: "6px"
  control: "8px"
  surface: "12px"
spacing:
  tight: ".2rem"
  small: ".4rem"
  compact: ".5rem"
  gap: ".8rem"
  base: "1rem"
  shell-medium: "1.25rem"
  shell-wide: "2rem"
components:
  button-common:
    rounded: "{rounded.control}"
  form:
    backgroundColor: "{colors.surface}"
    rounded: "{rounded.surface}"
  expander:
    backgroundColor: "{colors.surface}"
    rounded: "{rounded.surface}"
  study-block:
    backgroundColor: "{colors.surface}"
    rounded: "{rounded.surface}"
  navigation-selected:
    backgroundColor: "{colors.selected}"
    textColor: "{colors.primary-deep}"
    rounded: "{rounded.control}"
    padding: ".45rem .65rem"
    typography: "{typography.label}"
  dose:
    backgroundColor: "{colors.selected}"
    textColor: "{colors.primary-deep}"
    rounded: "{rounded.badge}"
    padding: ".35rem .55rem"
    typography: "{typography.dose}"
  status-learning:
    backgroundColor: "{colors.selected}"
    textColor: "{colors.primary-deep}"
    rounded: "{rounded.badge}"
    padding: ".2rem .5rem"
    typography: "{typography.chip}"
  status-success:
    backgroundColor: "{colors.success-bg}"
    textColor: "{colors.success}"
    rounded: "{rounded.badge}"
    padding: ".2rem .5rem"
    typography: "{typography.chip}"
  status-warning:
    backgroundColor: "{colors.warning-bg}"
    textColor: "{colors.warning}"
    rounded: "{rounded.badge}"
    padding: ".2rem .5rem"
    typography: "{typography.chip}"
  calendar-late:
    backgroundColor: "{colors.danger-bg}"
    textColor: "{colors.danger}"
    rounded: "{rounded.badge}"
    padding: ".25rem .4rem"
    typography: "{typography.chip}"
---

# Design System: Osler

## Overview

**Creative North Star: "Clareza para estudar"**

A identidade existente combina azul, superfícies claras e controles familiares. A direção Operate valoriza leitura rápida e ações de estudo evidentes: mostrar o que falta, oferecer o próximo bloco e deixar ajustes e explicações em segundo plano. O uso confirmado abrange computador e celular.

Este documento registra o código atual, sem criar uma identidade nova. A referência normativa é `osler/study.css`, aplicada por `study_style.py`, com componentes em `study_components.py`, `study_day_ui.py`, `study_tables_ui.py`, `study_calendar_ui.py` e `adaptive_ui.py`, mais o tema de `.streamlit/config.toml`. Os tokens acima registram valores reutilizados; estilos e comportamento nativos dependem do Streamlit 1.66. A cascade efetiva do navegador não foi inspecionada.

**Key Characteristics:**
- Português simples, ações específicas e detalhes recolhidos.
- Azul como acento; estados sempre acompanhados por texto.
- Tipografia nativa, números alinháveis e conteúdo com quebra de linha.
- Mesma tarefa disponível em computador e celular, sem depender de hover.

## Colors

Um azul nítido organiza a navegação e as ações sobre uma base clara e fria. Os nomes abaixo apontam para os tokens do frontmatter, sem criar outra paleta.

### Primary
- **Azul de ação** (`primary`): acento do tema e cursor de edição.
- **Azul de foco** (`primary-deep`): contorno de foco, navegação selecionada, dose e estado Aprendendo.
- **Azul suave de seleção** (`selected`): fundo de navegação ativa, dose, Aprendendo e recuperações no calendário.
- **Azul de seleção de texto** (`selection`): seleção de texto com tinta principal.

### Neutral
- **Fundo frio** (`page`) e **superfície branca** (`surface`): página e agrupamentos de trabalho.
- **Tinta** (`ink`) e **texto de apoio** (`muted`): hierarquia entre informação principal e contexto.
- **Linha clara** (`line`): separadores e borda lateral da barra de ferramentas.

Os pares `success` / `success-bg`, `warning` / `warning-bg` e `danger` / `danger-bg` são semânticos, não acentos decorativos: Dominado, Em alerta ou pendências previstas, e atrasos. Mensagens nativas de sucesso/erro mantêm o tratamento do Streamlit; estes pares não comprovam as cores computadas desses alertas.

As rampas OKLCH do sidecar são auxiliares de visualização calculados a partir das cores existentes; não são tokens adicionais nem cores usadas pela aplicação. O frontmatter continua normativo.

**The Estado Legível Rule.** Cor reforça um rótulo explícito; nunca substitui o estado, a data ou a quantidade.

## Typography

O tema pede `sans-serif`, sem fonte remota ou família de display própria. A família efetivamente resolvida e os tamanhos não sobrescritos permanecem a cargo do Streamlit e do navegador.

- `headline`, `title` e `title-small`: título da tela, seções e blocos; não usar caixa alta promocional.
- `body`: entrelinha comum de parágrafos e listas; não estabelece um tamanho global de corpo.
- `caption`: caminhos de temas e explicações secundárias, em texto de apoio.
- `label`, `chip` e `dose`: navegação, estados e quantidade do bloco.
- `metric`: resumo numérico. Métricas, doses e resumo de lista usam algarismos tabulares.

Em viewport até (760px), o título principal passa a (1.65rem), o valor das métricas do resumo a (1.55rem), seu rótulo a (.8rem) e a dose a (.85rem). Campos recebem tamanho de (16px) nessa faixa. Palavras longas podem quebrar em títulos, parágrafos e rótulos.

## Layout

O conteúdo tem largura máxima de (1240px), com margens internas (2.2rem 2rem 4rem). Até (1000px), o espaço horizontal passa a (1.25rem). Até (760px), usa (1.2rem max(1rem, env(safe-area-inset-left)) 3rem). Não presumir comportamento de safe area além dessa regra existente.

Na tela Hoje, trabalho e apoio usam proporção (1.85:1); em largura estreita, colunas passam a uma pilha. Resumo e filtros de estado conservam três colunas compactas. A navegação tem cinco destinos, reflui para três colunas e, com container até (350px), para duas, com o último destino ocupando a linha. O container `study` também ativa a composição estreita até (700px), independentemente da largura da janela.

Calendário oferece Agenda, Semana e Mês; Agenda é a primeira opção. A grade semanal/mensal passa a sete colunas explícitas até (1000px) e a duas na faixa estreita. Tabelas têm largura contida; Temas oferece Lista paginada em até 12 itens, com ações por tema, como alternativa à rolagem horizontal. Não esconder funções essenciais por largura.

Os breakpoints são regras implementadas, não prova de renderização em dispositivos. A matriz de referência do trabalho é (320, 390, 768, 1024 e 1440px).

## Elevation & Depth

O CSS próprio usa superfícies claras, separadores e fundos semânticos para agrupar informação. Não define sombras. Bordas e eventuais sombras dos containers e controles nativos pertencem ao Streamlit; não foram extraídas de estilos computados.

**The Agrupamento Útil Rule.** Um container deve reunir uma tarefa ou seu contexto; não adicionar camadas decorativas para cada linha de informação.

## Shapes

Os três raios do frontmatter distinguem rótulos compactos, controles e superfícies. Formulários, expanders e blocos recebem a curva de superfície; botões e opções de navegação, a curva de controle; doses e badges, a curva de rótulo. Não substituir esse vocabulário por pílulas ou cartões com cantos excessivos.

Foco próprio: contorno sólido (3px) em azul de foco, afastado (3px), para botões, links, inputs, textarea e summary; rótulos também recebem contorno quando contêm input em foco visível. Não remover o foco para obter uma superfície mais limpa.

## Components

### Buttons

Controles nativos com ação concreta. CSS próprio define altura mínima de (44px), quebra de texto, raio de controle e foco visível. As cores, bordas, padding e estados hover/active/disabled de variantes nativas não foram inspecionados; `primaryColor` é configuração de tema, não uma extração da aparência computada de cada botão.

O primeiro bloco de Hoje usa `type='primary'`; demais blocos usam `secondary`. O dia selecionado no calendário é primário. Salvar resultado e salvar planejamento são ações primárias explícitas. Transições próprias de fundo e borda duram (150ms ease-out); com movimento reduzido são removidas. Não acrescentar efeitos de deslocamento.

### Inputs / Fields

Usar widgets nativos e rótulos visíveis. O estilo próprio define cursor azul, placeholder em texto de apoio e foco; não determina borda, fundo ou raio dos campos. Radio, checkbox e summary têm altura mínima própria de (44px). Isso é uma regra de CSS, não confirmação por medição de todos os alvos de toque.

### Navigation

Grupo radio nativo com Hoje, Calendário, Temas, Registrar e Ajustes. O rótulo do grupo fica visualmente recolhido. Seleção usa fundo azul suave, texto azul de foco e peso de label. Manter os destinos e o comportamento nativo de teclado; os snippets do sidecar demonstram somente as regras locais, sem reconstruir o runtime Streamlit.

### Cards / Containers

Bloco de estudo tem superfície branca e raio de superfície. Borda e padding do `st.container(border=True)` permanecem nativos, sem valor inventado aqui. Cabeçalho reúne tema e dose; a dose não encolhe e o cabeçalho pode quebrar em largura estreita. Abaixo vêm caminho, estado/etapa e a ação. Detalhes de revisões ficam recolhidos.

Formulários e expanders recebem o mesmo fundo e raio. Ajustes diários, adiantamento e explicações seguem divulgação progressiva. A redução de esforço percebido e os painéis com ação, das referências Revenue-Centric Design, orientam esta hierarquia sem criar promessas ou urgência.

### Chips e badges

Estados são informativos, não controles. Dominado, Aprendendo e Em alerta usam os pares semânticos do frontmatter. Calendário distingue atrasados, recuperações e pendências previstas por texto e cor. Quantidade de questões usa dose separada do estado; nem dose nem badge devem sugerir que um estudo já foi registrado.

### Métricas, tabela e lista

Resumo de Hoje mostra meta, feitas e para fazer; progresso corresponde a questões registradas. Temas oferece filtros acionáveis e alternância Tabela/Lista. A lista distingue acerto de convicção e mostra “Próxima revisão: Não programada” quando não há data. Não substituir esse vazio por uma data inferida.

### Evidência e limites

Esta captura é estática. O contexto do trabalho informa detector estático com resultado `[]` e AppTest funcional; esta documentação não os executou novamente. Não há screenshots atuais, inspeção visual de viewport ou teste de toque: o bloqueio de navegador anterior não foi contornado. O guia visual legado não representa esta interface. Não há declaração de conformidade WCAG completa. Os exemplos do sidecar isolam regras próprias, não são capturas nem reprodução completa da aparência nativa.

## Do's and Don'ts

### Do:
- **Do** priorizar a ação de estudo e deixar configuração e explicações em detalhes recolhidos.
- **Do** reutilizar os tokens acima e widgets nativos antes de criar uma nova aparência.
- **Do** acompanhar estados com texto e oferecer alternativa Lista para consultar temas.
- **Do** verificar renderização, teclado e toque quando houver ambiente permitido; separar evidência funcional de evidência visual.
- **Do** preservar originais, versões, histórico e preferências ao mudar a apresentação.

### Don't:
- **Don't** adicionar fonte remota, tipografia promocional ou animação decorativa.
- **Don't** inventar progresso, dados pessoais demonstrativos ou urgência artificial.
- **Don't** tratar meta de 90% como probabilidade ou garantia de aprovação, percentual revisado como acerto ou data de PDF como contato.
- **Don't** depender de hover, ocultar ações essenciais no celular ou remover foco visível.
- **Don't** automatizar a plataforma Osler ou aplicações de suspensão/reativação; a interface trabalha com exportações manuais e entradas do usuário.
- **Don't** declarar validação visual, toque ou conformidade completa a partir de CSS, detector estático ou AppTest.
