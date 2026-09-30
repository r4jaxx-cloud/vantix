import {createClient} from '@supabase/supabase-js';
import {accountService} from './account-service.js';
const client=createClient('https://hnoqhdqnvvndyipcoudi.supabase.co','sb_publishable_pqG8y-tgBKvio5KFlS1PSQ_DdTc1w03',{
  auth:{storage:sessionStorage,storageKey:'virtlink-test-auth-v1',persistSession:true,autoRefreshToken:true,detectSessionInUrl:false}
});
const service=accountService(client);
let revision=0;
function publish(profile){window.dispatchEvent(new CustomEvent('virtlink-account',{detail:profile}));}
async function refresh(){
  const current=++revision;
  try{
    const {data,error}=await client.auth.getSession();if(error)throw error;
    if(!data.session){if(current===revision)publish(null);return;}
    const profile=await service.load();
    if(current===revision)publish(profile);
  }catch{if(current===revision){publish(null);window.dispatchEvent(new CustomEvent('virtlink-account-error'));}}
}
client.auth.onAuthStateChange(event=>{
  if(event==='SIGNED_OUT'){revision++;publish(null);}
  else if(['SIGNED_IN','TOKEN_REFRESHED','USER_UPDATED','MFA_CHALLENGE_VERIFIED'].includes(event))setTimeout(refresh,0);
});
window.addEventListener('virtlink-signout',async()=>{
  try{await service.signOut();revision++;publish(null);}
  catch{window.dispatchEvent(new CustomEvent('virtlink-account-error'));}
});
window.addEventListener('pageshow',refresh);
