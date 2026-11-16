-- Leads and their activity history. Owner-only data: RLS enabled, no public policies.
-- Access goes through the backend (service role, server-side only).

create table public.leads (
  id uuid primary key default gen_random_uuid(),
  name text not null check (char_length(name) between 1 and 120),
  phone text not null,
  email text,
  event_type text not null
    check (event_type in ('wedding','corporate','birthday','bar_mitzvah','private','other')),
  event_date date,
  guest_count integer check (guest_count between 1 and 5000),
  budget_estimate integer check (budget_estimate >= 0),
  source text not null
    check (source in ('referral','website','social','phone','ads','returning')),
  status text not null default 'new'
    check (status in ('new','contacted','quote_sent','won','lost')),
  first_response_minutes integer check (first_response_minutes >= 0),
  interaction_count integer not null default 0 check (interaction_count >= 0),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index leads_status_idx on public.leads (status);
create index leads_created_at_idx on public.leads (created_at desc);

create table public.lead_events (
  id uuid primary key default gen_random_uuid(),
  lead_id uuid not null references public.leads (id) on delete cascade,
  kind text not null check (kind in ('status_change','call','message','meeting','quote_sent')),
  note text,
  created_at timestamptz not null default now()
);

create index lead_events_lead_idx on public.lead_events (lead_id, created_at);

alter table public.leads enable row level security;
alter table public.lead_events enable row level security;
