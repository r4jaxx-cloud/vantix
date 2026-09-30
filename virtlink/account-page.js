import {createClient} from '@supabase/supabase-js';
import {accountService} from './account-service.js';
const $=s=>document.querySelector(s);
const client=createClient('https://hnoqhdqnvvndyipcoudi.supabase.co','sb_publishable_pqG8y-tgBKvio5KFlS1PSQ_DdTc1w03',{
  auth:{storage:sessionStorage,storageKey:'virtlink-test-auth-v1',persistSession:true,autoRefreshToken:true,detectSessionInUrl:false}
});
const service=accountService(client);
// Show validation beside each field, and focus the first error on submit.
for(const form of document.querySelectorAll('.accountShell form')){
  const fields=[...form.querySelectorAll('input,textarea')];
  const errors=new Map();
  for(const field of fields){
    const label=field.closest('label');
    const name=label?.firstChild.textContent.trim()||field.name;
    const error=document.createElement('small');
    error.id=form.id+'-'+field.name+'-error';error.hidden=true;
    error.style.color='#ffb4b4';error.setAttribute('aria-live','polite');
    field.after(error);errors.set(field,error);
    field.setAttribute('aria-describedby', [field.getAttribute('aria-describedby'),error.id].filter(Boolean).join(' '));
    if(field.required&&label){
      label.firstChild.textContent+=' (required)';
    }
    const validate=()=>{
      field.setCustomValidity('');
      if(field.required&&!field.value.trim())field.setCustomValidity('Please enter your '+name.toLowerCase()+'.');
      let message=field.validationMessage;
      if(field.validity.patternMismatch&&field.name==='username')message='Use 3–30 lowercase letters, numbers or underscores, starting with a letter.';
      if(field.validity.patternMismatch&&field.name==='code')message='Enter the six-digit code from your authenticator.';
      error.textContent=message;error.hidden=!message;
      if(message){field.setAttribute('aria-invalid','true');field.style.borderColor='#ff8d8d';}
      else{field.removeAttribute('aria-invalid');field.style.removeProperty('border-color');}
      return !message;
    };
    field.addEventListener('input',()=>{if(field.hasAttribute('aria-invalid'))validate();});
    field.addEventListener('blur',()=>{if(field.value||field.hasAttribute('aria-invalid'))validate();});
    field.validateAccountField=validate;
  }
  form.noValidate=true;
  form.addEventListener('submit',event=>{
    const invalid=fields.filter(field=>!field.validateAccountField());
    if(invalid.length){event.preventDefault();event.stopImmediatePropagation();invalid[0].focus();}
  },true);
  form.addEventListener('reset',()=>{
    for(const field of fields){field.setCustomValidity('');field.removeAttribute('aria-invalid');field.style.removeProperty('border-color');errors.get(field).hidden=true;errors.get(field).textContent='';}
  });
}

