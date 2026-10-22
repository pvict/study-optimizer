---
name: Osler — estudos locais
description: Interface local de estudo com abas claras, azul Osler e ações diretas.
colors:
  primary: "#2457d6"
  primary-deep: "#1e46ad"
  page: "#f3f4f6"
  surface: "#e8edf5"
  soft: "#dfe7f1"
  field-line: "#7d8796"
  field-bg: "#f7f8fa"
  ink: "#1d1d1f"
  muted: "#5f6368"
  line: "#d9dde3"
  selected: "#eef3ff"
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
  headline-narrow:
    fontSize: "1.65rem"
  sidebar-title:
    fontSize: "1.35rem"
    letterSpacing: "-.02em"
  field-narrow:
    fontSize: "16px"
  progress-total:
    fontSize: "1rem"
  topic-metric:
    fontSize: "1.25rem"
  evolution-metric-narrow:
    fontSize: "1.15rem"
  dose-narrow:
    fontSize: ".85rem"
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
  field:
    backgroundColor: "{colors.field-bg}"
    textColor: "{colors.ink}"
    rounded: "{rounded.control}"
  support:
    backgroundColor: "{colors.soft}"
    rounded: "{rounded.surface}"
    padding: "{spacing.base}"
  summary:
    backgroundColor: "{colors.surface}"
    rounded: "{rounded.control}"
    padding: ".8rem 1rem"
  navigation-selected:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.primary-deep}"
    padding: ".4rem .3rem"
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

A identidade existente combina azul Osler, fundo neutro, superfícies em azul-cinza e apoio cinza contrastante. Abas sem círculos distinguem destinos de campos de formulário. A direção Operate valoriza leitura rápida e ações de estudo evidentes: mostrar o que falta, oferecer o próximo bloco e deixar ajustes e explicações em segundo plano. O uso confirmado abrange computador e celular. Evolução estende a identidade com uma jornada elegante de marcos e conquistas discretas; estratégia em [Evolução](docs/design/evolucao.md).

Este documento registra o código atual, sem criar uma identidade nova. A referência normativa é `osler/study.css`, aplicada por `study_style.py`, com componentes em `study_components.py`, `study_day_ui.py`, `study_tables_ui.py`, `study_calendar_ui.py` e `adaptive_ui.py`, mais o tema de `.streamlit/config.toml`. Os tokens acima registram valores reutilizados; estilos e comportamento nativos dependem do Streamlit 1.66. A cascata efetiva do navegador não foi inspecionada. Este registro atualiza o sistema existente para o redesign de apresentação autorizado, preservando seus compromissos confirmados.

**Key Characteristics:**
- Português simples, ações específicas e detalhes recolhidos.
- Abas claras sem círculos, campos delimitados e hierarquia entre trabalho e apoio.
- Azul como acento; estados sempre acompanhados por texto.
- Tipografia nativa, números alinháveis e conteúdo com quebra de linha.
- Mesma tarefa disponível em computador e celular, sem depender de hover.

## Colors

Um azul nítido organiza a navegação e as ações sobre uma base clara e fria. Os nomes abaixo apontam para os tokens do frontmatter, sem criar outra paleta.

### Primary
- **Azul de ação** (`primary`): acento do tema e cursor de edição.
- **Azul profundo** (`primary-deep`): contorno de foco, texto da navegação selecionada, dose e estado Aprendendo.
- **Azul suave de seleção** (`selected`): hover de navegação, dose, Aprendendo e recuperações no calendário.
- **Azul de seleção de texto** (`selection`): seleção de texto com tinta principal.

### Neutral
- **Fundo neutro** (`page`) e **superfície em azul-cinza** (`surface`): página e agrupamentos de trabalho.
- **Tinta** (`ink`) e **texto de apoio** (`muted`): hierarquia entre informação principal e contexto.
- **Apoio cinza** (`soft`): lateral e painel de apoio do estudo.
- **Linha clara** (`line`): separadores e contornos de agrupamento.
- **Limite de campo** (`field-line`) e **interior de campo** (`field-bg`): contorno e fundo dos controles antes do foco.

