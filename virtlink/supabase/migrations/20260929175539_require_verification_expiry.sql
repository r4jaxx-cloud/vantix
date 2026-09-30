alter table public.virtlink_verifications add constraint approved_requires_expiry check (status <> 'approved' or expires_at is not null);
