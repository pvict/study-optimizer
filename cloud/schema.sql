-- Execute no SQL Editor do SEU projeto Supabase gratuito.
-- Nenhuma tabela de estudo é exposta: somente snapshots privados do app.
begin;
create schema if not exists osler_private;
revoke all on schema osler_private from public, anon, authenticated;

create table if not exists osler_private.workspace (
  id boolean primary key default true check (id),
  revision bigint not null default 0,
  manifest jsonb not null default '{}'::jsonb,
  previous_manifest jsonb not null default '{}'::jsonb,
  owner uuid,
  lease_until timestamptz,
  updated_at timestamptz not null default now()
);
insert into osler_private.workspace(id) values(true) on conflict do nothing;
create table if not exists osler_private.objects (
  digest text primary key check (digest ~ '^[0-9a-f]{64}$'),
  content text not null check (length(content) <= 90000000),
  created_at timestamptz not null default now()
);
alter table osler_private.workspace enable row level security;
alter table osler_private.objects enable row level security;
revoke all on all tables in schema osler_private from public, anon, authenticated;

create or replace function public.osler_acquire(p_owner uuid)
returns jsonb language plpgsql security definer set search_path = '' as $$
declare w osler_private.workspace;
begin
  select * into w from osler_private.workspace where id for update;
  if w.owner is not null and w.owner <> p_owner and w.lease_until > clock_timestamp() then
    raise exception 'Workspace ocupado' using errcode = '40001';
  end if;
  update osler_private.workspace set owner=p_owner, lease_until=clock_timestamp()+interval '5 minutes' where id;
  return jsonb_build_object('revision',w.revision,'manifest',w.manifest);
end $$;

create or replace function public.osler_release(p_owner uuid)
returns void language sql security definer set search_path = '' as $$
  update osler_private.workspace set owner=null, lease_until=null where id and owner=p_owner;
$$;

create or replace function public.osler_put(p_owner uuid, p_digest text, p_content text)
returns void language plpgsql security definer set search_path = '' as $$
begin
  perform 1 from osler_private.workspace where id and owner=p_owner and lease_until>clock_timestamp() for update;
  if not found then raise exception 'Lease expirado' using errcode='40001'; end if;
  insert into osler_private.objects(digest,content) values(p_digest,p_content) on conflict do nothing;
  if exists(select 1 from osler_private.objects where digest=p_digest and content<>p_content) then
    raise exception 'Objeto divergente' using errcode='22000';
  end if;
end $$;

create or replace function public.osler_get(p_digest text)
returns text language sql stable security definer set search_path = '' as $$
  select content from osler_private.objects where digest=p_digest;
$$;

create or replace function public.osler_commit(p_owner uuid,p_revision bigint,p_manifest jsonb)
returns bigint language plpgsql security definer set search_path = '' as $$
declare w osler_private.workspace;
begin
  select * into w from osler_private.workspace where id for update;
  if w.owner is distinct from p_owner or w.lease_until<=clock_timestamp() or w.revision<>p_revision then
    raise exception 'Versao ou lease mudou' using errcode='40001';
  end if;
  if jsonb_typeof(p_manifest)<>'object' or not (p_manifest ? 'osler.sqlite3') then
    raise exception 'Manifesto invalido';
  end if;
  if exists(select 1 from jsonb_each_text(p_manifest) m
            where not exists(select 1 from osler_private.objects o where o.digest=m.value)) then
    raise exception 'Upload incompleto';
  end if;
  update osler_private.workspace set revision=revision+1,previous_manifest=manifest,
    manifest=p_manifest,updated_at=clock_timestamp() where id;
  -- Retém estado atual e anterior; elimina somente objetos órfãos antigos.
  delete from osler_private.objects o where o.created_at<now()-interval '1 day'
    and not exists(select 1 from jsonb_each_text(p_manifest) m where m.value=o.digest)
    and not exists(select 1 from jsonb_each_text(w.manifest) m where m.value=o.digest);
  return w.revision+1;
end $$;

revoke all on function public.osler_acquire(uuid) from public,anon,authenticated;
revoke all on function public.osler_release(uuid) from public,anon,authenticated;
revoke all on function public.osler_put(uuid,text,text) from public,anon,authenticated;
revoke all on function public.osler_get(text) from public,anon,authenticated;
revoke all on function public.osler_commit(uuid,bigint,jsonb) from public,anon,authenticated;
grant execute on function public.osler_acquire(uuid) to service_role;
grant execute on function public.osler_release(uuid) to service_role;
grant execute on function public.osler_put(uuid,text,text) to service_role;
grant execute on function public.osler_get(text) to service_role;
grant execute on function public.osler_commit(uuid,bigint,jsonb) to service_role;
commit;
notify pgrst, 'reload schema';
