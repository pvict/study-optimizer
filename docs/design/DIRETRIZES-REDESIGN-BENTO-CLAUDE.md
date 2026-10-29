# Mapeamento do Sistema Real & Especificação Completa de Redesign: Osler Bento Grid & Anti-Burnout
**Documento Técnico Mestre para o Claude (Geração de Prompts de Implementação para o Codex)**  
*Aplicação: Osler — Sistema de Preparação para Residência Médica (Streamlit)*  
*Local do Código no Host: `C:\Projetos\Osler`*  
*Data de Mapeamento: 23 de Outubro de 2026*

---

## 1. Mapeamento Arquitetural do Sistema Real

Inspecionamos diretamente o código-fonte em execução no disco. O Osler é composto por uma casca global de navegação e três grandes módulos centrais:

```text
OSLER (ui.py)
 ├── 1. Meu estudo (Plano de questões) [adaptive_ui.py]
 │    ├── 1.1 Meu dia (Hoje) [study_day_ui.py]
 │    ├── 1.2 Calendário [study_calendar_ui.py]
 │    ├── 1.3 Evolução [study_evolution_ui.py]
 │    ├── 1.4 Temas e estatísticas [study_tables_ui.py, study_errors_ui.py, study_triage_ui.py, goal_risk_ui.py]
 │    │    ├── Tab: Desempenho dos temas
 │    │    ├── Tab: Erros abertos
 │    │    ├── Tab: Plano de corte
 │    │    └── Tab: Minha meta (+ Exportar CSV consolidado)
 │    ├── 1.5 Registrar resultados [adaptive_ui.py: _register]
 │    ├── 1.6 Simulados [mock_exams_ui.py, mock_schedule_ui.py]
 │    │    ├── Tab: Programação
 │    │    └── Tab: Resultados
 │    └── 1.7 Ajustes do plano [adaptive_ui.py: _settings, exam_goals_ui.py, final_review_ui.py, guide_settings_ui.py]
 │         ├── Subseção: Meta e rotina
 │         ├── Subseção: Minhas provas (pesos e metas)
 │         └── Subseção: Instituições e incidências
 ├── 2. Flashcards (Diminuir revisões) [reduction_ui.py -> practical_reduction_ui.py]
 │    └── Triagem prática de temas para suspensão seletiva de revisões
 └── 3. Arquivos e ferramentas [ui.py: _advanced_tools, _data_tabs]
      ├── Tabs: Biblioteca | Importar relatórios | Inspecionar dados | Validação e auditoria | Cruzamento | Classificação
      └── Backup e restauração de dados [backups_ui.py]
```

---

## 2. Princípios de Design e Tokens Visuais (Bento Grid & Anti-Burnout)

### 2.1 Filosofia Acolhedora & Anti-Burnout
1. **Sem métricas de estresse:** Substituir contadores punitivos e cores vermelhas alarmistas por indicadores de ritmo saudável. Em vez de "X blocos atrasados", usar *"X temas sugeridos para redistribuir no seu ritmo"*.
2. **Foco no próximo passo:** Reduzir o ruído visual; a tela inicial destaca com clareza o bloco imediato.
3. **Pausas e descompressão ativas:** O estudo de alto rendimento para residência exige preservação cognitiva.
4. **Celebração de progresso:** Feedbacks comemorativos a cada bloco concluído ou simulado registrado.

### 2.2 Tokens de Design Global (CSS Streamlit)
```css
/* Paleta Global */
--bg-osler: #FBFBFC;              /* Fundo off-white relaxante */
--card-osler: #FFFFFF;            /* Branco puro dos cartões */
--border-subtle: rgba(0,0,0,0.06);
--radius-squircle: 24px;
--shadow-bento: 0 4px 20px -2px rgba(0,0,0,0.03), 0 2px 6px -1px rgba(0,0,0,0.02);
--shadow-hover: 0 10px 30px -4px rgba(0,0,0,0.08);

/* Tipografia */
--font-display: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, sans-serif;
--text-primary: #111827;          /* Preto display pesado (800) */
--text-secondary: #4B5563;        /* Cinza escuro leitura */
--text-muted: #6B7280;            /* Cinza médio apoio */

/* Cores das 5 Grandes Áreas Médicas */
--cor-clinica: #4F46E5;           /* Índigo Vibrante */
--cor-cirurgia: #FF6B6B;          /* Coral Quente */
--cor-pediatria: #10B981;         /* Esmeralda / Menta */
--cor-ginecologia: #8B5CF6;       /* Violeta Suave */
--cor-preventiva: #F59E0B;        /* Âmbar / Dourado */
```

---

## 3. Redesign Detalhado Seção por Seção

