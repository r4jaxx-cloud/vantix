create or replace function virtlink_private.account_ready() returns boolean
language sql stable security definer set search_path = '' as $$
  select coalesce((select auth.jwt()->>'aal') = 'aal2', false)
    and exists (
      select 1 from auth.users u
      where u.id = (select auth.uid()) and exists(select 1 from auth.sessions s where s.user_id=u.id and s.id::text=(select auth.jwt()->>'session_id') and (s.not_after is null or s.not_after>now()))
        and u.email_confirmed_at is not null
        and not coalesce(u.is_anonymous, false)
        and (u.banned_until is null or u.banned_until <= now())
    );
$$;

create or replace function virtlink_private.profile_ready() returns boolean
language sql stable security definer set search_path = '' as $$
  select exists (
    select 1 from auth.users u where u.id = (select auth.uid()) and exists(select 1 from auth.sessions s where s.user_id=u.id and s.id::text=(select auth.jwt()->>'session_id') and (s.not_after is null or s.not_after>now()))
      and u.email_confirmed_at is not null and not coalesce(u.is_anonymous,false)
      and (u.banned_until is null or u.banned_until <= now())
  ) and (
    coalesce((select auth.jwt()->>'aal') = 'aal2',false)
    or (coalesce((select auth.jwt()->>'aal') = 'aal1',false)
      and not exists(select 1 from auth.mfa_factors f where f.user_id=(select auth.uid()) and f.status='verified'))
  );
$$;
