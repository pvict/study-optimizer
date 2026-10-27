# PROMPT MESTRE — Redesign Bento do Osler (para Codex/ChatGPT)

Cole este arquivo inteiro no início de cada sessão e, no final, diga: **"Execute somente a Fase N"**. Não peça duas fases na mesma sessão.

---

## 0. Como você deve trabalhar (obrigatório)

Você tem dificuldade conhecida em produzir design bonito a partir de adjetivos. Este documento troca adjetivos por **valores exatos, código-base, dados de origem e um ciclo de verificação visual**. Siga-o à risca. Onde algo estiver ambíguo, escolha a opção mais simples que respeite as regras da seção 2 e anote a decisão.

### Skills a usar (invoque-as explicitamente, na ordem)

1. **superpowers**
   - `using-superpowers`: no início, para carregar o fluxo.
   - `brainstorming`: **apenas** para confirmar o escopo da fase (máx. 5 minutos, sem perguntar ao usuário nada que este documento já responda).
   - `writing-plans`: produza o plano da fase em `docs/plans/AAAA-MM-DD-bento-faseN.md` **antes** de editar código.
   - `test-driven-development`: testes antes do código para toda lógica nova (helpers, mapeamentos, estados).
   - `systematic-debugging`: para qualquer falha de teste ou de renderização.
   - `verification-before-completion`: **antes de dizer "pronto"**, rode os comandos e cole as saídas.
   - `requesting-code-review`: ao final da fase, faça uma revisão do próprio diff contra a seção 11.
2. **Impeccable** (o projeto já usa as referências Operate, Distill, Adapt e Craft Floor; ver `.impeccable/design.json`): use-a para a direção de design e, **depois** de implementar cada tela, para a crítica e o polimento (critique, polish, audit e, se disponíveis, os comandos de cor e de adaptação a telas pequenas). Aplique as correções que ela apontar, dentro destas regras.
3. **Revenue-Centric Design** (exigida pelo `AGENTS.md`): `C:/Users/Paulo/.codex/skills/revenue-centric-design/SKILL.md`. Hierarquia de atenção e esforço percebido. Se qualquer skill sugerir algo que viole a seção 2, **a seção 2 vence**.

Se uma skill não estiver disponível, diga isso no início e prossiga sem ela, sem inventar o que ela faria.

### Antes da Fase 1: inventário

Eu **não** vi o estado atual do repositório; ele evoluiu desde a v0.14. Portanto, antes de tudo:
- Leia `AGENTS.md`, `README.md`, `DESIGN.md`, `.impeccable/design.json`, `.streamlit/config.toml`, `osler/study.css`, `osler/study_style.py`, `osler/ui.py`, `osler/adaptive_ui.py` e a pasta `tests/`.
- Liste as telas e módulos **reais** (a lista da seção 8 é a esperada; confirme no código e corrija nomes que divirjam).
- Rode `python -m pytest -q` e registre o resultado inicial.
- Confirme a versão do Streamlit instalada e que APIs usadas aqui existem nela: `st.container(key=)`, `st.html`, `st.pills`, `st.segmented_control`, `st.fragment(run_every=)`, `st.toast`, `st.dataframe(column_config=)`, `st.button(icon=)` (ícones `:material/...:`), `st.date_input(format=)`. **Não use uma API sem confirmá-la.**

### Material de referência (peça ao usuário para colocar na raiz do projeto)

```
evidencias/previas/previa_01_meu_dia.png
evidencias/previas/previa_02_temas_desempenho.png
evidencias/previas/previa_03_simulados_calendario.png
docs/design/DIRETRIZES-REDESIGN-BENTO-CLAUDE.md
```
As prévias são **referência de composição e hierarquia, não de implementação**. Elas têm erros que **não** devem ser copiados (seção 3).

---

## 1. Objetivo

Transformar a interface em uma experiência **acolhedora, organizada em Bento Grid, com personalidade e cor por grande área**, tipografia no estilo SF Pro, usando só widgets e APIs públicas do Streamlit. Nenhuma regra de estudo, cálculo, gravação ou importação muda.

---

## 2. Regras invioláveis

**Funcionais**
1. Não alterar cálculos, prioridades, revisões, convicção, importação nem a gravação de dados. Mudança só na camada de apresentação (`*_ui.py`, CSS, helpers visuais).
2. **Dado desconhecido nunca vira zero.** Ausência = "—" com texto curto explicando.
3. **Nada inventado.** Todo número, rótulo e frase na tela precisa ter uma fonte no código (tabela da seção 8). Não crie conteúdo pedagógico, "conceitos-chave", "dificuldade estimada" nem previsões.
4. **Nunca exibir "probabilidade de aprovação", "estimativa de corte sobe de X para Y" ou qualquer projeção de nota.** A meta de 90% orienta, não prevê. Percentual revisado de flashcards não é acerto. Data de PDF não é contato.
5. Não misturar denominadores: novas, repetidas, mistas, simulados e PDFs continuam separados. Todo percentual mostra **n** (tamanho da amostra) por perto.
6. Uso 100% local. Não acessar nem automatizar a plataforma Osler. Suspensão/reativação de cartões continuam manuais.
7. Preservar `key=` dos widgets, `session_state`, rerun, foco e acessibilidade.

