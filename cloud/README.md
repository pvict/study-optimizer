# Acesso online privado

A mesma aplicação Python roda no Streamlit Community Cloud, com estado persistente no projeto Supabase do usuário. O PC pode ficar desligado. A cópia local continua independente: depois da migração, use a URL online nos dois dispositivos para manter um só histórico.

## Configuração

1. Crie organização/projeto no **Free** do Supabase, sem add-ons pagos. Copie o host do **Session pooler** em Connect.
2. Em uma pasta restrita fora deste repositório, crie `supabase-credentials.toml` com `[supabase]` e `database_password`. Não envie senhas no chat ou no Git.
3. Instale os requisitos de `cloud/requirements.txt`. Execute `scripts/configure_cloud.py --project-ref SEU_REF --host SEU_HOST --private-dir SUA_PASTA_PRIVADA`. O script aplica `cloud/schema.sql`, cria o papel `osler_cloud` com acesso somente às funções do app e salva `cloud-secrets.toml` e `app-access.txt` na pasta privada. Não utiliza a senha administrativa na aplicação hospedada.
4. O branch de deploy precisa de `cloud_app.py` na raiz, `cloud/requirements.txt` como `requirements.txt` e config com `server.address="0.0.0.0"`, sem `browser.serverAddress="127.0.0.1"`. O script `scripts/build_cloud_branch.py` prepara esse branch preservando a árvore local.
5. No Community Cloud, escolha Python **3.13**, repositório **privado**, branch de deploy e `cloud_app.py`. Cole `cloud-secrets.toml` em Advanced settings > Secrets. Confirme que o app está **private** antes de importar dados. Nunca comite secrets.
6. Entre com a senha de `app-access.txt`. Importe o ZIP verificado ou use `scripts/seed_cloud.py --backup ARQUIVO --secrets-file CONFIG_PRIVADA`. A inicialização recusa sobrescrever dados online existentes.
7. Verifique relatórios, totais e calendário. Abra o mesmo endereço no celular. Não misture lançamentos na cópia local e online: elas não têm sincronização bidirecional.

Depois de confirmar **Sharing > Only specific people can view this app**, você pode definir `auth_mode = "streamlit_private"` nos secrets. Esse modo usa somente o login nativo da hospedagem. Mantenha o app privado: não use essa configuração em hospedagem pública. O modo `password` conserva a senha adicional.

## Persistência e segurança

- TLS `verify-full` verifica CA e hostname. Certificado público obtido no painel oficial em Database > Settings > SSL configuration: https://supabase-downloads.s3-ap-southeast-1.amazonaws.com/prod/ssl/prod-ca-2021.crt . SHA256 do arquivo: `700723581420dd1ac98fd7e9ac529f0ef210eadcaf87fc868a3ad7d114c2f3b7`.
- Tabelas em schema privado, RLS habilitada, sem acesso anônimo/autenticado da API. Papel do app tem apenas EXECUTE das cinco funções SECURITY DEFINER com search_path fixo. Nenhuma automação ou conexão com a plataforma Osler.
- Cada execução e dialog mutável usa lease de cinco minutos, lock por processo e comparação da revisão. Objetos têm SHA256 e compressão; SQLite usa backup consistente. O manifesto só muda depois do upload completo.
- Falha de rede mantém estado pendente, evita substituir alterações locais por dados remotos novos e suprime toast de sucesso. A tela oferece cópia de recuperação. Se houver conflito, baixe essa cópia antes de reiniciar a hospedagem; não repita o registro.
- Senha adicional: PBKDF2-SHA256, 600 mil iterações, salt aleatório, limite de tentativas por processo e sessão de 12h. Em Sobre o app há Sair. A privacidade nativa do Streamlit continua necessária.
- Estado atual e manifesto anterior são retidos; objetos órfãos antigos são removidos após um dia para limitar espaço. Isso não substitui backups baixados pelo usuário.

## Limites do plano gratuito

O Streamlit pode hibernar e o Supabase pode pausar projetos pouco ativos. Ao voltar, pode ser necessário aguardar a inicialização ou reativar o projeto no painel. Não há promessa de disponibilidade contínua. O plano Supabase Free informa 500 MB de banco e não inclui backups automáticos. Baixe backups periodicamente e acompanhe a cota no painel; não habilite um plano pago para resolver cotas sem decidir isso conscientemente.

Arquivos individuais acima de 64 MB e conjuntos acima de 512 MB são recusados com preservação dos dados. PDFs, Planner HTML, exportações e registros permanecem no armazenamento privado, fora do GitHub.

Referências: https://supabase.com/pricing ; https://supabase.com/docs/guides/platform/free-project-pausing ; https://docs.streamlit.io/deploy/streamlit-community-cloud/get-started/trust-and-security .
