# Aviso de temas novos com saldo e ajustes calculados

Base: 92c8fa3686c1ad858d4c81ffc061d1b82e4fda49. Escopo pedido pelo usuário: mostrar quantas questões em temas novos faltam e quais valores ajustar para incluí-las. Execução direta já autorizada em AGENTS.md.

1. Corrigir o diagnóstico para comparar o mínimo diário com questões efetivamente feitas e presentes no plano, não apenas admissões intermediárias.
2. Reutilizar o próprio alocador para testar ajustes de máximo de temas e proporção de novos, isolados e combinados, mantendo a quantidade diária e compromissos. Mostrar valores anteriores e sugeridos. Não gravar configurações ao consultar.
3. Calcular alternativas somente ao abrir o aviso. Sem alternativa dentro desses controles, informar isso explicitamente e quantificar compromissos/questões, sem prometer encaixe ou aumentar a carga silenciosamente.
4. Testar primeiro o saldo real (inclusive mínimo já atingido por reservas), sugestões executáveis, ausência de candidatos, compromissos e consultas sem alterações no banco. Validar UI e suíte completa em CI; integrar à branch do app sem nova etapa burocrática.

O diagnóstico trata do mínimo configurado de questões em temas novos para o dia, não da conclusão de todos os temas do acervo. Os rótulos devem deixar isso explícito. Não alterar o motor pedagógico, datas ou resultados.