Os pares `success` / `success-bg`, `warning` / `warning-bg` e `danger` / `danger-bg` são semânticos, não acentos decorativos: Dominado, Em alerta ou pendências previstas, e atrasos. Mensagens nativas de sucesso/erro mantêm o tratamento do Streamlit; estes pares não comprovam as cores computadas desses alertas.

Correspondência com o CSS: `primary` → `--study-primary`, `primary-deep` → `--study-primary-deep`, `page` → `--study-bg`, `surface` → `--study-surface`, `soft` → `--study-soft`, `ink` → `--study-ink`, `muted` → `--study-muted`, `line` → `--study-line`, `field-line` → `--study-field-line`, `selected` → `--study-selected`; os pares semânticos seguem `--study-<nome>`. `field-bg` e `selection` registram os literais reutilizados nos seletores, sem declarar propriedades CSS novas.

Cálculo estático dos pares atuais: tinta/superfície (14,32:1), texto de apoio/superfície (5,15:1), texto de apoio/painel (4,85:1), borda de campo/superfície (3,09:1), azul profundo/superfície (7,05:1). Branco/azul de ação continua (6,16:1). Os pares textuais medidos superam (4,5:1); o limite de campo supera (3:1). Isso não verifica cascata, estados nativos ou conformidade completa.

As rampas OKLCH do sidecar são auxiliares de visualização calculados a partir das cores existentes; não são tokens adicionais nem cores usadas pela aplicação. O frontmatter continua normativo.

**The Estado Legível Rule.** Cor reforça um rótulo explícito; nunca substitui o estado, a data ou a quantidade.

## Typography

O tema pede `sans-serif`, sem fonte remota ou família de display própria. A família efetivamente resolvida e os tamanhos não sobrescritos permanecem a cargo do Streamlit e do navegador.

- `headline`, `title` e `title-small`: título da tela, seções e blocos; não usar caixa alta promocional.
- `body`: entrelinha comum de parágrafos e listas; não estabelece um tamanho global de corpo.
- `caption`: caminhos de temas e explicações secundárias, em texto de apoio.
- `label`, `chip` e `dose`: navegação, estados e quantidade do bloco.
- `metric`: resumo numérico. Métricas, doses e resumo de lista usam algarismos tabulares.

A lateral usa `sidebar-title`; o resumo de Hoje usa `progress-total`, com apoio na escala de label; Temas usa `topic-metric`. Em viewport até (760px), entram `headline-narrow`, `field-narrow` e `dose-narrow`; os rótulos compactos usam o tamanho de chip. Evolução usa `evolution-metric-narrow` em viewport até (760px) e container até (700px). Palavras longas podem quebrar em títulos, parágrafos e rótulos. A antiga regra de métrica de resumo (1.55rem) permanece no CSS, mas o resumo atual não emite esse componente: não faz parte da escala normativa para novas telas.

## Layout

O conteúdo tem largura máxima de (1240px), com margens internas (4rem 2rem 4rem). Até (1000px), o espaço horizontal passa a (1.25rem). Até (760px), usa (4rem max(1rem, env(safe-area-inset-left)) 3rem). O padding superior comum de (4rem) reserva espaço para o cabeçalho fixo; é implementação estática, sem confirmação de que resolve a sobreposição em renderização. Não presumir comportamento de safe area além dessa regra existente.

Na tela Hoje, trabalho e apoio usam proporção (1.85:1); em largura estreita, colunas passam a uma pilha. O resumo de Hoje usa uma faixa flexível com total registrado, restantes e barra; filtros de estado em Temas usam quatro colunas, passando a duas na faixa estreita. A navegação tem seis destinos, reflui para três colunas e, com container até (350px), para duas; um último destino ocupa a linha apenas quando a quantidade é ímpar. O container `study` também ativa a composição estreita até (700px), independentemente da largura da janela.

