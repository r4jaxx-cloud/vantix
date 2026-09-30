-- MFA is opt-in for profiles, but enabled factors must still be challenged.
-- Verification records retain the original strict aal2 policy.
create function virtlink_private.profile_ready() returns boolean
language sql stable security definer set search_path = '' as $$
  select exists (
    select 1 from auth.users u where u.id = (select auth.uid())
      and u.email_confirmed_at is not null and not coalesce(u.is_anonymous,false)
      and (u.banned_until is null or u.banned_until <= now())
  ) and (
    coalesce((select auth.jwt()->>'aal') = 'aal2',false)
    or (coalesce((select auth.jwt()->>'aal') = 'aal1',false)
      and not exists(select 1 from auth.mfa_factors f where f.user_id=(select auth.uid()) and f.status='verified'))
  );
$$;
revoke all on function virtlink_private.profile_ready() from public, anon;
grant execute on function virtlink_private.profile_ready() to authenticated;
alter policy profiles_verified_mfa on public.virtlink_profiles
  using ((select virtlink_private.profile_ready()))
  with check ((select virtlink_private.profile_ready()));