### SEÇÃO 1: NAVEGAÇÃO LATERAL (Sidebar Global em `ui.py`)
* **Situação Atual:** Radio buttons verticais simples com rótulos `Meu estudo`, `Flashcards`, `Arquivos e ferramentas`.
* **Proposta Bento Grid:** Sidebar estilo macOS/iPadOS com cantos arredondados, avatar/identificação do aluno, badge de meta do dia e pílulas táteis de seleção.
```text
┌──────────────────────────────────────┐
│  🩺 OSLER RESIDÊNCIA                 │
│  Dr. Paulo · Foco R1 2026/2027       │
├──────────────────────────────────────┤
│  ☀️  Meu Estudo (Plano Diário)       │  <- Ativo (Pill estilizada com fundo sutil)
│  🃏  Flashcards (Redução de Fila)    │
│  📂  Arquivos & Biblioteca           │
├──────────────────────────────────────┤
│  💾  Backup Rápido                   │
│  ℹ️  Sobre o App                     │
└──────────────────────────────────────┘
```

---

### SEÇÃO 2: "MEU DIA" (Dashboard Hoje em `study_day_ui.py`)
* **Situação Atual:** Título genérico, texto de progresso, containers cinzentos padrão e formulários com sliders.
* **Proposta Bento Grid:**
```text
┌─────────────────────────────────────────────────────────────────────────────────────────────┐
│  BOM DIA, PAULO 👋                                                  [ Sexta, 23 de Outubro ] │
│  Mantenha seu ritmo sem pressa. Cada bloco conta.                                         │
├──────────────────────────────────────────────────────────────┬──────────────────────────────┤
│  CARD 1 (HERO BENTO 2x2) - PRÓXIMO BLOCO                     │  CARD 2 (1x1) - CONSTÂNCIA   │
│  [EYEBROW: CIRURGIA GERAL · 20 QUESTÕES]                     │  [EYEBROW: DISCIPLINA]       │
│  Cicatrização e Avaliação de Feridas Complexas               │  🔥 4 dias em ritmo ativo    │
│  Foco: Cicatrização por 2ª intenção e feridas crônicas       │  "Constância vence volume"   │
│  Tempo sugerido: 40 min · Dificuldade estimada: Média        ├──────────────────────────────┤
│                                                              │  CARD 3 (1x1) - RITMO DO DIA │
│  [ Iniciar & Registrar Bloco ➜ ]   [ Ver Conceitos-Chave ]   │  [EYEBROW: BATERIA DO DIA]   │
│                                                              │  🔋 65% concluído (2/3 blocos│
├──────────────────────────────────────────────────────────────┴──────────────────────────────┤
│  CARD 4 (2x1) - ABAS: "PARA FAZER (1)"  |  "FEITO HOJE (2)"  |  "PAUSA CONSCIENTE (☕ 10 min)"│
│  • Bloco 2: Cetoacidose Diabética (Clínica Médica · 20 quest.) [ Registrar ]               │
│  • Bloco 3: Pré-Natal de Baixo Risco (GO · 15 quest.) [ Registrar ]                         │
└─────────────────────────────────────────────────────────────────────────────────────────────┘
```

---

### SEÇÃO 3: "CALENDÁRIO DE ESTUDOS" (`study_calendar_ui.py`)
* **Situação Atual:** Controles dispersos de semanas e tabela com listas de dias.
* **Proposta Bento Grid:**
  - **Tile de Controle:** Navegação compacta `[ < ] Outubro 2026 [ > ]` com seletor de visualização (Semana/Mês) e status do plano adaptativo.
  - **Grid Semanal:** Cada dia é um mini Bento Card contendo chips coloridos por especialidade e badges de conclusão.
  - **Ação Anti-Burnout:** Botão *"Reorganizar temas pendentes no meu ritmo"* sem marcas punitivas de atraso.

---

### SEÇÃO 4: "EVOLUÇÃO" (`study_evolution_ui.py`)
* **Situação Atual:** Gráficos padrão Streamlit com dados brutos.
* **Proposta Bento Grid:**
  - **Card de Acurácia:** Percentual geral e curva de evolução semanal inspirada nos anéis do Apple Health.
  - **Card de Volume:** Total de questões resolvidas versus meta semanal com barra suave.
  - **Radar Bento das 5 Áreas:** Visualização equilibrada de proficiência entre Clínica, Cirurgia, Pediatria, GO e Preventiva.

---