**Dados**
8. **Nunca teste no banco real.** Crie `scripts/seed_demo_data.py` que gera dados sintéticos **somente** em uma pasta temporária passada por argumento e **recusa** rodar em `data/` ou em qualquer pasta que contenha `osler.sqlite3` do usuário. Use essa pasta com `OSLER_DATA_DIR` e **outra porta** (por exemplo 8602) para ver as telas.

**Técnicas**
9. Streamlit apenas; sem trocar de framework, sem JavaScript próprio, sem dependências de rede em tempo de execução, sem CDN.
10. CSS só por **`.st-key-<key>`** (via `key=` do container/widget) e `data-testid` já presentes. Proibido seletores de classes geradas (`css-xxxx`, `emotion-*`).
11. Todo texto de usuário/dados exibido via `st.html` passa por `html.escape`. CSV continua com `_safe_cell`.
12. **Contrato de testes**: antes de renomear qualquer `key=` ou rótulo, procure nos testes (`rg`). Mudanças de teste são permitidas **somente** quando decorrem da navegação nova (seção 9) e devem ser listadas.
13. Acessibilidade: contraste WCAG AA medido; foco visível; alvos ≥ 44 px; `prefers-reduced-motion`; informação nunca só por cor.
14. **Desempenho:** nunca renderize centenas de cards. Listas de temas são paginadas (12 por página, como hoje). O app tem cerca de 1.480 temas.

**Idioma/tom**: português simples e adulto. O usuário é médico. Sem infantilização, sem culpa, sem urgência artificial, sem confete.

---

## 3. Decisões de design aprovadas (diferenças em relação às prévias)

O usuário **gostou das prévias, exceto dos fundos pretos** nos cards da página inicial. Além disso, a revisão encontrou problemas que você deve corrigir:

| # | Na prévia | Decisão |
|---|---|---|
| 1 | Cards pretos no "Meu dia", com texto escuro ilegível | **Nenhum fundo preto.** O card principal (hero) usa a **cor da grande área** do próximo bloco em tom claro (ver seção 4), texto `--o-ink`, botão sólido na cor forte da área. Cards laterais brancos. |
| 2 | Estado (Dominado/Aprendendo/Em alerta) usa verde/âmbar/vermelho, que **colidem** com as cores das áreas (esmeralda = Pediatria, âmbar = Preventiva, coral = Cirurgia) | **Cor é só da área.** Estado usa **ícone + texto** em chip neutro (seção 4.4). "Em alerta" ganha borda mais forte, não vermelho. |
| 3 | Botão "Revisar" vermelho cheio | Anti-burnout: botão **secundário** com ícone. Nada de vermelho de alarme em lugar nenhum, exceto erro técnico real do sistema. |
| 4 | Emojis (fogo, bateria, aceno, folha, vaso) | **Sem emoji.** Ícones Material via `:material/nome:` (API pública). |
| 5 | "🔥 4 dias seguidos" | "Ritmo da semana": 7 pontos (feito, parcial, descanso, futuro). **Dia de descanso planejado não quebra o ritmo.** Texto "4 de 7 dias com estudo", sem fogo, sem recorde. Só dados reais. |
| 6 | "Bateria do dia 65%" (bateria cheia = energia sobrando, semântica invertida; 40/60 = 67%, não 65%) | **Anel "Hoje"** com `feitas / meta` e "restam N". Percentual calculado, nunca digitado. |
| 7 | "Ver Conceitos-Chave", "Foco: Cicatrização por 2ª intenção…", "Dificuldade estimada" | **Removidos.** O app não tem esse conteúdo. O hero mostra tema, caminho, quantidade, etapa, estado, **motivo** (`item['reason']`), erros abertos (se houver) e "≈ N min (estimativa)" só se houver mediana de minutos por questão. Ação secundária: "Ver próximas revisões" (já existe). |
| 8 | "Iniciar & Registrar Bloco" | O app não "inicia" nada. Rótulo mantido: **"Registrar este bloco"** (contrato de teste). |
| 9 | "Dr. Paulo · Foco R1 2026/2027" fixo | O nome vem de um campo opcional em Ajustes ("Como quer ser chamado?"). Sem nome: "Olá". Sem "Dr.", sem ano fixo. O rodapé da lateral mostra só o que existir. |
| 10 | "Cirurgia Geral" | Os nomes reais das áreas nos relatórios são: **Clínica Médica, Clínica Cirúrgica, Pediatria, Ginecologia e Obstetrícia, Preventiva & Social.** Use-os. Mapeamento na seção 6. |
| 11 | "Insight inteligente… estimativa de corte sobe de 78% para 84%" | **Proibido (regra 4).** Substituir por fato calculável, por exemplo: "N temas em alerta têm incidência alta na tabela que você trouxe" (só se houver tabela de incidência). |
| 12 | "Corte oficial", "Corte Histórico (USP)" | O corte é **informado pelo usuário, com fonte e confiança** (módulo "Minhas provas"). Rótulo: "Corte informado por você · fonte: …". Sem corte cadastrado: "Cadastre o corte em Minhas provas." |
| 13 | Barras por área com 20 questões cada, comparando 90% × 75% como se fosse diferença firme | Com n = 20 a margem é de ± ~18 p.p. Mostre **n** e a **faixa (Wilson 95%)**. Cor da barra = área; o status vem do texto. Aviso curto: "Um simulado não é a prova real." |
| 14 | Texto da "Pausa" estourando o card | Texto com quebra de linha; card só aparece **após ≥ 1 bloco registrado hoje**, é dispensável e nunca bloqueia o fluxo. Frases fixas e neutras, sem alegações de saúde. |
| 15 | "Simulados & Calendário" numa tela só; menu lateral diferente em cada prévia | **Telas separadas** (como no código) e **um único menu** (seção 9). O calendário mostra o dia de simulado como um chip. |
| 16 | Tipografia serifada nas prévias (provável fallback de fonte) | Tipografia sans estilo SF Pro (seção 5). |
| 17 | Radar das 5 áreas (sugerido nas diretrizes) | **Não usar radar.** Com amostras pequenas ele passa falsa precisão. Usar barras horizontais com faixa e n. |
| 18 | Confete/comemoração ao salvar | **Celebração discreta**: `st.toast` com ícone de check e uma linha: "Salvo. Hoje: 40 de 60." |

