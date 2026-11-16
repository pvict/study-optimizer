# Aviso de temas novos com saldo e ajustes calculados

Base: 92c8fa3686c1ad858d4c81ffc061d1b82e4fda49. Escopo pedido pelo usuário: mostrar quantas questões em temas novos faltam e quais valores ajustar para incluí-las. Execução direta já autorizada em AGENTS.md.

1. Corrigir o diagnóstico para comparar o mínimo diário com questões efetivamente feitas e presentes no plano, não apenas admissões intermediárias.
2. Reutilizar o próprio alocador para testar ajustes de máximo de temas e proporção de novos, isolados e combinados, mantendo a quantidade diária e compromissos. Mostrar valores anteriores e sugeridos. Não gravar configurações ao consultar.
3. Calcular alternativas somente ao abrir o aviso. Sem alternativa dentro desses controles, informar isso explicitamente e quantificar compromissos/questões, sem prometer encaixe ou aumentar a carga silenciosamente.
4. Testar primeiro o saldo real (inclusive mínimo já atingido por reservas), sugestões executáveis, ausência de candidatos, compromissos e consultas sem alterações no banco. Validar UI e suíte completa em CI; integrar à branch do app sem nova etapa burocrática.

O diagnóstico trata do mínimo configurado de questões em temas novos para o dia, não da conclusão de todos os temas do acervo. Os rótulos devem deixar isso explícito. Não alterar o motor pedagógico, datas ou resultados.

## Verificação e decisões

- RED→GREEN: 12 testes de domínio, incluindo contagem final, alternativas isoladas/combinadas, controle percentual efetivo, inventário insuficiente, extras e crédito de alocação diferente da quantidade realmente feita.
- A revisão independente identificou quatro casos: conclusão parcial posterior ao diagnóstico, uso de créditos em vez de quantidade real, extras omitidos das reservas e indicação indevida para reagendar quando faltava acervo. Os quatro receberam reprodução e correção no mesmo passe.
- Decisão: o serviço fornece um finalizador puro de conclusões ao alocador, aplicado também em cada simulação, para reutilizar os mesmos compromissos e decisões do dia sem repetir consultas ao banco em cada alternativa. O diagnóstico não altera os blocos efetivamente gerados.
- Serviço real: a alternativa 2→3 temas foi reproduzida em overview; reservas e registros preservados. Conclusão parcial real de um tema reservado deixou feitas=5, plano=0 e faltantes=7, sem sugerir reabrir silenciosamente o bloco.
- CI inclui verificação rápida dos testes novos antes da comparação da suíte completa com as falhas preexistentes.
