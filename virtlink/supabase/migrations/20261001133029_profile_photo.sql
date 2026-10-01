alter table public.virtlink_profiles add column avatar_data text not null default ''
 check(avatar_data='' or (octet_length(avatar_data)<=100000 and avatar_data ~ '^data:image/jpeg;base64,[A-Za-z0-9+/=]+$'));
grant insert(avatar_data),update(avatar_data) on public.virtlink_profiles to authenticated;