---

## 4. Tokens (CSS) — valores exatos

Crie `osler/bento.css` (carregado por `study_style.py` junto de `study.css`; `study.css` continua existindo e é **reduzido** apenas onde houver conflito). Todos os pares de cor abaixo foram **medidos** (WCAG).

### 4.1 Base

```css
:root{
  --o-font:"SF Pro Display","SF Pro Text",-apple-system,BlinkMacSystemFont,"Inter","Segoe UI",system-ui,sans-serif;
  --o-bg:#F6F7FB;            /* fundo da página */
  --o-card:#FFFFFF;
  --o-line:rgba(17,24,39,.08);
  --o-ink:#111827;           /* 17,1:1 sobre o fundo */
  --o-ink-2:#4B5563;         /* 7,6:1 sobre branco */
  --o-ink-3:#6B7280;         /* 4,8:1 sobre branco; só em branco/fundo, nunca sobre tinta colorida */
  --o-primary:#4F46E5;       /* texto branco sobre ele: 6,3:1 */
  --o-primary-strong:#4338CA;/* 7,9:1 */
  --o-primary-tint:#EEF2FF;
  --o-radius:24px; --o-radius-md:16px; --o-radius-sm:12px; --o-pill:999px;
  --o-shadow:0 1px 2px rgba(17,24,39,.04),0 6px 20px -6px rgba(17,24,39,.06);
  --o-shadow-hover:0 2px 4px rgba(17,24,39,.05),0 14px 32px -8px rgba(17,24,39,.12);
  --o-gap:16px; --o-pad:24px;
  --o-sand:#F5F1EA; --o-sand-ink:#5B4A32;   /* pausa e descanso */
}
```

### 4.2 Cores por grande área (cada uma com 4 papéis)

`fill` = decorativo (anel, barra, ponto; **nunca texto**). `tint` = fundo claro. `ink` = texto/ícone sobre `tint` e sobre branco. `solid` = fundo de botão com texto branco.

| Área (nome real) | slug | fill | tint | ink (sobre tint) | solid (texto branco) |
|---|---|---|---|---|---|
| Clínica Médica | `clinica` | #4F46E5 | #EEF2FF | #3730A3 (8,9:1) | #4338CA (7,9:1) |
| Clínica Cirúrgica | `cirurgia` | #FF6B6B | #FFF1F0 | #B42318 (6,0:1) | #B42318 (6,6:1) |
| Pediatria | `pediatria` | #10B981 | #ECFDF5 | #047857 (5,2:1) | #047857 (5,5:1) |
| Ginecologia e Obstetrícia | `go` | #8B5CF6 | #F5F3FF | #6D28D9 (6,5:1) | #6D28D9 (7,1:1) |
| Preventiva & Social | `preventiva` | #F59E0B | #FFFBEB | #92400E (6,8:1) | #92400E (7,1:1) |
| (não mapeada) | `neutral` | #6B7280 | #F3F4F6 | #374151 | #374151 |

Defina como variáveis: `--a-<slug>-fill`, `--a-<slug>-tint`, `--a-<slug>-ink`, `--a-<slug>-solid`. **Não use** `#FF6B6B` ou `#F59E0B` como cor de texto (2,8:1 e 2,2:1: reprovam) nem `#059669` como fundo de botão (3,8:1).

### 4.3 Tipografia