let captchaToken='',widgetId=null,factorId=null,busy=false,revision=0;
function status(text){$('#accountStatus').textContent=text;}
function show(panel){for(const id of ['signinPanel','mfaPanel','profilePanel']) $('#'+id).hidden=id!==panel;}
function clearPrivate(){factorId=null;$('#savedProfile').reset();$('#mfaForm').reset();$('#mfaSecret').textContent='';$('#mfaQr').removeAttribute('src');$('#enrollDetails').hidden=true;$('#mfaForm').hidden=true;}
function resetCaptcha(){captchaToken='';if(window.turnstile&&widgetId!==null)window.turnstile.reset(widgetId);}
function humanCheck(){
  if(window.turnstile&&widgetId===null)widgetId=window.turnstile.render('#humanCheck',{
    sitekey:'0x4AAAAAAFJYFDkwLT_FJO_L',theme:'dark',callback:t=>{captchaToken=t;},
    'expired-callback':()=>{captchaToken='';},'error-callback':()=>{captchaToken='';status('Human check could not load. Refresh and try again.');}
  });
}
async function refresh(){
  const current=revision;
  clearPrivate();
  const {data,error}=await client.auth.getSession();
  if(error)throw error;
  if(!data.session){show('signinPanel');$('#accountLogout').hidden=true;humanCheck();status('Sign in with your existing test account.');return;}
  await service.user();$('#accountLogout').hidden=false;
  const assurance=await client.auth.mfa.getAuthenticatorAssuranceLevel();if(assurance.error)throw assurance.error;
  if(assurance.data.currentLevel==='aal2'){
    const row=await service.load();if(current!==revision)return;show('profilePanel');
    if(row)for(const el of $('#savedProfile').elements)if(el.name&&row[el.name]!=null)el.value=row[el.name];
    status('Email confirmed · Authenticator verified');return;
  }
  const factors=await client.auth.mfa.listFactors();if(factors.error)throw factors.error;
  if(current!==revision)return;
  factorId=factors.data.totp.find(f=>f.status==='verified')?.id??null;
  $('#enrollButton').hidden=Boolean(factorId);$('#mfaForm').hidden=!factorId;
  show('mfaPanel');status(factorId?'Enter your authenticator code.':'Set up an authenticator to continue.');
}
async function run(work){
  if(busy)return;busy=true;const current=revision;
  document.querySelectorAll('button').forEach(b=>b.disabled=true);
  try{await work();}catch(error){if(current===revision)status(error.message==='Complete the human check first.'?error.message:'Could not complete this step. Check your details and connection, then try again.');}
  finally{busy=false;document.querySelectorAll('button').forEach(b=>b.disabled=false);}
}
$('#accountLogin').addEventListener('submit',e=>{e.preventDefault();run(async()=>{
  const form=e.currentTarget,data=new FormData(form);status('Signing in…');
  try{await service.signIn(String(data.get('email')).trim(),String(data.get('password')),captchaToken);await refresh();}
  finally{form.elements.password.value='';resetCaptcha();}
});});
$('#enrollButton').addEventListener('click',()=>run(async()=>{
  const existing=await client.auth.mfa.listFactors();if(existing.error)throw existing.error;
  for(const factor of existing.data.all)if(factor.status==='unverified'&&factor.friendly_name==='VIRTLINK test authenticator'){
    const removed=await client.auth.mfa.unenroll({factorId:factor.id});if(removed.error)throw removed.error;
  }
  const result=await client.auth.mfa.enroll({factorType:'totp',friendlyName:'VIRTLINK test authenticator',issuer:'VIRTLINK'});
  if(result.error)throw result.error;factorId=result.data.id;
  const qr=result.data.totp.qr_code;
  $('#mfaQr').src=qr.startsWith('data:image/svg+xml')?qr:'data:image/svg+xml;charset=utf-8,'+encodeURIComponent(qr);
  $('#mfaSecret').textContent=result.data.totp.secret;$('#enrollDetails').hidden=false;$('#mfaForm').hidden=false;$('#enrollButton').hidden=true;
  status('Add the authenticator, then enter its six-digit code.');
}));
$('#mfaForm').addEventListener('submit',e=>{e.preventDefault();run(async()=>{
  if(!factorId)throw new Error('No factor');
  const code=String(new FormData(e.currentTarget).get('code')).trim();
  const result=await client.auth.mfa.challengeAndVerify({factorId,code});if(result.error)throw result.error;
  await refresh();
});});
$('#savedProfile').addEventListener('submit',e=>{e.preventDefault();run(async()=>{
  await service.save(Object.fromEntries(new FormData(e.currentTarget)));status('Your profile is saved privately in VIRTLINK.');
});});
$('#accountLogout').addEventListener('click',()=>run(async()=>{await service.signOut();clearPrivate();await refresh();}));
client.auth.onAuthStateChange(event=>{if(event==='SIGNED_OUT'){
  revision++;clearPrivate();show('signinPanel');$('#accountLogout').hidden=true;status('Signed out.');humanCheck();
}});
const script=document.createElement('script');script.src='https://challenges.cloudflare.com/turnstile/v0/api.js?render=explicit';script.async=true;script.onload=humanCheck;script.onerror=()=>status('Human check could not load. Refresh and try again.');document.head.append(script);
run(refresh);
