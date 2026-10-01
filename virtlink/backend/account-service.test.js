import {test} from 'node:test';
import assert from 'node:assert/strict';
import {accountService} from '../account-service.js';
function fixture({level='aal2',nextLevel='aal2',confirmed=true,anonymous=false,exists=false}={}){
  const calls=[];
  const query={select(v){calls.push(['select',v]);return this},eq(k,v){calls.push(['eq',k,v]);return this},
    async maybeSingle(){return {data:exists?{user_id:'owner'}:null}},
    insert(row){calls.push(['insert',row]);return this},update(row){calls.push(['update',row]);return this},async single(){return {data:{user_id:'owner'}}}};
  const client={auth:{getUser:async()=>({data:{user:{id:'owner',email_confirmed_at:confirmed?'date':null,is_anonymous:anonymous}}}),
    mfa:{getAuthenticatorAssuranceLevel:async()=>({data:{currentLevel:level,nextLevel}})},
    signInWithPassword:async args=>{calls.push(['login',args]);return {data:{}}},signOut:async args=>{calls.push(['logout',args]);return {error:null}}},
    from(name){calls.push(['from',name]);return query}};
  return {calls,service:accountService(client)};
}
test('missing human check never sends a password',async()=>{const f=fixture();await assert.rejects(f.service.signIn('a','secret',''));assert.equal(f.calls.length,0)});
test('human token goes to Auth',async()=>{const f=fixture();await f.service.signIn('a','secret','token');assert.equal(f.calls[0][1].options.captchaToken,'token')});
for(const setup of [{level:'aal1'},{confirmed:false},{anonymous:true}])test('profile access denied '+JSON.stringify(setup),async()=>{
  const f=fixture(setup);await assert.rejects(f.service.load());await assert.rejects(f.service.save({}));assert.equal(f.calls.length,0);
});
test('profile inserts use verified user, discard privilege fields',async()=>{
  const f=fixture();await f.service.save({user_id:'victim',username:'  Alice  ',display_name:'Alice',status:'approved',level:'investor',discoverable:true});
  const row=f.calls.find(c=>c[0]==='insert')[1];assert.equal(row.user_id,'owner');assert.equal(row.username,'alice');assert.equal(row.status,undefined);assert.equal(row.level,undefined);assert.equal(row.discoverable,undefined);
});
test('updates scoped to verified owner and cannot change owner',async()=>{
  const f=fixture({exists:true});await f.service.save({user_id:'victim',username:'alice',display_name:'Alice'});
  assert.equal(f.calls.find(c=>c[0]==='update')[1].user_id,undefined);assert.equal(f.calls.filter(c=>c[0]==='eq'&&c[1]==='user_id'&&c[2]==='owner').length,2);
});
test('signout requests local session revocation',async()=>{const f=fixture();await f.service.signOut();assert.deepEqual(f.calls,[['logout',{scope:'local'}]])});

test('confirmed users without MFA can use their profile',async()=>{const f=fixture({level:'aal1',nextLevel:'aal1'});await f.service.load();await f.service.save({username:'alice',display_name:'Alice'});assert.ok(f.calls.some(c=>c[0]==='insert'));});

import {profileSaver} from '../profile-save.js';
test('sign-out during profile save cannot restore private identity',async()=>{
 let revision=1,resolve;const published=[],results=[];
 const save=profileSaver({save:()=>new Promise(r=>resolve=r),revision:()=>revision,publish:r=>published.push(r),result:r=>results.push(r)});
 const pending=save({display_name:'Private'});revision++;resolve({display_name:'Private'});await pending;
 assert.deepEqual(published,[]);assert.deepEqual(results,[]);
});
test('old-session save failure cannot affect a new session',async()=>{
 let revision=1,reject;const results=[];
 const save=profileSaver({save:()=>new Promise((_,r)=>reject=r),revision:()=>revision,publish:()=>assert.fail(),result:r=>results.push(r)});
 const pending=save({});revision++;reject({code:'42501'});await pending;assert.deepEqual(results,[]);
});
test('same-session save succeeds and duplicate submissions are suppressed',async()=>{
 let resolve,calls=0;const published=[],results=[];
 const save=profileSaver({save:()=>{calls++;return new Promise(r=>resolve=r)},revision:()=>1,publish:r=>published.push(r),result:r=>results.push(r)});
 const pending=save({});await save({});resolve({user_id:'owner'});await pending;
 assert.equal(calls,1);assert.deepEqual(published,[{user_id:'owner'}]);assert.deepEqual(results,[{saved:true}]);
});

test('sign out everywhere explicitly revokes global scope',async()=>{
 const f=fixture();await f.service.signOutAll();assert.deepEqual(f.calls.filter(c=>c[0]==='logout'),[['logout',{scope:'global'}]]);
});
test('unconfirmed identity cannot request account-wide revocation',async()=>{
 const f=fixture({confirmed:false});await assert.rejects(f.service.signOutAll());assert.equal(f.calls.length,0);
});
