// The SDK verifies the user; database policies independently enforce ownership/MFA.
export function accountService(client) {
  const unwrap = ({data,error}) => { if(error) throw error; return data; };
  async function user() {
    const data=unwrap(await client.auth.getUser());
    if(!data.user || !data.user.email_confirmed_at || data.user.is_anonymous) throw new Error('A confirmed account is required.');
    return data.user;
  }
  async function ready() {
    const u=await user();
    const assurance=unwrap(await client.auth.mfa.getAuthenticatorAssuranceLevel());
    if(assurance.currentLevel!=='aal2'&&assurance.nextLevel!=='aal1') throw new Error('Complete your authenticator check first.');
    return u;
  }
  const fields=['username','display_name','headline','bio','location','profession','skills','looking_for'];
  return {
    user,
    async signIn(email,password,captchaToken) {
      if(!captchaToken) throw new Error('Complete the human check first.');
      unwrap(await client.auth.signInWithPassword({email,password,options:{captchaToken}}));
      return user();
    },
    async load() {
      const u=await ready();
      return unwrap(await client.from('virtlink_profiles').select('*').eq('user_id',u.id).maybeSingle());
    },
    async save(input) {
      const u=await ready();
      const row=Object.fromEntries(fields.map(k=>[k,String(input[k]??'').trim()]));
      row.username=row.username.toLowerCase();
      const exists=unwrap(await client.from('virtlink_profiles').select('user_id').eq('user_id',u.id).maybeSingle());
      const query=exists ? client.from('virtlink_profiles').update(row).eq('user_id',u.id)
        : client.from('virtlink_profiles').insert({...row,user_id:u.id});
      return unwrap(await query.select('*').single());
    },
    async signOut() { const {error}=await client.auth.signOut({scope:'local'}); if(error) throw error; }
  };
}