Calendário oferece Agenda, Semana e Mês; Agenda é a primeira opção. Agenda e blocos do dia selecionado vêm antes da gestão de revisões. A grade semanal/mensal passa a sete colunas explícitas até (1000px) e a duas na faixa estreita. Tabelas têm largura contida; Temas oferece Lista paginada em até 12 itens, com ações por tema, como alternativa à rolagem horizontal. Registrar e Meta e rotina têm largura máxima de (720px); seus formulários recebem padding de (1.25rem), reduzido a (.8rem) até (760px). Busca e filtro principal em Temas ficam na superfície de filtros; os demais seguem em Mais filtros e definições. Biblioteca é a primeira aba de arquivos e a seleção técnica fica recolhida. Não esconder funções essenciais por largura.

Os breakpoints são regras implementadas, não prova de renderização em dispositivos. A matriz de referência do trabalho é (320, 390, 768, 1024 e 1440px).

## Elevation & Depth

O CSS próprio usa superfícies claras, separadores e fundos semânticos para agrupar informação. Não define sombras. Bordas e eventuais sombras dos containers e controles nativos pertencem ao Streamlit; não foram extraídas de estilos computados.

**The Agrupamento Útil Rule.** Um container deve reunir uma tarefa ou seu contexto; não adicionar camadas decorativas para cada linha de informação.

## Shapes

Os três raios do frontmatter distinguem rótulos compactos, controles e superfícies. Formulários, expanders e blocos recebem a curva de superfície; botões e opções de navegação, a curva de controle; doses e badges, a curva de rótulo. Não substituir esse vocabulário por pílulas ou cartões com cantos excessivos.

Foco próprio: contorno sólido (3px) em azul de foco, afastado (3px), para botões, links, inputs, textarea e summary; rótulos também recebem contorno quando contêm input em foco visível. Não remover o foco para obter uma superfície mais limpa.

## Components

Após salvar um resultado, a confirmação oferece “Voltar ao plano” e “Registrar outro estudo”; o formulário enviado deixa de ser mostrado até iniciar um novo registro. Erros de entrada conservam os campos para correção. Esse estado pertence à apresentação, sem mudar as regras de gravação.

### Buttons

Controles nativos com ação concreta. CSS próprio define altura mínima de (44px), quebra de texto, raio de controle e foco visível. As cores, bordas, padding e estados hover/active/disabled de variantes nativas não foram inspecionados; `primaryColor` é configuração de tema, não uma extração da aparência computada de cada botão.

O primeiro bloco de Hoje usa `type='primary'`; demais blocos usam `secondary`. O dia selecionado no calendário é primário. Salvar resultado e salvar planejamento são ações primárias explícitas. Transições próprias de fundo e borda duram (150ms ease-out); com movimento reduzido são removidas. Não acrescentar efeitos de deslocamento.

### Inputs / Fields

Usar widgets nativos e rótulos visíveis. Seletores próprios definem fundo `field-bg`, borda sólida de (1px) em `field-line`, raio de controle e altura mínima de (44px) nos campos numéricos, texto, data, textarea e seleção. Cursor azul e placeholder em texto de apoio completam o tratamento. Wrappers em foco recebem contorno de (2px), afastado (2px), em `primary-deep`; o foco visível de elementos conserva a regra geral. Radio, checkbox e summary também têm altura mínima própria de (44px). Estes são seletores e valores de CSS; não confirmam alcance de todos os wrappers, cascata ou alvos medidos em tela.

### Navigation

