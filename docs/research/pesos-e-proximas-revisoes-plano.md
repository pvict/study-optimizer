# Pesos com incidência e próximas revisões — desenho e plano

Pedido: desfazer a alteração de pesos que descartou a tabela conjunta, bloquear pesos por prova sem incidências individuais, avisar todo impacto com prévia e mostrar a próxima revisão de um tema pesquisado. Execução autorizada sem novas aprovações burocráticas.

Decisões: pesos modificam importância, não a seleção de instituições. Preservar o conjunto configurado e exigir tabelas individuais aplicáveis para todas as instituições que participarão do cálculo ponderado. Tabelas conjuntas continuam válidas para o conjunto sem pesos individuais. Pesos antigos incompatíveis têm efeito suspenso com aviso; o histórico não é alterado. Desfazer o peso atual cria nova versão do perfil, preservando provas, cortes, simulados e estudos.

Uma política pura `exam_weight_policy.py` resolve pesos, fontes e impedimentos. `StudyStore.save_profile` valida dentro da transação; `profile` mantém fallback seguro para perfis legados e expõe o motivo. `exam_weight_service.py` monta prévia do perfil, dados/alcance de incidência, instituições antes/depois, temas e blocos atuais, próximos contatos da janela de 28 dias e limites/carga. Token e conteúdo são conferidos novamente antes de aplicar. `exam_weights_ui.py` troca a escrita direta por prévia/aplicar. Meta de 120 e parâmetros estatísticos ficam intactos.

Para Temas: buscar o próximo bloco no calendário operacional até o fim da preparação, com limite de 18 meses, e manter a data devida separada. A próxima data prevista aparece junto ao nome/estado tanto na visão de histórico quanto na de blocos, também em lista e CSV. Sem vaga, sem catálogo ou sem horizonte: texto explícito, sem inventar datas. Datas futuras são condicionais aos próximos resultados. Cache de sessão por data e token evita recalcular a cada tecla.

Stack: Python, Streamlit, SQLite, pytest/AppTest. Superpowers:executing-plans/TDD; Revenue-Centric Design e Impeccable no visual existente. Isolamento por branch local `codex/pesos-com-incidencia-e-revisoes`, mantendo o app na pasta autorizada e sem replicar dados.

- [x] Backup e nova versão do perfil para retirar somente o peso incompatível atual.
- [x] RED/GREEN: bloqueio de tabela conjunta/futura/vazia, cobertura individual completa, preservar instituições, fallback legado, impedir gravação direta, perfis sem pesos preservados.
- [x] Prévia/aplicar com token e perfil esperado; comparação de fontes, pesos, acerto/convicção, estados/prioridades, plano de hoje e próximos contatos. Sem estudo fictício; avisos de perda de vaga e alcance explícitos.
- [x] RED/GREEN e AppTest da interface de pesos: controles desabilitados quando faltam fontes, prévia sem escrita, aplicação explícita, invalidar prévia ao mudar dados/entradas.
- [x] RED/GREEN: próxima revisão real respeita simulado, descanso e reservas; casos sem vaga/catalogo; coluna visível ao pesquisar em histórico e blocos, lista e exportação.
- [x] Revisão independente, suíte completa, QA em cópia mínima real e no navegador; documentação, versão 0.24.1, registro local das alterações.

Pontos de revisão: importar uma prova não autoriza retirar outras; nenhuma incidência conjunta vira individual; dados futuros/sem massa não habilitam pesos; renomear/desconsiderar prova não contorna validação; uma data vencida não pode aparecer como próxima vaga; preview deve reproduzir exatamente o perfil que será salvo e não esconder contatos que perderam vaga.
