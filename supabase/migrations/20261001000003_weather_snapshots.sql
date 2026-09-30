-- Every weather result the backend produces, whatever its source.
--   source      = live (Open-Meteo, NOT IMD) | cached (a re-served live row) | demo | unavailable
--   observed_at = the time the data describes; fetched_at = when we produced this result
--   error       = why the live source was not used (null when source = live)
-- Cached fallbacks read the latest source = 'live' row for the district.

create table weather_snapshots (
  id                        uuid primary key default gen_random_uuid(),
  district                  text not null,
  source                    text not null check (source in ('live', 'cached', 'demo', 'unavailable')),
  provider                  text,
  observed_at               timestamptz,
  fetched_at                timestamptz not null,
  stale                     boolean not null default false,
  temperature_c             real,
  humidity_pct              real,
  precipitation_mm          real,
  rain_next_24h_mm          real,
  rain_probability_max_pct  real,
  wind_speed_kmh            real,
  error                     text,
  created_at                timestamptz not null default now()
);

create index weather_snapshots_live_lookup_idx
  on weather_snapshots (district, observed_at desc) where source = 'live';

alter table weather_snapshots enable row level security;

-- District weather is not personal data; any signed-in user may read it. Writes: backend only.
create policy weather_snapshots_read on weather_snapshots
  for select to authenticated using (true);
