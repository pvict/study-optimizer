# Bento — entrega da fase 1

Data: 27/10/2026. Base: `a851ad1`. Escopo: **Fundação**, conforme o pedido; fases2–5 não executadas.

## Arquivos

| Grupo | Arquivos |
|---|---|
| Fundação | `osler/bento.css`, `osler/bento.py`, `osler/study_style.py`, remoção de declarações conflitantes em `osler/study.css` |
| Fonte e tema | `.streamlit/config.toml`, `static/fonts/InterVariable.woff2`, `docs/third-party/Inter-OFL.txt` |
| Documentação | `DESIGN.md`, `.impeccable/design.json`, este relatório, `docs/plans/2026-10-27-bento-fase1.md`, briefing original em `docs/redesign/` |
| Desenvolvimento | `scripts/seed_demo_data.py`, `scripts/capture_bento.py`, `requirements-dev.txt`, `.gitignore` |
| Novos testes | `tests/test_bento.py`, `tests/test_bento_demo.py`, `tests/test_bento_foundation.py`, `tests/fixtures/bento_components_app.py` |

Nenhum teste preexistente alterado. Nenhum módulo de cálculo, agenda, modelo, importação, schema ou persistência do app alterado. README e versão0.27.0 mantidos: atualização geral prevista para a fase5. O arquivo do usuário `docs/design/DIRETRIZES-REDESIGN-BENTO-CLAUDE.md` foi preservado fora do commit.

## Decisões de implementação

- O CSS existente continua responsável pela composição. Tokens e tipografia Bento carregam depois, com aliases `--study-*`. Não montar antecipadamente o novo menu ou hero.
- Containers, variantes das cinco áreas e estado neutro estão preparados. A fixture mostra esses componentes com conteúdo **sintético**, sem inserir demonstração no app do usuário.
- Inter4.1 variável foi obtida do repositório oficial; um WOFF2 local de352.240bytes, licença OFL preservada. SHA256: `693b77d4f32ee9b8bfc995589b5fad5e99adf2832738661f5402f9978429a8e3`. Nenhum arquivo SF Pro incluído. O Windows deste teste já possui SF Pro Display: CDP confirmou seu uso pela pilha aprovada. O fallback Inter foi forçado apenas durante a sonda de teste e confirmado como fonte customizada efetivamente renderizada; o estilo original foi restaurado antes da captura.
- Playwright1.64.1 é dependência de desenvolvimento. Edge instalado foi reutilizado; nenhum Chromium adicional foi baixado. O harness aceita exclusivamente127.0.0.1:8602, cria seu próprio servidor e bloqueia recursos remotos.
- Gerador recusa destino existente, banco preexistente, `data/`, caminhos fora do temporário e links/junções antes de abrir Repository. Só cria o cenário sintético:40temas,5áreas,2PDFs,14dias com descanso/parcial,3erros,prova-alvo e simulado.
- O SVG do anel precisa do renderizador Markdown nativo: o sanitizador de `st.html`1.66 elimina SVG. Não habilitar JavaScript. Validação e escape permanecem no helper; botões/campos continuam widgets nativos. Captura da fixture confirma40/60.
- Ausência mantém traço e rótulo acessível; zero continua zero. Percentual visual limita a trilha sem alterar os totais reais. Números negativos/não finitos, classes arbitrárias e tamanho inválido são recusados.
- Execução no ramo `codex/bento-fase1`, sem cópia do ambiente/banco. Integração local prevista no plano; sem push. A autorização do usuário e AGENTS dispensa menu adicional de aprovação para esta alteração reversível.

## Testes

Comando: `.venv/Scripts/python.exe -m pytest -q`.

| Momento | Resultado |
|---|---|
| Baseline antes de editar | 780 passed,1warning,215.59s |
| Cenário/harness | 788 passed,1skipped,1warning,265.89s |
| Fundação e revisões | 818 passed,1skipped,1warning,202.16s |
| Rechecagem completa | 818 passed,1skipped,1warning,217.54s |
| Helpers/fundação/cenário após correção do renderer SVG | 39 passed,1skipped,2.81s |
| Árvore final | **819 passed,1skipped,1warning,206.12s** |

O skip é criação física de symlink indisponível no Windows; o teste alternativo de ancestral indireto passou. O warning é o ZIP deliberadamente duplicado do teste de segurança de backups, já presente na baseline.