| Papel | Tamanho/linha | Peso | Extras |
|---|---|---|---|
| Display (título da tela) | 32/38 (24/30 em ≤ 760 px) | 700 | `letter-spacing:-.022em` |
| Título de card (H3) | 20/26 | 650 | `letter-spacing:-.012em` |
| Corpo | 15/22 | 400 | |
| Apoio | 13/18 | 400 | cor `--o-ink-2` |
| Eyebrow | 11/16 | 700 | maiúsculas, `letter-spacing:.08em`, cor `--a-*-ink` |
| Número grande (métrica) | 40/44 | 700 | `font-variant-numeric:tabular-nums` |

Máximo de **3 tamanhos por card**. Campos de formulário a 16 px em ≤ 760 px. Números sempre tabulares.

### 4.4 Chips de estado (sem cor de área)

Todos: `background:#F3F4F6; color:var(--o-ink); border:1px solid transparent; border-radius:var(--o-pill); padding:4px 10px; font:600 12px/16px var(--o-font)` com ícone Material de 16 px à esquerda.

| Estado | Ícone | Diferença extra |
|---|---|---|
| Dominado | `check_circle` | — |
| Aprendendo | `trending_up` | — |
| Em alerta | `priority_high` | `border-color:rgba(17,24,39,.45)`; fundo `#FFFFFF` |
| Sem estudo | `radio_button_unchecked` | — |

### 4.5 Estrutura de card (Bento) — receita única

```css
[class*="st-key-bento-"]{
  background:var(--o-card); border:1px solid var(--o-line);
  border-radius:var(--o-radius); box-shadow:var(--o-shadow);
  padding:var(--o-pad);
  transition:box-shadow 160ms ease-out, transform 160ms ease-out;
}
[class*="st-key-bento-"].o-interactive:hover{box-shadow:var(--o-shadow-hover);transform:translateY(-1px)}
@supports (corner-shape: squircle){
  [class*="st-key-bento-"]{corner-shape:squircle;border-radius:34px}   /* squircle exibe raio menor; verifique no navegador */
}
@media (prefers-reduced-motion:reduce){[class*="st-key-bento-"]{transition:none}[class*="st-key-bento-"].o-interactive:hover{transform:none}}
```
`corner-shape` é recurso novo: trate como **melhoria progressiva** e confirme o resultado visual; sem suporte, vale `border-radius:24px`.

Variantes por área (o hero e o destaque do card usam a `tint` da área):
```css
.st-key-bento-hero-cirurgia{background:var(--a-cirurgia-tint);border-color:color-mix(in srgb,var(--a-cirurgia-fill) 30%,transparent)}
/* repetir para clinica, pediatria, go, preventiva e neutral (gere por laço no Python, não à mão) */
```

### 4.6 Botões (use `st.button`, nunca `<button>` em HTML)

- **Primário** (`type="primary"`): fundo `--o-primary-strong`, texto branco, raio 14 px, altura 44 px, peso 600. **Um por card/contexto.**
- **Secundário**: fundo branco, borda `--o-line` forte (`rgba(17,24,39,.16)`), texto `--o-ink`.
- No hero de uma área, o botão primário usa `--a-<slug>-solid`.
- Foco: `outline:3px solid var(--o-primary-strong); outline-offset:3px`.

### 4.7 Grade e responsividade

- Largura máxima do conteúdo 1240 px; `gap` 16 px; padding externo 32 px (≥ 1100), 20 px (≤ 760).
- Desktop: 12 colunas lógicas; use `st.columns([2,1], gap="medium")` (hero 2/3 + coluna lateral 1/3) e `st.columns(2)`/`3`.
- ≤ 900 px: tudo em 1 coluna, exceto o "ritmo da semana" e chips, que continuam em linha.
- Sem rolagem horizontal da página; tabelas largas em contêiner próprio.

---

## 5. Tipografia SF Pro — o que é possível

- O usuário está em **Windows**. `-apple-system`/`BlinkMacSystemFont` só resolvem para SF Pro em **macOS/iOS**; no Windows o navegador cairá no próximo item da pilha.
- **Não inclua arquivos de SF Pro no repositório nem os sirva ao navegador.** A licença da Apple restringe seu uso e redistribuição; verifique antes de qualquer decisão diferente.
- Solução: a pilha `--o-font` da seção 4.1, com **Inter** (licença OFL) como substituta visualmente próxima, **empacotada localmente**:
  1. baixar `InterVariable.woff2` manualmente (sem rede em tempo de execução) para `static/fonts/` e registrar a licença em `docs/third-party/Inter-OFL.txt`;
  2. em `.streamlit/config.toml`: `[server] enableStaticServing = true`;
  3. `@font-face` apontando para `/app/static/fonts/InterVariable.woff2` (`font-display:swap`);
  4. confirmar no navegador que a fonte carrega e que há fallback correto.
- Se o download não for possível no ambiente, **não improvise**: mantenha `"Segoe UI", system-ui` e diga na entrega que o Inter não foi empacotado.
- Atualizar `DESIGN.md` (hoje diz "sem fonte remota": continua verdadeiro, pois a fonte é local).

---

## 6. Biblioteca de componentes — `osler/bento.py` (escreva primeiro, com testes)

