import {createClient} from '@supabase/supabase-js';
import {accountService} from './account-service.js';
const $=s=>document.querySelector(s);
const client=createClient('https://hnoqhdqnvvndyipcoudi.supabase.co','sb_publishable_pqG8y-tgBKvio5KFlS1PSQ_DdTc1w03',{
  auth:{storage:sessionStorage,storageKey:'virtlink-test-auth-v1',persistSession:true,autoRefreshToken:true,detectSessionInUrl:false}
});
const service=accountService(client);
const inlineEdit=new URLSearchParams(location.search).get('edit')==='1'&&window.parent!==window;
if(inlineEdit)document.body.classList.add('inlineProfileEditor');
function finishProfile(){if(inlineEdit)window.parent.postMessage({type:'virtlink-profile-saved'},location.origin);else location.assign('index.html#profile');}
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

let photoBitmap=null;
let captchaToken='',widgetId=null,factorId=null,busy=false,revision=0,savedRow=null,mfaEnabled=false,avatarData='',photoProcessing=false,finishSetup=false,goToProfile=false;
function status(text){$('#accountStatus').textContent=text;}
function show(panel){for(const id of ['signinPanel','mfaPanel','profilePanel','profileView','registrationPanel']) $('#'+id).hidden=id!==panel;}
function clearPrivate(){if(photoBitmap){photoBitmap.close();photoBitmap=null;}$('#photoTools').hidden=true;$('#cancelProfileEdit').hidden=true;$('#profileEditorTitle').textContent='Create your profile';avatarData='';$('#photoError').hidden=true;$('#savedPhoto').removeAttribute('src');$('#savedPhoto').hidden=true;$('#photoPreview').removeAttribute('src');$('#photoPreview').hidden=true;$('#photoPlaceholder').hidden=false;savedRow=null;$('#profileName').textContent='';$('#profileUsername').textContent='';$('#profileDetails').replaceChildren();factorId=null;$('#savedProfile').reset();$('#mfaForm').reset();$('#mfaSecret').textContent='';$('#mfaQr').removeAttribute('src');$('#enrollDetails').hidden=true;$('#mfaForm').hidden=true;}
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
  mfaEnabled=assurance.data.nextLevel==='aal2';$('#setupAuthenticator').checked=mfaEnabled;$('#setupAuthenticator').disabled=mfaEnabled;
  if(assurance.data.currentLevel==='aal2'||assurance.data.nextLevel==='aal1'){
    const row=await service.load();if(current!==revision)return;
    if(row){savedRow=row;if(goToProfile&&!inlineEdit){finishProfile();return;}renderProfile(row);if(inlineEdit)editSavedProfile();}else{show('profilePanel');status('Complete your profile. Authenticator setup is optional.');}
    return;
  }
  const factors=await client.auth.mfa.listFactors();if(factors.error)throw factors.error;
  if(current!==revision)return;
  factorId=factors.data.totp.find(f=>f.status==='verified')?.id??null;
  $('#enrollButton').hidden=Boolean(factorId);$('#mfaForm').hidden=!factorId;
  $('#cancelMfa').hidden=true;show('mfaPanel');status(factorId?'Enter your authenticator code.':'Set up an authenticator to continue.');
}
function renderProfile(row){
  savedRow=row;avatarData=row.avatar_data||'';show('profileView');$('#savedPhoto').hidden=!avatarData;if(avatarData)$('#savedPhoto').src=avatarData;
  $('#profileName').textContent=row.display_name;$('#profileUsername').textContent='@'+row.username;
  $('#profileDetails').replaceChildren();
  for(const [key,label] of Object.entries({headline:'Headline',profession:'Profession',location:'Location',skills:'Skills',looking_for:'Looking for',bio:'About you'})){
    if(!row[key])continue;
    const term=document.createElement('dt'),value=document.createElement('dd');
    term.textContent=label;value.textContent=row[key];$('#profileDetails').append(term,value);
  }
  $('#securitySummary').textContent=mfaEnabled?'Authenticator protection is enabled.':'Email and password sign-in. You can add an authenticator for extra protection.';
  $('#optionalMfa').hidden=mfaEnabled;status('Your profile');$('#profileName').focus();
}
function editSavedProfile(){
  show('profilePanel');$('#profileEditorTitle').textContent='Edit your profile';$('#cancelProfileEdit').hidden=false;for(const el of $('#savedProfile').elements)if(el.name&&savedRow?.[el.name]!=null)el.value=savedRow[el.name];
  $('#photoPreview').hidden=!avatarData;$('#photoPlaceholder').hidden=Boolean(avatarData);if(avatarData)$('#photoPreview').src=avatarData;$('#setupAuthenticator').checked=mfaEnabled;$('#setupAuthenticator').disabled=mfaEnabled;
  status('Edit your profile');$('#savedProfile').elements.username.focus();
}
$('#editProfile').addEventListener('click',editSavedProfile);
$('#cancelProfileEdit').addEventListener('click',()=>{if(inlineEdit)window.parent.postMessage({type:'virtlink-profile-cancel'},location.origin);else if(savedRow)renderProfile(savedRow);});
$('#optionalMfa').addEventListener('click',()=>{
  show('mfaPanel');$('#enrollButton').hidden=false;$('#cancelMfa').hidden=false;status('Optional authenticator setup');
});
$('#cancelMfa').addEventListener('click',()=>run(async()=>{
  if(factorId){const result=await client.auth.mfa.unenroll({factorId});if(result.error)throw result.error;}
  if(finishSetup){finishProfile();return;}await refresh();
}));
async function run(work){
  if(busy)return;busy=true;const current=revision;
  document.querySelectorAll('button').forEach(b=>b.disabled=true);
  try{await work();}catch(error){if(current===revision)status(error.message==='Complete the human check first.'?error.message:'Could not complete this step. Check your details and connection, then try again.');}
  finally{busy=false;document.querySelectorAll('button').forEach(b=>b.disabled=false);}
}
$('#accountLogin').addEventListener('submit',e=>{e.preventDefault();run(async()=>{
  const form=e.currentTarget,data=new FormData(form);status('Signing in…');
  try{await service.signIn(String(data.get('email')).trim(),String(data.get('password')),captchaToken);goToProfile=true;await refresh();}
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
  if(finishSetup){finishProfile();return;}await refresh();
});});
$('#savedProfile').addEventListener('submit',e=>{e.preventDefault();run(async()=>{
  if(photoProcessing){status('Wait for your photo to finish loading.');return;}
  if(!avatarData&&!savedRow){$('#photoError').textContent='Please add a profile picture.';$('#photoError').hidden=false;$('#photoInput').setAttribute('aria-invalid','true');$('#photoInput').focus();return;}
  const addSecurity=$('#setupAuthenticator').checked&&!mfaEnabled;
  const row=await service.save({...Object.fromEntries(new FormData(e.currentTarget)),avatar_data:avatarData});
  if(addSecurity){savedRow=row;finishSetup=true;show('mfaPanel');$('#enrollButton').hidden=false;$('#cancelMfa').hidden=false;status('Profile saved. Set up your optional authenticator.');}
  else finishProfile();
});});
$('#accountLogout').addEventListener('click',()=>run(async()=>{await service.signOut();clearPrivate();await refresh();}));
client.auth.onAuthStateChange(event=>{if(event==='SIGNED_OUT'){
  revision++;clearPrivate();show('signinPanel');$('#accountLogout').hidden=true;status('Signed out.');humanCheck();
}});
const script=document.createElement('script');script.src='https://challenges.cloudflare.com/turnstile/v0/api.js?render=explicit';script.async=true;script.onload=humanCheck;script.onerror=()=>status('Human check could not load. Refresh and try again.');document.head.append(script);
run(async()=>{await refresh();if(location.hash==='#register'&&!$('#signinPanel').hidden){show('registrationPanel');status('Registration is currently invite-only.');}});