## Evidência visual e funcional

Todos os números e temas nas capturas abaixo pertencem ao cenário sintético. O banco real não foi aberto para QA. As imagens e JSON ficam locais em `evidencias/bento/fase1/` e são ignorados pelo Git.

| Hoje | Antes | Depois |
|---|---|---|
| 1440×900 | [Imagem](../../evidencias/bento/fase1/antes-hoje-1440x900.png) | [Imagem](../../evidencias/bento/fase1/depois-hoje-1440x900.png) |
| 1366×768 | [Imagem](../../evidencias/bento/fase1/antes-hoje-1366x768.png) | [Imagem](../../evidencias/bento/fase1/depois-hoje-1366x768.png) |
| 768×1024 | [Imagem](../../evidencias/bento/fase1/antes-hoje-768x1024.png) | [Imagem](../../evidencias/bento/fase1/depois-hoje-768x1024.png) |
| 390×844 | [Imagem](../../evidencias/bento/fase1/antes-hoje-390x844.png) | [Imagem](../../evidencias/bento/fase1/depois-hoje-390x844.png) |

36capturas finais: Hoje, Calendário, Evolução, Temas, Registrar, Simulados, Ajustes, Flashcards e Arquivos nas quatro resoluções. Inspeção humana pelo agente das capturas desktop/mobile de Hoje, Temas, Registrar e Simulados, além da fixture de componentes e registro em zoom emulado. As demais telas passaram pelo smoke no navegador e medições; não alegar avaliação manual de cada detalhe das36imagens.

Manifesto final: **zero overflow horizontal da página**, zero botões visíveis no conteúdo principal abaixo de44×44px (tolerância de arredondamento0.5px), nenhum recurso remoto solicitado. Títulos32px em768/1366/1440 e24px em390. Texto de apoio com opacidade computada1. A sonda CDP comprova SF Pro instalada e fallback Inter Variable, com352.240bytes locais carregados.

Na primeira inspeção, o apoio declarado4B5563 era atenuado pela opacidade0.6 do container nativo, resultando em contraste próximo de2.79:1. A correção foi no container, preservando controles desabilitados. Os botões auxiliares de24/32px ganharam largura mínima44px. A segunda medição eliminou ambos os problemas; a rodada final confirmou o estado. Ajustes do harness (espera de HTML/renderer SVG) corrigiram a evidência, sem redesign adicional de páginas.

Teclado: Espaço selecionou Registrar; foco visível de3px; Enter submeteu o formulário. Entrada inválida21acertos/20questões continuou preenchida e não gravou evento. Correção para16/20com12convictas salvou uma vez; voltar/recarregar não duplicou. Zoom200% **emulado** por683×384CSSpx comDPR2, equivalente à área útil de1366×768: formulário concluído sem overflow. Não representa teste físico em aparelho nem certificação completa de acessibilidade.

Evidências: `depois-manifest.json`, `interacao.json`, `componentes.json`, `contrastes.json`, `detector.json`. O `interLoaded` do manifesto antigo de antes era apenas `document.fonts.check`, que pode dar falso positivo; não é prova de carregamento. A comprovação válida é a sonda CDP do manifesto final.

## Rubrica do briefing

✔: atendido no escopo; N/A: composição de fase futura; ✘: pendência material.

| # | Resultado | Evidência/limite |
|---|---|---|
| 1 | ✔ na fixture; N/A para revisão das composições | Um primário no contexto Bento de teste. Ações das páginas existentes preservadas. |
| 2 | N/A, pendência da fase2 | Não há novo hero. O primeiro botão de registro da composição antiga fica abaixo da dobra em1366×768; não declarar este critério satisfeito. |
| 3 | ✔ na fixture; N/A nas páginas legadas |24px de padding e16px de gap nos novos containers. A geometria antiga permanece. |
| 4 | ✔ na fixture | Até3tamanhos por card e título650; títulos das páginas700. Composições legadas não foram reestruturadas. |
| 5 | ✔ nas capturas inspecionadas | Sem corte/sobreposição observado; nomes quebram naturalmente. Todas as36medições sem overflow da página. |
| 6 | ✔ nos novos componentes | Cor de área em eyebrow/tint/barra/primário; estados neutros e textuais. |
| 7 | ✔ |18pares textuais AA, tabela abaixo; apoio computado sem atenuação. |
| 8 | ✔ nas capturas inspecionadas | Nenhum card preto observado; tema claro. |
| 9 | N/A para nova composição | Alinhamento existente preservado; fixture com padding uniforme. Posicionamento final das ações pertence às telas futuras. |
| 10 | ✔ no fluxo testado | Registro possível em390px; conteúdo principal com botões≥44px; tabelas largas mantêm seu próprio contêiner. |