```python
"""Componentes visuais puros. Nenhuma regra de estudo aqui."""
from html import escape
import math
from .models import normalize_path

AREA_SLUGS = {
    'clinica medica': 'clinica',
    'clinica cirurgica': 'cirurgia',
    'pediatria': 'pediatria',
    'ginecologia e obstetricia': 'go',
    'preventiva & social': 'preventiva',
}
AREA_LABELS = {'clinica': 'Clínica Médica', 'cirurgia': 'Clínica Cirúrgica', 'pediatria': 'Pediatria',
               'go': 'Ginecologia e Obstetrícia', 'preventiva': 'Preventiva & Social', 'neutral': ''}
STATE_CHIPS = {  # (rótulo, ícone material)
    'dominado': ('Dominado', 'check_circle'), 'aprendendo': ('Aprendendo', 'trending_up'),
    'alerta': ('Em alerta', 'priority_high'), 'sem_registro': ('Sem estudo', 'radio_button_unchecked')}


def area_slug(path):
    """Mapeia o primeiro nível do caminho para um slug; desconhecido vira 'neutral'."""
    if not path: return 'neutral'
    return AREA_SLUGS.get(normalize_path([path[0]])[0], 'neutral')


def eyebrow(text, slug='neutral'):
    return f'<span class="o-eyebrow o-eyebrow--{slug}">{escape(text)}</span>'


def chip(text, state=None):
    label, icon = STATE_CHIPS.get(state, (text, None))
    glyph = f'<span class="o-chip-icon material-symbols-rounded" aria-hidden="true">{icon}</span>' if icon else ''
    return f'<span class="o-chip o-chip--{escape(state or "plain")}">{glyph}{escape(label)}</span>'


def pct(done, total):
    """None quando não há denominador; nunca 0 inventado."""
    if not total or done is None: return None
    return max(0.0, min(1.0, done / total))


def ring(done, total, size=96):
    p = pct(done, total)
    r = 42; c = 2 * math.pi * r
    arc = '' if p is None else f'<circle cx="50" cy="50" r="{r}" fill="none" stroke="var(--o-primary)" stroke-width="9" stroke-linecap="round" stroke-dasharray="{p*c:.1f} {c:.1f}" transform="rotate(-90 50 50)"/>'
    label = 'Sem meta definida' if p is None else f'{done} de {total} questões'
    return (f'<svg class="o-ring" width="{size}" height="{size}" viewBox="0 0 100 100" role="img" aria-label="{escape(label)}">'
            f'<circle cx="50" cy="50" r="{r}" fill="none" stroke="#E5E7EB" stroke-width="9"/>{arc}</svg>')


def bar(value, slug='neutral', target=None, label=''):
    """Barra de 0 a 1; `target` desenha um traço (ex.: 0.90). value None => trilha vazia."""
    width = '0%' if value is None else f'{max(0, min(1, value))*100:.1f}%'
    tick = '' if target is None else f'<span class="o-bar-tick" style="left:{target*100:.0f}%"></span>'
    return (f'<div class="o-bar" role="img" aria-label="{escape(label)}"><span class="o-bar-fill o-bar-fill--{slug}" '
            f'style="width:{width}"></span>{tick}</div>')
```

Regras:
- Todo valor numérico passa por validação (`None` ≠ 0). Teste unitário para: `area_slug` com acento/caixa/área desconhecida, `ring(None, 0)`, `ring(40, 60)`, `bar(None)`, escape de `<script>` em `eyebrow/chip`, `pct` fora de [0,1].
- `st.html` aceita só HTML estático; **botões e campos continuam sendo widgets nativos** dentro do mesmo `st.container(key=...)`.
- Ícones: nos chips use o mesmo conjunto Material (`:material/...:` nos widgets; no HTML, glifos Material Symbols **só se a fonte for servida localmente**; senão use `st.markdown(":material/nome:")` em elementos separados ou omita o ícone e mantenha o texto). Não carregue fonte de ícones por CDN.
- Padrão de card:

```python
with st.container(key=f"bento-hero-{slug}"):
    st.html(eyebrow(f"{AREA_LABELS[slug]} · {n} questões", slug))
    st.html(f'<h3 class="o-title">{escape(item["path"][-1])}</h3>')
    st.caption(" › ".join(item["path"][:-1]))
    st.button("Registrar este bloco", key=f"study_{item['topic_id']}", type="primary",
              on_click=go_record, args=(item["topic_id"], item["questions"], mode), icon=":material/edit_note:")
```

---

## 7. Dados de teste visuais — `scripts/seed_demo_data.py`

Gera, **somente em pasta temporária**: 2 relatórios sintéticos (use o gerador de `tests/conftest.py::sample_pdf` como base e amplie para 5 áreas e ~40 temas), 14 dias de sessões variadas (acertos de 55% a 95%, convicção parcial, um dia de descanso, um dia parcial), 3 erros abertos, 1 prova-alvo com corte informado, 1 simulado com acertos por área. Recusa rodar se o destino for `data/` ou contiver `osler.sqlite3` pré-existente. Isto serve para **ver e avaliar o design**; não é conteúdo do app.