### SEÇÃO 5: "TEMAS E ESTATÍSTICAS" (`study_tables_ui.py`, `study_errors_ui.py`, `study_triage_ui.py`, `goal_risk_ui.py`)
Contém 4 abas essenciais que agora ganham formatação Bento modular:
1. **Aba "Desempenho dos Temas":**
   - Barra Bento de busca rápida instantânea.
   - Pílulas coloridas para filtro por Área e por Status (`Aprendendo 🌱`, `Dominado ⭐️`, `Em Alerta ⚠️`).
   - Cards táteis por tema (em vez de tabela cinza única) com botão direto de registrar ou praticar.
2. **Aba "Erros Abertos":**
   - Lista acolhedora dos conceitos errados recentemente nos blocos, agrupados por especialidade médica, permitindo revisão cirúrgica dos pontos fracos.
3. **Aba "Plano de Corte":**
   - Triagem visual destacando quais temas têm maior probabilidade de cair na banca versus temas que podem ser suspensos ou estudados de forma simplificada.
4. **Aba "Minha Meta":**
   - Indicador de probabilidade e ritmo necessário para cumprir o edital sem estresse, com botão elegante de exportar CSV consolidado.

---

### SEÇÃO 6: "REGISTRAR RESULTADOS" (`adaptive_ui.py: _register`)
* **Situação Atual:** Formulário aberto em tela cheia com campos numéricos largos.
* **Proposta Bento Grid:**
  - **Formulário Centralizado em Card Bento (680px de largura máxima):**
    - Identificador visual do tema com a cor da especialidade.
    - Seletor rápido de tipo: Bloco do dia / Total acumulado anterior / Contato sem questões.
    - Campos bem delimitados com bordas nítidas para: *Total de Questões*, *Acertos* e *Acertos com Convicção (sem chute)*.
    - Card comemorativo instantâneo ao salvar com incentivo positivo e botão direto para o próximo bloco.

---

### SEÇÃO 7: "SIMULADOS" (`mock_exams_ui.py`, `mock_schedule_ui.py`)
* **Aba "Programação":**
  - Card Bento para agendar simulados de fim de semana, com o recurso automático de *dispensa de blocos normais no dia de prova*, evitando sobrecarga.
* **Aba "Resultados":**
  - Registro da prova completa com campos de nota geral, pontuação por grande área e comparação automática com a nota de corte da instituição desejada.

---

### SEÇÃO 8: "AJUSTES DO PLANO" (`adaptive_ui.py: _settings`, `exam_goals_ui.py`, etc.)
Organizado em 3 cards Bento claros:
1. **Meta e Rotina:** Definição da meta diária de questões, dias de descanso semanal e alternância entre rotina *Adaptativa* (que abre espaço automático para revisões) e *Fixa*.
2. **Minhas Provas:** Cadastro das bancas de residência pretendidas, metas de nota e pesos por prova.
3. **Instituições e Incidências:** Pesos específicos por especialidade conforme os editais das bancas.

---

### SEÇÃO 9: "FLASHCARDS" (`practical_reduction_ui.py`)
* **Deck Bento de Revisão Ativa:**
  - Card com resumo amigável de temas recomendados para suspensão de revisões diárias.
  - Critérios de segurança transparentes (mínimo de 30 respondidas, acerto >= 85%, 20 cartões estudados).
  - Economia de tempo estimada em minutos/dia com a suspensão seletiva.

---

### SEÇÃO 10: "ARQUIVOS E FERRAMENTAS" (`ui.py: _advanced_tools`)
* **Biblioteca de Relatórios:** Cards limpos com status de cada PDF importado (Qbank e Flashcards), identificação automática de duplicados e ferramentas de auditoria e backup.

---

## 4. Plano de Implementação para o Codex (4 Prompts Sequenciais)

O Claude deve instruir o Codex a executar as mudanças em 4 fases seguras sem quebrar a lógica existente:

1. **Fase 1 — CSS Global & Tokens Bento (`osler/study_style.py`):**
   - Injeção das fontes `Plus Jakarta Sans`, classes `.osler-bento-card`, `.osler-eyebrow`, botões com efeito hover tátil e esquema de cores por especialidade.
2. **Fase 2 — Shell de Navegação & Tela "Meu Dia" (`osler/ui.py` e `osler/study_day_ui.py`):**
   - Modernização da Sidebar e implementação do Bento Grid da dashboard inicial com Hero Card 2x2 e cartões de ritmo/pausa.
3. **Fase 3 — Registro de Resultados & Temas (`osler/adaptive_ui.py` e `osler/study_tables_ui.py`):**
   - Card de formulário centralizado para registro rápido e abas de temas com filtros em pílulas coloridas e erros abertos.
4. **Fase 4 — Calendário, Simulados, Flashcards e Ajustes:**
   - Padronização das demais telas no formato Bento Grid, validação de responsividade e preservação de todos os cálculos existentes.
