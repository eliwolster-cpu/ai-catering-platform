-- Advisory conversion probability written by the offline scoring job (backend/ml/score.py).
-- Never used to compute prices or quotations.

alter table public.leads
  add column conversion_score numeric(5,4) check (conversion_score between 0 and 1),
  add column scored_at timestamptz;

create index leads_conversion_score_idx on public.leads (conversion_score desc nulls last);