$('#showRegistration').addEventListener('click',()=>{show('registrationPanel');status('Registration is currently invite-only.');});
$('#backToLogin').addEventListener('click',()=>{show('signinPanel');status('Sign in with your existing test account.');});
$('#photoInput').addEventListener('change',async event=>{
 const file=event.target.files[0];if(!file)return;photoProcessing=true;$('#photoError').hidden=true;
 try{
  if(!['image/jpeg','image/png','image/webp'].includes(file.type)||file.size>10*1024*1024)throw new Error('Choose a JPG, PNG or WebP picture under 10 MB.');
  const bitmap=await createImageBitmap(file);if(photoBitmap)photoBitmap.close();photoBitmap=bitmap;
  $('#photoZoom').value='1';updatePhotoCrop();$('#photoTools').hidden=false;$('#photoInput').removeAttribute('aria-invalid');
 }catch(error){$('#photoError').textContent=error.message||'Could not read this picture. Try another file.';$('#photoError').hidden=false;}
 finally{photoProcessing=false;}
});

function updatePhotoCrop(){
 if(!photoBitmap)return;
 const canvas=document.createElement('canvas');canvas.width=canvas.height=256;
 const context=canvas.getContext('2d');context.fillStyle='#ffffff';context.fillRect(0,0,256,256);
 const side=Math.min(photoBitmap.width,photoBitmap.height)/Number($('#photoZoom').value);
 context.drawImage(photoBitmap,(photoBitmap.width-side)/2,(photoBitmap.height-side)/2,side,side,0,0,256,256);
 const result=canvas.toDataURL('image/jpeg',0.82);if(result.length>100000)throw new Error('Choose a smaller picture.');
 avatarData=result;$('#photoPreview').src=result;$('#photoPreview').hidden=false;$('#photoPlaceholder').hidden=true;
}
$('#photoZoom').addEventListener('input',updatePhotoCrop);

$('#signoutAllDevices').addEventListener('click',()=>{
 if(!confirm('Sign out on every device, including this one?'))return;
 run(async()=>{await service.signOutAll();revision++;clearPrivate();await refresh();status('All sessions signed out. Sign in again to continue.');});
});
