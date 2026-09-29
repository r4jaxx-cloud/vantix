-- VIRTLINK only. Never apply to the VANTIX or another project's database.
-- Registration remains closed until email delivery, CAPTCHA and MFA UI are tested.
create schema if not exists virtlink_private;
revoke all on schema virtlink_private from public, anon, authenticated;
grant usage on schema virtlink_private to authenticated;

-- This narrowly scoped definer is needed to read Auth's protected user records.
-- No user-editable metadata controls permissions, identity or verified badges.
create function virtlink_private.account_ready() returns boolean
language sql stable security definer set search_path = '' as $$
  select coalesce((select auth.jwt()->>'aal') = 'aal2', false)
    and exists (
      select 1 from auth.users u
      where u.id = (select auth.uid())
        and u.email_confirmed_at is not null
        and not coalesce(u.is_anonymous, false)
        and (u.banned_until is null or u.banned_until <= now())
    );
$$;
revoke all on function virtlink_private.account_ready() from public, anon;
grant execute on function virtlink_private.account_ready() to authenticated;

create table public.virtlink_profiles (
  user_id uuid primary key references auth.users(id) on delete cascade,
  username text not null unique check (username ~ '^[a-z][a-z0-9_]{2,29}$'),
  display_name text not null check (char_length(btrim(display_name)) between 1 and 80),
  headline text not null default '' check (char_length(headline) <= 160),
  bio text not null default '' check (char_length(bio) <= 2000),
  location text not null default '' check (char_length(location) <= 120),
  profession text not null default '' check (char_length(profession) <= 100),
  skills text not null default '' check (char_length(skills) <= 400),
  looking_for text not null default '' check (char_length(looking_for) <= 160),
  discoverable boolean not null default false,
  created_at timestamptz not null default now()
);
alter table public.virtlink_profiles enable row level security;
revoke all on public.virtlink_profiles from public, anon, authenticated;
grant select on public.virtlink_profiles to authenticated;
grant insert (user_id, username, display_name, headline, bio, location, profession, skills, looking_for, discoverable)
  on public.virtlink_profiles to authenticated;
grant update (username, display_name, headline, bio, location, profession, skills, looking_for, discoverable)
  on public.virtlink_profiles to authenticated;
create policy profiles_owner_read on public.virtlink_profiles for select to authenticated
  using ((select auth.uid()) = user_id);
create policy profiles_owner_insert on public.virtlink_profiles for insert to authenticated
  with check ((select auth.uid()) = user_id);
create policy profiles_owner_update on public.virtlink_profiles for update to authenticated
  using ((select auth.uid()) = user_id) with check ((select auth.uid()) = user_id);
create policy profiles_verified_mfa on public.virtlink_profiles as restrictive for all to authenticated
  using ((select virtlink_private.account_ready()))
  with check ((select virtlink_private.account_ready()));

-- Reviewed status is separate from profile fields. No client writes or self-approval.
-- Evidence/documents must never be placed here or in normal profile/chat storage.
create table public.virtlink_verifications (
  user_id uuid primary key references auth.users(id) on delete cascade,
  level text not null default 'none' check (level in ('none','identity','professional','investor')),
  status text not null default 'pending' check (status in ('pending','approved','rejected','revoked')),
  reviewed_at timestamptz,
  expires_at timestamptz,
  check (status <> 'approved' or (level <> 'none' and reviewed_at is not null and expires_at > reviewed_at))
);
alter table public.virtlink_verifications enable row level security;
revoke all on public.virtlink_verifications from public, anon, authenticated;
grant select on public.virtlink_verifications to authenticated;
create policy verification_owner_read on public.virtlink_verifications for select to authenticated
  using ((select auth.uid()) = user_id and (select virtlink_private.account_ready()));

comment on table public.virtlink_profiles is 'VIRTLINK private onboarding profiles; directory publication requires a separate reviewed policy.';
comment on table public.virtlink_verifications is 'Read-only to users. Approved badges require unexpired, non-revoked server review. No reviewer workflow is enabled yet.';