---

## 8. Especificação por tela (com fonte de cada dado)

Confirme os nomes de arquivo/função no repositório atual. Onde a coluna "Fonte" disser "novo", o dado precisa ser **derivado** de algo existente, sem mudar regra.

### 8.1 Meu dia (`study_day_ui.py`)

Layout desktop (colunas de proporção entre parênteses):
```
[Cabeçalho: saudação + subtítulo ........................ chip de data]
[HERO (2) ............................ ][ Anel "Hoje" (1) ]
[                                       ][ Ritmo da semana (1) ]
[ Lista "Para fazer / Feito hoje" (2) ..][ Pausa (1) ]
[ Faixa "Sua semana" — 4 métricas ......................... ]
```

| Elemento | Conteúdo | Fonte |
|---|---|---|
| Saudação | "Bom dia/Boa tarde/Boa noite" por hora local; + nome se configurado | hora local; Ajustes (novo campo opcional) |
| Subtítulo | Texto fixo: "Um bloco de cada vez." | constante |
| Chip de data | "Sexta, 23 de outubro" | `today_local()` |
| Hero: eyebrow | `AREA · N questões` | `item['path'][0]`, `item['questions']` |
| Hero: título | `item['path'][-1]` | primeiro de `plan['items']` |
| Hero: caminho | `path[:-1]` unido por " › " | idem |
| Hero: chips | Etapa (`item['stage']`), Estado (`item['learning_state']`), "N erros abertos" **se N>0** | existentes; erros abertos de `study_errors` |
| Hero: motivo | `item['reason']` (uma linha) | existente |
| Hero: estimativa | "≈ N min (estimativa)" **só se** existir mediana de minutos/questão | `view['time_source']` / `effective_profile.minutes_per_question` |
| Hero: ações | primário "Registrar este bloco"; secundário "Ver próximas revisões" (expander existente) | `go_record`, `trajectory_detail` |
| Anel Hoje | `done_questions / target_questions`, texto "restam N" | `plan['done_questions']`, `plan['target_questions']`, `plan['questions']` |
| Ritmo da semana | 7 pontos seg→dom: feito (sessão no dia) / parcial / descanso / futuro | `store.active`, `store.days()`, `guide.days()` |
| Lista Para fazer | demais itens: eyebrow área, título, "N questões", botão secundário "Registrar" | `plan['items'][1:]` |
| Lista Feito hoje | sessões do dia: tema, "x/y acertos", hora local | `view['sessions']` do dia |
| Pausa | só se há ≥1 sessão hoje; 2 frases fixas; botão "Iniciar pausa de 10 min" (fragmento com `run_every`, sem bloquear); botão "Dispensar" | sessões do dia |
| Sua semana | questões na semana (vs. semana anterior), acerto em novas **com n**, temas dominados, dias até a prova-alvo | `topic_statistics`, `exam_targets` |

Estados obrigatórios: **descanso** (hero vira card areia "Hoje é descanso", sem cobrança), **meta cumprida** (hero com "Meta registrada" e atalho "Adiantar revisões"), **sem relatório importado** (hero vira onboarding com ação "Importar relatório"), **erro** (`st.error` simples), **carregando** (`st.spinner`).

### 8.2 Calendário (`study_calendar_ui.py`)
- Barra de controle: `‹ Outubro 2026 ›`, visão (Agenda/Semana/Mês) com `st.segmented_control` **ou** o `st.radio` atual estilizado (confirme AppTest), ir para data.
- Faixa de atrasos: em vez do resumo grande, **uma linha** "N temas pedem nova data" + botão secundário "Reorganizar" (expander existente). Sem vermelho, sem contador punitivo.
- Cards de dia (7 colunas; 2 em ≤ 760 px): **Feito** (check + total), **Hoje** (contorno `--o-primary`, 2px), **Previsão** (borda tracejada + total previsto + até 2 chips de área), **Simulado** (chip "Simulado"), **Descanso** (fundo areia), **Sem plano** (neutro). Mantenha `key='calendar_cell_<data>'` e `calendar_selected`.
- Detalhe do dia abaixo da grade, com cards de bloco no padrão 8.1.

### 8.3 Evolução (`study_evolution_ui.py`)
- Linha do tempo semanal de acerto em **novas com convicção** (n por ponto no tooltip/legenda), barras de volume semanal vs. meta, barras horizontais por área com **faixa Wilson e n**, resumo de consistência (dias com estudo, sem fogo). Sem radar. Sem previsão.

