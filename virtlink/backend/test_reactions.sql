begin;
select set_config('virtlink.feed_a',gen_random_uuid()::text,true);
select set_config('virtlink.feed_b',gen_random_uuid()::text,true);
insert into auth.users(id,email,email_confirmed_at,is_anonymous)
select current_setting('virtlink.feed_a')::uuid,current_setting('virtlink.feed_a')||'@example.invalid',now(),false
union all select current_setting('virtlink.feed_b')::uuid,current_setting('virtlink.feed_b')||'@example.invalid',now(),false;
insert into auth.sessions(id,user_id,created_at,updated_at) values(current_setting('virtlink.feed_a')::uuid,current_setting('virtlink.feed_a')::uuid,now(),now()),(current_setting('virtlink.feed_b')::uuid,current_setting('virtlink.feed_b')::uuid,now(),now());
insert into public.virtlink_profiles(user_id,username,display_name)
values(current_setting('virtlink.feed_a')::uuid,'a_'||left(replace(current_setting('virtlink.feed_a'),'-',''),20),'Author A'),
(current_setting('virtlink.feed_b')::uuid,'b_'||left(replace(current_setting('virtlink.feed_b'),'-',''),20),'Author B');
select set_config('request.jwt.claims',jsonb_build_object('sub',current_setting('virtlink.feed_a'),'session_id',current_setting('virtlink.feed_a'),'aal','aal1','role','authenticated')::text,true);
set local role authenticated;
insert into public.virtlink_posts(author_id,body) values(current_setting('virtlink.feed_a')::uuid,'First post');
select set_config('virtlink.feed_post',(select id::text from public.virtlink_posts where author_id=current_setting('virtlink.feed_a')::uuid),true);
do $$ begin
 if (select author_name from public.virtlink_posts where id=current_setting('virtlink.feed_post')::uuid)<>'Author A' then raise exception 'Author identity mismatch';end if;
 begin
  insert into public.virtlink_posts(author_id,body) values(current_setting('virtlink.feed_b')::uuid,'Spoof');
  raise exception 'Spoofed author permitted';
 exception when insufficient_privilege then null;end;
 begin
  insert into public.virtlink_posts(author_id,body,author_name) values(current_setting('virtlink.feed_a')::uuid,'Spoof','Another person');
  raise exception 'Spoofed author name permitted';
 exception when insufficient_privilege then null;end;
 begin
  update public.virtlink_posts set body='Edited';raise exception 'Ungrantable edit permitted';
 exception when insufficient_privilege then null;end;
end $$;
select set_config('request.jwt.claims',jsonb_build_object('sub',current_setting('virtlink.feed_b'),'session_id',current_setting('virtlink.feed_b'),'aal','aal1','role','authenticated')::text,true);
do $$ begin
 if not exists(select 1 from public.virtlink_posts where id=current_setting('virtlink.feed_post')::uuid) then raise exception 'Member cannot read feed';end if;
 delete from public.virtlink_posts where id=current_setting('virtlink.feed_post')::uuid;
 if found then raise exception 'Other member deleted post';end if;
 if exists(select 1 from public.virtlink_profiles where user_id=current_setting('virtlink.feed_a')::uuid) then raise exception 'Private profile disclosed';end if;
end $$;
insert into public.virtlink_likes(post_id,user_id) values(current_setting('virtlink.feed_post')::uuid,current_setting('virtlink.feed_b')::uuid);
insert into public.virtlink_comments(post_id,author_id,body) values(current_setting('virtlink.feed_post')::uuid,current_setting('virtlink.feed_b')::uuid,'Member reply');
do $$ begin
 if not exists(select 1 from public.virtlink_member_feed() where id=current_setting('virtlink.feed_post')::uuid and like_count=1 and comment_count=1 and liked) then raise exception 'Feed counts incorrect';end if;
 begin
  insert into public.virtlink_likes(post_id,user_id) values(current_setting('virtlink.feed_post')::uuid,current_setting('virtlink.feed_b')::uuid);
  raise exception 'Duplicate like allowed';
 exception when unique_violation then null;end;
 begin
  insert into public.virtlink_likes(post_id,user_id) values(current_setting('virtlink.feed_post')::uuid,current_setting('virtlink.feed_a')::uuid);
  raise exception 'Spoofed like';
 exception when insufficient_privilege then null;end;
 begin
  insert into public.virtlink_comments(post_id,author_id,body) values(current_setting('virtlink.feed_post')::uuid,current_setting('virtlink.feed_a')::uuid,'Spoof');
  raise exception 'Spoofed comment';
 exception when insufficient_privilege then null;end;
