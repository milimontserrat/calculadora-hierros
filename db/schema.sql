-- Schema para Calculadora de Hierros.
-- Correr una sola vez en el SQL Editor de Supabase.
-- Si ya existe, eliminá las tablas antes de volver a correrlo:
--   drop table if exists elements; drop table if exists projects;

create extension if not exists "pgcrypto";

create table if not exists projects (
    id          uuid primary key default gen_random_uuid(),
    nombre      text not null,
    largo_barra numeric not null default 12,
    created_at  timestamptz not null default now(),
    updated_at  timestamptz not null default now()
);

create table if not exists elements (
    id                       uuid primary key default gen_random_uuid(),
    project_id               uuid not null references projects(id) on delete cascade,
    nombre                   text not null,
    phi                      int not null,
    cantidad_elementos       int not null,
    cantidad_repeticiones    int not null default 1,
    medida                   numeric not null,
    orden                    int not null
);

create index if not exists elements_project_id_idx on elements(project_id);
create index if not exists projects_updated_at_idx on projects(updated_at desc);

-- Trigger para updated_at automático
create or replace function set_updated_at()
returns trigger as $$
begin
    new.updated_at = now();
    return new;
end;
$$ language plpgsql;

drop trigger if exists projects_set_updated_at on projects;
create trigger projects_set_updated_at
    before update on projects
    for each row
    execute function set_updated_at();