### 8.4 Temas e estatísticas (`study_tables_ui.py`, `study_errors_ui.py`, `study_triage_ui.py`, `goal_risk_ui.py`)
- Abas existentes (Desempenho dos temas · Erros abertos · Plano de corte · Minha meta).
- Barra de filtros em um card: busca + **pills de área com contagem** (`st.pills`/`segmented_control` ou o filtro atual estilizado) + pills de estado (com ícone, sem cor de área).
- Cards de tema em 2 colunas, **paginados em 12**: eyebrow da área, chip de estado, título, apoio "N questões · acerto em novas X% (n=…) · convicção Y%", **barra de acerto com traço na meta (90%)**, e **uma** ação por card ("Registrar resultado", secundário; "Ver erros" se houver erros abertos). Mantenha `list_record_<id>`, `list_extra_<id>`.
- Faixa de fato calculável + botão "Exportar CSV consolidado" (secundário).
- Aba "Minha meta": mostrar corte informado, fonte, confiança, **faixa** do desempenho e rótulo textual (Abaixo / Próximo / Acima / Sem dados suficientes) como já definido no lote C; **nenhuma probabilidade**.

### 8.5 Registrar resultados (`adaptive_ui.py::_register`)
- Card único, largura máxima **680 px**, centralizado: eyebrow da área, título do tema, caminho, seletor "Um bloco que fiz / Total acumulado anterior / Estudei sem fazer questões" (já existe em "Outras formas de registrar"; deixe visível como segmento), campos *Quantas questões · Quantas acertou · Quantas com convicção*, em linha no desktop e empilhados no celular, **com borda e fundo nítidos**.
- Validação visível junto ao campo: acertos ≤ questões; convicção ≤ acertos; mensagem curta ("Acertos não podem passar de 20."). Mantém o que foi digitado.
- Ao salvar: `st.toast` + painel "Salvo. Hoje: x de y." com **primário "Próximo bloco"** (leva ao próximo item de `plan['items']`) e secundário "Voltar ao plano". Proteja contra duplo clique (a identidade `study_entry_id` já existe; confirme).

### 8.6 Simulados (`mock_exams_ui.py`, `mock_schedule_ui.py`) — abas Programação | Resultados
- **Resultados**: card "Último simulado": nome, data, duração, **nota**, **corte informado por você (fonte)**, diferença em p.p. como "referência", card "Por área" com barras (cor da área), "n" e faixa; aviso fixo "Um simulado não é a prova real."
- **Programação**: card de agendamento + explicação "No dia de simulado os blocos normais são dispensados." (se for o comportamento atual; confirme no código).

### 8.7 Ajustes (`adaptive_ui.py::_settings`, `exam_goals_ui.py`, `final_review_ui.py`, `guide_settings_ui.py`)
- 3 cards: **Meta e rotina** (inclui novo "Como quer ser chamado?", opcional), **Minhas provas**, **Instituições e incidências**. Detalhes avançados continuam em expanders.

### 8.8 Flashcards (`practical_reduction_ui.py`) e Arquivos (`ui.py`)
- Flashcards: **recomendações antes** da configuração; cards ou tabela com nomes completos acessíveis; três grandezas separadas (cartões já estudados · cartões para avaliar · revisões/dia); manter os avisos de que volume ≠ suspensão. Sem "economia de minutos/dia" estimada (não é dado do app).
- Arquivos: biblioteca como entrada; ferramentas técnicas em "Avançado".

---

## 9. Navegação (um único menu)

Menu lateral, agrupado, com o item ativo em pílula `--o-primary-tint` + texto `--o-primary-strong`:

```
[logo + "Osler"]
[ botão primário: Registrar bloco ]
ESTUDO     Hoje · Calendário · Evolução · Temas · Simulados
FERRAMENTAS  Flashcards · Arquivos e ferramentas
(rodapé)   Ajustes · [nome, se configurado]
```
Logo: marca própria simples (círculo `--o-primary` com cruz branca em SVG). Não copie marcas de terceiros.

**Implementação (decida na Fase 2, com este critério):**
- **Caminho B (preferido, igual às prévias):** menu único com `st.button(..., type="primary"/"secondary", key="nav_<id>", on_click=...)` que define `st.session_state['main_view']` e `st.session_state['adaptive_view']`. Os radios `main_view`/`adaptive_view` deixam de ser widgets (continuam como chaves de estado). Nos testes, substitua `app.radio(key='adaptive_view').set_value(X).run()` por um helper em `tests/conftest.py`, `open_view(app, 'main', 'adaptive')`, que faz `app.session_state[...] = ...; app.run()`, e troque as asserções `app.radio(key=...).value` por `app.session_state[...]`. **Liste todos os arquivos de teste alterados.**
- **Caminho A (plano de contingência):** manter os dois `st.radio` e as keys, e apenas estilizar (lateral com `main_view`, pílulas no topo com `adaptive_view`). Use se o caminho B exigir mudanças de teste além do helper.
- O item "Registrar" **sai do menu** e vira o botão primário da lateral e o atalho contextual nos blocos (a tela continua existindo como `adaptive_view='Registrar resultados'`).

---

## 10. Fases (uma por sessão)

**Fase 1 — Fundação.** `bento.css`, `bento.py` (+ testes), pilha de fontes e Inter local, tokens em `DESIGN.md` e `.impeccable/design.json`, `seed_demo_data.py`, harness de screenshots, atualização de `study_style.py`. Aplicar só cor/tipografia globais e remover conflitos de `study.css`. *Pronto quando:* testes verdes; telas existentes ainda funcionam com o novo visual base; screenshots "antes/depois" da tela Hoje.