end $$;
select set_config('request.jwt.claims',jsonb_build_object('sub',current_setting('virtlink.feed_a'),'session_id',current_setting('virtlink.feed_a'),'aal','aal1','role','authenticated')::text,true);
do $$ begin
 delete from public.virtlink_comments where post_id=current_setting('virtlink.feed_post')::uuid;
 if found then raise exception 'Other author comment deletion allowed';end if;
 delete from public.virtlink_likes where post_id=current_setting('virtlink.feed_post')::uuid;
 if found then raise exception 'Other member like deletion allowed';end if;
end $$;
select set_config('request.jwt.claims',jsonb_build_object('sub',current_setting('virtlink.feed_b'),'session_id',current_setting('virtlink.feed_b'),'aal','aal1','role','authenticated')::text,true);
delete from public.virtlink_likes where post_id=current_setting('virtlink.feed_post')::uuid;
delete from public.virtlink_comments where post_id=current_setting('virtlink.feed_post')::uuid;
do $$ begin
 if exists(select 1 from public.virtlink_member_feed() where id=current_setting('virtlink.feed_post')::uuid and (like_count<>0 or comment_count<>0 or liked)) then raise exception 'Owner removal failed';end if;
end $$;
reset role;
insert into auth.mfa_factors(id,user_id,factor_type,status,created_at,updated_at)
values(gen_random_uuid(),current_setting('virtlink.feed_b')::uuid,'totp','verified',now(),now());
set local role authenticated;
do $$ begin
 if exists(select 1 from public.virtlink_posts where id=current_setting('virtlink.feed_post')::uuid) then raise exception 'Enabled MFA bypassed';end if;
end $$;
select set_config('request.jwt.claims',jsonb_build_object('sub',current_setting('virtlink.feed_a'),'session_id',current_setting('virtlink.feed_a'),'aal','aal1','role','authenticated')::text,true);
do $$ begin
 for i in 1..4 loop
  insert into public.virtlink_posts(author_id,body) values(current_setting('virtlink.feed_a')::uuid,'Rate test');
 end loop;
 begin
  insert into public.virtlink_posts(author_id,body) values(current_setting('virtlink.feed_a')::uuid,'Too many');
  raise exception 'Rate guard failed';
 exception when raise_exception then
  if sqlerrm<>'Posting limit reached. Try again later.' then raise;end if;
 end;
 delete from public.virtlink_posts where id=current_setting('virtlink.feed_post')::uuid;
 if not found then raise exception 'Owner could not delete';end if;
end $$;
reset role;
select set_config('request.jwt.claims',jsonb_build_object('sub',current_setting('virtlink.feed_a'),'session_id',current_setting('virtlink.feed_a'),'aal','aal2','role','authenticated')::text,true);
update auth.users set banned_until=null,email_confirmed_at=now() where id=current_setting('virtlink.feed_a')::uuid;
do $$ begin if not virtlink_private.profile_ready() then raise exception 'Active session denied';end if;end $$;
delete from auth.sessions where id=current_setting('virtlink.feed_a')::uuid;
set local role authenticated;
do $$ begin
 if virtlink_private.profile_ready() or virtlink_private.account_ready() then raise exception 'Revoked session retained access';end if;
end $$;
reset role;
set local role anon;
do $$ begin
 begin
  perform * from public.virtlink_posts;raise exception 'Anonymous feed access';
 exception when insufficient_privilege then null;end;
end $$;
reset role;
select 'PASS: member feed, author integrity, private profiles, owner deletion, MFA, anonymous access, posting guard, likes and comments' as result;
rollback;