Grupo radio nativo com Hoje, Calendário, Evolução, Temas, Registrar e Ajustes. O rótulo do grupo fica visualmente recolhido. Os círculos visuais são ocultados nos grupos com keys explícitas; o widget continua sendo radio, sem inventar semântica ARIA de tab. Seleção usa superfície em azul-cinza, texto azul profundo e traço inferior azul de (3px), com cantos retos; hover usa seleção suave. Manter keys, inputs e comportamento nativo de teclado. A lateral mantém três destinos superiores, com seleção em azul-cinza sobre apoio mais escuro; calendário, períodos, visualizações e ajustes recebem tratamento local de abas. Abas nativas de biblioteca mantêm seu próprio papel de tab, altura mínima de (44px) e rolagem horizontal local. Os snippets do sidecar demonstram regras locais, sem reconstruir o runtime Streamlit.

### Cards / Containers

Bloco de estudo tem superfície em azul-cinza e raio de superfície. Borda e padding do `st.container(border=True)` permanecem nativos, sem valor inventado aqui. O primeiro bloco recebe borda azul; o apoio usa fundo `soft` e padding de (1rem), reduzido a (.75rem) em viewport estreita. Blocos recebem padding vertical de (.1rem) e gap interno de (.4rem). Cabeçalho reúne tema e dose; a dose não encolhe e o cabeçalho pode quebrar em largura estreita. Abaixo vêm caminho, estado/etapa e a ação. Detalhes de revisões ficam recolhidos.

Formulários e expanders recebem o mesmo fundo e raio. Meta e rotina organiza Rotina diária e Objetivos e datas. Ajustes diários, adiantamento e explicações seguem divulgação progressiva. A redução de esforço percebido e os painéis com ação, das referências Revenue-Centric Design, orientam esta hierarquia sem criar promessas ou urgência.

### Chips e badges

Estados são informativos, não controles. Dominado, Aprendendo e Em alerta usam os pares semânticos do frontmatter. Calendário distingue atrasados, recuperações e pendências previstas por texto e cor. Quantidade de questões usa dose separada do estado; nem dose nem badge devem sugerir que um estudo já foi registrado.

### Métricas, tabela e lista

Resumo de Hoje mostra questões registradas sobre a meta e restantes em faixa compacta; progresso corresponde a questões registradas, sem três KPIs grandes. Temas oferece filtros acionáveis e alternância Tabela/Lista. A lista distingue acerto de convicção e mostra “Próxima revisão: Não programada” quando não há data. Não substituir esse vazio por uma data inferida.

### Evidência e limites

Esta captura é estática. O detector estático anterior à atualização documental sinalizou o traço inferior da aba como borda de cartão arredondado, embora o seletor fixe raio zero; esse diagnóstico não foi convertido em regra do sistema. Seus advisories de tamanho foram conciliados com as funções tipográficas observadas; a regra sem uso do resumo permanece fora dos tokens.

A execução principal informou baseline de (416 testes) e suíte específica de (61 testes) aprovados; esta documentação não os executou novamente. Os contrastes acima vieram do cálculo estático em `tmp/redesign-contrast.json` na cópia original do projeto. Não há screenshots atuais, inspeção visual de viewport ou teste de toque: o bloqueio de navegador anterior não foi contornado. O guia visual legado não representa esta interface. Não há declaração de conformidade WCAG completa. Os exemplos do sidecar isolam regras próprias, não são capturas nem reprodução completa da aparência nativa.

## Do's and Don'ts

### Do:
- **Do** priorizar a ação de estudo e deixar configuração e explicações em detalhes recolhidos.
- **Do** reutilizar os tokens acima e widgets nativos antes de criar uma nova aparência.
- **Do** apresentar destinos em abas sem círculos e manter a semântica radio dos widgets existentes.
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

### Correção dos filtros após evidência do usuário

A captura enviada após o redesign mostrou os quatro filtros de estado truncados. A grade CSS recebia colunas nativas ainda com largura proporcional: o reset local para100% remove essa segunda redução. Os filtros usam faixas sem caixa, com indicador inferior e texto completo; a busca não tem painel de fundo. Superfícies usam azul-cinza em vez de branco. Não houve nova captura do navegador; a correção foi examinada no código e funcionalmente.
