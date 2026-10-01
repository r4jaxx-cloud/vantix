-- Run as database owner against VIRTLINK only. All fixtures are rolled back.
begin;
select set_config('virtlink.test_a', gen_random_uuid()::text, true);
select set_config('virtlink.test_b', gen_random_uuid()::text, true);
insert into auth.users (id, email, email_confirmed_at, is_anonymous)
values (current_setting('virtlink.test_a')::uuid, 'a-' || current_setting('virtlink.test_a') || '@example.invalid', now(), false),
       (current_setting('virtlink.test_b')::uuid, 'b-' || current_setting('virtlink.test_b') || '@example.invalid', now(), false);
insert into auth.sessions(id,user_id,created_at,updated_at) values(current_setting('virtlink.test_a')::uuid,current_setting('virtlink.test_a')::uuid,now(),now()),(current_setting('virtlink.test_b')::uuid,current_setting('virtlink.test_b')::uuid,now(),now());
insert into public.virtlink_verifications (user_id)
values (current_setting('virtlink.test_a')::uuid), (current_setting('virtlink.test_b')::uuid);
do $$ begin
  begin
    update public.virtlink_verifications set status='approved',level='identity',reviewed_at=now()
      where user_id=current_setting('virtlink.test_a')::uuid;
    raise exception 'Approval without expiry permitted';
  exception when check_violation then null; end;
end $$;
select set_config('request.jwt.claims', jsonb_build_object('sub',current_setting('virtlink.test_a'),'session_id',current_setting('virtlink.test_a'),'aal','aal2','role','authenticated')::text,true);
set local role authenticated;
insert into public.virtlink_profiles (user_id,username,display_name)
values (current_setting('virtlink.test_a')::uuid, 'a_' || replace(current_setting('virtlink.test_a'),'-','')::varchar(20), 'Test A');
do $$ begin
  if (select count(*) from public.virtlink_profiles) <> 1 then raise exception 'Owner cannot read profile'; end if;
  update public.virtlink_profiles set display_name='Updated A',avatar_data='data:image/jpeg;base64,/9j/';
  if not found then raise exception 'Owner cannot update profile'; end if;
  begin
    update public.virtlink_profiles set avatar_data='data:image/svg+xml,<svg/>';
    raise exception 'Non-JPEG avatar permitted';
  exception when check_violation then null; end;
  begin
    insert into public.virtlink_profiles (user_id,username,display_name)
    values (current_setting('virtlink.test_b')::uuid,'spoofed','Spoof');
    raise exception 'Cross-user insert permitted';
  exception when insufficient_privilege then null; end;
  begin
    update public.virtlink_profiles set user_id=current_setting('virtlink.test_b')::uuid;
    raise exception 'Owner reassignment permitted';
  exception when insufficient_privilege then null; end;
  if (select count(*) from public.virtlink_verifications) <> 1 then raise exception 'Verification isolation failed'; end if;
  begin
    update public.virtlink_verifications set status='approved',level='investor',reviewed_at=now(),expires_at=now()+interval '1 year';
    raise exception 'Self-verification permitted';
  exception when insufficient_privilege then null; end;
end $$;
select set_config('request.jwt.claims',jsonb_build_object('sub',current_setting('virtlink.test_b'),'session_id',current_setting('virtlink.test_b'),'aal','aal2','role','authenticated','user_metadata',jsonb_build_object('verified',true,'role','admin'))::text,true);
do $$ begin
  if exists(select 1 from public.virtlink_profiles) then raise exception 'Other profile disclosed'; end if;
  update public.virtlink_profiles set display_name='Cross-user change';
  if found then raise exception 'Other profile changed'; end if;
end $$;
select set_config('request.jwt.claims',jsonb_build_object('sub',current_setting('virtlink.test_a'),'session_id',current_setting('virtlink.test_a'),'aal','aal1','role','authenticated')::text,true);
do $$ begin
  if not exists(select 1 from public.virtlink_profiles) then raise exception 'Optional MFA blocked profile'; end if;
  update public.virtlink_profiles set display_name='No MFA enabled';
  if not found then raise exception 'Optional MFA blocked write'; end if;
  if exists(select 1 from public.virtlink_verifications) then raise exception 'Verification MFA gate weakened'; end if;
end $$;
reset role;
insert into auth.mfa_factors(id,user_id,factor_type,status,created_at,updated_at)
values(gen_random_uuid(),current_setting('virtlink.test_a')::uuid,'totp','verified',now(),now());
set local role authenticated;
do $$ begin
  if exists(select 1 from public.virtlink_profiles) then raise exception 'MFA bypass'; end if;
  update public.virtlink_profiles set display_name='MFA bypass';
  if found then raise exception 'Write without MFA'; end if;
end $$;
reset role;
update auth.users set email_confirmed_at=null where id=current_setting('virtlink.test_a')::uuid;
select set_config('request.jwt.claims',jsonb_build_object('sub',current_setting('virtlink.test_a'),'session_id',current_setting('virtlink.test_a'),'aal','aal2','role','authenticated')::text,true);
set local role authenticated;
do $$ begin
  if exists(select 1 from public.virtlink_profiles) then raise exception 'Unverified email bypass'; end if;
end $$;
reset role;
update auth.users set email_confirmed_at=now(),banned_until=now()+interval '1 day' where id=current_setting('virtlink.test_a')::uuid;
set local role authenticated;
do $$ begin
  if exists(select 1 from public.virtlink_profiles) then raise exception 'Banned account bypass'; end if;
end $$;
reset role;
select set_config('request.jwt.claims',jsonb_build_object('sub',current_setting('virtlink.test_a'),'session_id',current_setting('virtlink.test_a'),'aal','aal2','role','authenticated')::text,true);
update auth.users set banned_until=null,email_confirmed_at=now() where id=current_setting('virtlink.test_a')::uuid;
do $$ begin if not virtlink_private.profile_ready() then raise exception 'Active session denied';end if;end $$;
delete from auth.sessions where id=current_setting('virtlink.test_a')::uuid;
set local role authenticated;
do $$ begin
 if virtlink_private.profile_ready() or virtlink_private.account_ready() then raise exception 'Revoked session retained access';end if;
end $$;
reset role;
set local role anon;
do $$ begin
  begin
    perform * from public.virtlink_profiles;
    raise exception 'Anonymous profile access';
  exception when insufficient_privilege then null; end;
  begin
    perform * from public.virtlink_verifications;
    raise exception 'Anonymous verification access';
  exception when insufficient_privilege then null; end;
end $$;
reset role;
select 'PASS: ownership, writes, self-verification, metadata forgery, MFA, email, suspension, anonymous access' as result;
rollback;