Nenhum ✘ de fundação ficou aberto. Critérios2/3/9 e parte1 são adiados explicitamente pela limitação da fase1; isso não equivale a validar o layout completo das prévias.

## Contraste calculado

Fórmula WCAG de luminância relativa sRGB, texto normal≥4.5:1. `fill` decorativo não é cor de texto. Números arredondados a duas casas.

| Par | Primeiro plano / fundo | Razão | Resultado |
|---|---|---|---|
| Texto/página | #111827 / #F6F7FB |16.57:1| AA |
| Apoio/página | #4B5563 / #F6F7FB |7.06:1| AA |
| Apoio/branco | #4B5563 / #FFFFFF |7.56:1| AA |
| Terciário/branco | #6B7280 / #FFFFFF |4.83:1| AA |
| Branco/primário | #FFFFFF / #4338CA |7.90:1| AA |
| Areia | #5B4A32 / #F5F1EA |7.55:1| AA |
| Clínica ink/tint | #3730A3 / #EEF2FF |8.88:1| AA |
| Branco/Clínica solid | #FFFFFF / #4338CA |7.90:1| AA |
| Cirurgia ink/tint | #B42318 / #FFF1F0 |5.98:1| AA |
| Branco/Cirurgia solid | #FFFFFF / #B42318 |6.57:1| AA |
| Pediatria ink/tint | #047857 / #ECFDF5 |5.21:1| AA |
| Branco/Pediatria solid | #FFFFFF / #047857 |5.48:1| AA |
| GO ink/tint | #6D28D9 / #F5F3FF |6.48:1| AA |
| Branco/GO solid | #FFFFFF / #6D28D9 |7.10:1| AA |
| Preventiva ink/tint | #92400E / #FFFBEB |6.84:1| AA |
| Branco/Preventiva solid | #FFFFFF / #92400E |7.09:1| AA |
| Neutral ink/tint | #374151 / #F3F4F6 |9.37:1| AA |
| Branco/Neutral solid | #FFFFFF / #374151 |10.31:1| AA |

## Revisões e limites

Duas revisões independentes: visual (10capturas desktop/mobile) e técnica (diff completo/segurança/contratos). Corrigidos: apoio atenuado, alvos pequenos, rótulo ausente da barra e falsa comprovação da fonte por`fonts.check`. A verificação final da fixture detectou o sanitizador SVG; uso do renderer nativo e teste de navegador confirmaram a correção.

Detector Impeccable executado **uma vez**, com12achados (2warnings,10advisories). Inter mantida porque exigida pelo briefing; aviso de borda da navegação refere-se à estrutura legada. Os10avisos comparavam valores com os tokens documentais antigos; DESIGN/sidecar foram alinhados. Não foi executado segundo detector e não se declara resultado zero.

`corner-shape` foi suportado no Edge usado (`superellipse(2)`, raio34px). Removendo apenas a regra de melhoria progressiva no teste, o fallback computado foi24px, em1440e390. Safari/Firefox e dispositivos físicos não testados. Ícones Material em HTML são omitidos até existir fonte local, como permitido no briefing; rótulos dos estados permanecem. Não houve acesso à plataforma Osler.

As capturas são evidência local e não viajam no clone Git. O harness e o gerador permitem reproduzir o cenário; cada reprodução só deve usar nova pasta no temporário. O cenário desta fase foi removido após validar seu caminho absoluto e marcador sintético; servidor8602 encerrado. Evidências preservadas: aproximadamente3.2MB. Dados pessoais, originais, backups e worktrees anteriores foram preservados.

## Integração e reversão

Um commit separado da fase será integrado localmente, sem push. Para desfazer apenas esta fase, use `git revert <commit-da-fase1>` identificado por `git log --oneline --grep='Bento phase 1'`. A base anterior é`a851ad1`. Não executar reset/clean nem apagar dados para reverter uma alteração visual.
