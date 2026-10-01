create table public.virtlink_likes (
 post_id uuid not null references public.virtlink_posts(id) on delete cascade,
 user_id uuid not null references auth.users(id) on delete cascade,
 primary key(post_id,user_id)
);
create index virtlink_likes_user_idx on public.virtlink_likes(user_id);
alter table public.virtlink_likes enable row level security;
revoke all on public.virtlink_likes from public,anon,authenticated;
grant select,insert,delete on public.virtlink_likes to authenticated;
create policy likes_read on public.virtlink_likes for select to authenticated using((select virtlink_private.profile_ready()));
create policy likes_insert on public.virtlink_likes for insert to authenticated with check(user_id=(select auth.uid()) and (select virtlink_private.profile_ready()));
create policy likes_delete on public.virtlink_likes for delete to authenticated using(user_id=(select auth.uid()) and (select virtlink_private.profile_ready()));
create table public.virtlink_comments (
 id uuid primary key default gen_random_uuid(),
 post_id uuid not null references public.virtlink_posts(id) on delete cascade,
 author_id uuid not null references auth.users(id) on delete cascade,
 author_name text not null,
 author_username text not null,
 body text not null check(char_length(btrim(body)) between 1 and 1000),
 created_at timestamptz not null default now()
);
create index virtlink_comments_post_idx on public.virtlink_comments(post_id,created_at desc,id desc);
create index virtlink_comments_author_idx on public.virtlink_comments(author_id,created_at desc);
alter table public.virtlink_comments enable row level security;
revoke all on public.virtlink_comments from public,anon,authenticated;
grant select,delete on public.virtlink_comments to authenticated;
grant insert(post_id,author_id,body) on public.virtlink_comments to authenticated;
create policy comments_read on public.virtlink_comments for select to authenticated using((select virtlink_private.profile_ready()));
create policy comments_insert on public.virtlink_comments for insert to authenticated with check(author_id=(select auth.uid()) and (select virtlink_private.profile_ready()));
create policy comments_delete on public.virtlink_comments for delete to authenticated using(author_id=(select auth.uid()) and (select virtlink_private.profile_ready()));
create function virtlink_private.prepare_comment() returns trigger
language plpgsql security invoker set search_path='' as $$
begin
 if new.author_id is distinct from auth.uid() or not virtlink_private.profile_ready() then
  raise exception 'Confirmed account required' using errcode='42501';
 end if;
 perform pg_catalog.pg_advisory_xact_lock(pg_catalog.hashtextextended(new.author_id::text,1));
 if (select count(*) from public.virtlink_comments where author_id=new.author_id and created_at>now()-interval '1 minute')>=10 then
  raise exception 'Commenting limit reached. Try again later.' using errcode='P0001';
 end if;
 select display_name,username into strict new.author_name,new.author_username from public.virtlink_profiles where user_id=new.author_id;
 new.body=btrim(new.body);return new;
end;
$$;
revoke all on function virtlink_private.prepare_comment() from public,anon,authenticated;
create trigger prepare_member_comment before insert on public.virtlink_comments for each row execute function virtlink_private.prepare_comment();
create function public.virtlink_member_feed() returns table(
 id uuid,author_id uuid,author_name text,author_username text,body text,created_at timestamptz,
 like_count bigint,comment_count bigint,liked boolean
) language sql stable security invoker set search_path='' as $$
 select p.id,p.author_id,p.author_name,p.author_username,p.body,p.created_at,
 (select count(*) from public.virtlink_likes l where l.post_id=p.id),
 (select count(*) from public.virtlink_comments c where c.post_id=p.id),
 exists(select 1 from public.virtlink_likes l where l.post_id=p.id and l.user_id=(select auth.uid()))
 from public.virtlink_posts p order by p.created_at desc,p.id desc limit 50;
$$;
revoke all on function public.virtlink_member_feed() from public,anon;
grant execute on function public.virtlink_member_feed() to authenticated;