**Fase 2 — Navegação + Meu dia.** Menu único (seção 9), tela 8.1 completa com todos os estados. *Pronto quando:* critérios 11.1–11.6 em Hoje; todos os estados verificados.

**Fase 3 — Temas + Registrar.** Telas 8.4 e 8.5.

**Fase 4 — Calendário, Simulados, Evolução.** Telas 8.2, 8.3 e 8.6.

**Fase 5 — Flashcards, Arquivos, Ajustes e acabamento.** Telas 8.7 e 8.8, auditoria geral com Impeccable, ajuste final de contraste, atualização de `README.md`, `DESIGN.md`, versão.

Em **toda** fase: plano (`writing-plans`) → testes → implementação → ciclo visual (seção 11) → `verification-before-completion` → `requesting-code-review` → commit separado.

---

## 11. Protocolo de verificação visual (obrigatório; AppTest NÃO prova estética)

1. Suba o app com dados sintéticos: `OSLER_DATA_DIR=<tmp> python -m streamlit run app.py --server.port 8602`.
2. Com Playwright (instale como dependência **de desenvolvimento**, fora de `requirements.txt`; se a rede estiver bloqueada, **diga** e use qualquer navegador permitido), capture cada tela nas larguras **1440×900, 1366×768, 768×1024 e 390×844** em `evidencias/bento/faseN/`.
3. Compare cada captura com a prévia correspondente e com esta **rubrica** (marque ✔/✘ e corrija os ✘; máximo **3 rodadas** por tela):
   1. Existe **um único** botão primário por card/contexto?
   2. O hero e o primeiro bloco estão visíveis sem rolagem em 1366×768?
   3. Cada card tem padding uniforme de 24 px e espaçamento entre cards de 16 px?
   4. Há no máximo 3 tamanhos de fonte por card e títulos em peso 650–700?
   5. Nenhum texto cortado, sobreposto ou fora do card (incluindo nomes longos)?
   6. Cor de área só em eyebrow, tint do hero, barras/anéis e botão do hero; **estado sem cor de área**?
   7. Contraste AA medido nos pares usados (rode o cálculo e cole a tabela)?
   8. Há fundo preto em algum card? (**tem de ser não**)
   9. Alinhamento: bordas esquerdas dos cards coincidem; botões alinhados à direita/baixo do card de forma consistente?
   10. Em 390 px, a tarefa principal continua possível e os alvos têm ≥ 44 px?
4. Teclado: percorra a tela com Tab; foco visível em tudo; Enter/Espaço acionam os botões.
5. Zoom de 200% sem perda de tarefa.
6. Cole na entrega a lista dos ✘ que **restaram** e por quê.

**Honestidade:** só escreva "validado visualmente" se você abriu as telas e comparou as capturas. Se não conseguiu abrir um navegador, escreva "verificação visual não realizada" e entregue apenas evidência estática/AppTest, rotulada como tal.

---

## 12. Testes

- Rode `python -m pytest -q` ao final de **cada** passo.
- Novos testes: helpers de `bento.py` (seção 6), mapeamento de áreas contra os nomes reais dos relatórios, estados do hero (descanso, meta cumprida, sem relatório), o fato de que **nenhuma tela contém** as strings proibidas ("probabilidade de aprovação", "estimativa de corte", "Conceitos-Chave", emojis), escape de HTML, paginação de temas (≤ 12 cards por página), ritmo da semana (descanso não quebra), `seed_demo_data.py` recusando `data/`.
- AppTest: telas abrem sem exceção; botões `study_*`, `calendar_cell_*`, `list_record_*` existem; registro salva e atualiza o plano; duplo clique não duplica.
- Se um teste existente quebrar por decisão de design, **altere de propósito** e liste.

---

## 13. Não fazer

- Fundo preto/escuro em cards; emojis; confete; vermelho de alarme; radar; "fogo/recorde".
- Probabilidade de aprovação, previsão de corte, "dificuldade estimada", "conceitos-chave" ou qualquer conteúdo inventado.
- Misturar denominadores; mostrar percentual sem n; transformar ausência em zero.
- Renderizar centenas de cards; JavaScript próprio; CDN; fonte SF Pro no repositório.
- Alterar regras de negócio, schema ou gravação.
- Testar no banco real; apagar histórico.
- Declarar sucesso sem executar a verificação.

---

## 14. Entrega de cada fase

Responda, nesta ordem, de forma curta:
1. Arquivos alterados/criados.
2. Decisões tomadas por conta própria (e por quê).
3. Saída de `pytest` (comando e resultado).
4. Capturas antes/depois e a rubrica preenchida (ou a declaração de que não houve verificação visual).
5. Testes alterados e justificativa.
6. Pendências e limitações (inclusive Inter/fonte, Playwright, `corner-shape`).
7. Como reverter (commits).

**Comece pelo inventário e pelo plano da fase pedida. Não implemente nada antes de apresentar o plano.**
