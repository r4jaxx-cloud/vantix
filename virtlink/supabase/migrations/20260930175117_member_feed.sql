-- Member-visible posts; author identity is copied from the saved profile by the server.
create table public.virtlink_posts (
 id uuid primary key default gen_random_uuid(),
 author_id uuid not null references auth.users(id) on delete cascade,
 author_name text not null,
 author_username text not null,
 body text not null check(char_length(btrim(body)) between 1 and 2000),
 created_at timestamptz not null default now()
);
create index virtlink_posts_feed_idx on public.virtlink_posts(created_at desc,id desc);
create index virtlink_posts_author_idx on public.virtlink_posts(author_id,created_at desc);
alter table public.virtlink_posts enable row level security;
revoke all on public.virtlink_posts from public,anon,authenticated;
grant select,delete on public.virtlink_posts to authenticated;
grant insert(author_id,body) on public.virtlink_posts to authenticated;
create policy posts_member_read on public.virtlink_posts for select to authenticated
 using((select virtlink_private.profile_ready()));
create policy posts_owner_insert on public.virtlink_posts for insert to authenticated
 with check(author_id=(select auth.uid()) and (select virtlink_private.profile_ready()));
create policy posts_owner_delete on public.virtlink_posts for delete to authenticated
 using(author_id=(select auth.uid()) and (select virtlink_private.profile_ready()));
create function virtlink_private.prepare_post() returns trigger
language plpgsql security invoker set search_path='' as $$
begin
 if new.author_id is distinct from auth.uid() or not virtlink_private.profile_ready() then
  raise exception 'Confirmed account required' using errcode='42501';
 end if;
 perform pg_catalog.pg_advisory_xact_lock(pg_catalog.hashtextextended(new.author_id::text,0));
 if (select count(*) from public.virtlink_posts where author_id=new.author_id and created_at>now()-interval '1 minute')>=5
 or (select count(*) from public.virtlink_posts where author_id=new.author_id and created_at>now()-interval '1 day')>=50 then
  raise exception 'Posting limit reached. Try again later.' using errcode='P0001';
 end if;
 select display_name,username into strict new.author_name,new.author_username
 from public.virtlink_profiles where user_id=new.author_id;
 new.body=btrim(new.body);
 return new;
end;
$$;
revoke all on function virtlink_private.prepare_post() from public,anon,authenticated;
create trigger prepare_member_post before insert on public.virtlink_posts
 for each row execute function virtlink_private.prepare_post();
