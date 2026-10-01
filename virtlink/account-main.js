import {createClient} from '@supabase/supabase-js';
import {feedService} from './feed-service.js';
import {accountService} from './account-service.js';
const client=createClient('https://hnoqhdqnvvndyipcoudi.supabase.co','sb_publishable_pqG8y-tgBKvio5KFlS1PSQ_DdTc1w03',{
  auth:{storage:sessionStorage,storageKey:'virtlink-test-auth-v1',persistSession:true,autoRefreshToken:true,detectSessionInUrl:false}
});
const service=accountService(client);
const feed=feedService(client,service);
let revision=0,feedRevision=0,posting=false;
function feedEvent(detail){window.dispatchEvent(new CustomEvent('virtlink-feed',{detail}));}
async function refreshFeed(){const current=revision,request=++feedRevision;try{const rows=await feed.list();if(current===revision&&request===feedRevision)feedEvent({rows});}catch{if(current===revision&&request===feedRevision)feedEvent({error:'Could not load posts. Try Refresh.'});}}
function publish(profile){window.dispatchEvent(new CustomEvent('virtlink-account',{detail:profile}));}
async function refresh(){
  const current=++revision;
  try{
    const {data,error}=await client.auth.getSession();if(error)throw error;
    if(!data.session){if(current===revision)publish(null);return;}
    const profile=await service.load();
    if(current===revision){publish(profile);if(profile)await refreshFeed();}
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

window.addEventListener('virtlink-feed-refresh',refreshFeed);
window.addEventListener('virtlink-post-create',async event=>{
  if(posting)return;posting=true;const current=revision;
  window.dispatchEvent(new CustomEvent('virtlink-post-status',{detail:{busy:true}}));
  try{
    await feed.create(event.detail);
    if(current===revision){window.dispatchEvent(new CustomEvent('virtlink-post-status',{detail:{saved:true}}));await refreshFeed();}
  }catch(error){if(current===revision)window.dispatchEvent(new CustomEvent('virtlink-post-status',{detail:{error:error.code==='P0001'?'Posting limit reached. Try again later.':'Could not confirm your post. Refresh the feed before trying again.'}}));}
  finally{posting=false;window.dispatchEvent(new CustomEvent('virtlink-post-status',{detail:{busy:false}}));}
});
window.addEventListener('virtlink-post-delete',async event=>{
  const current=revision;
  try{await feed.remove(event.detail);if(current===revision)await refreshFeed();}
  catch{if(current===revision)feedEvent({error:'Could not delete the post. Refresh and try again.'});}
});

const liking=new Set();let commentBusy=false,commentsRevision=0;
function commentsEvent(detail){window.dispatchEvent(new CustomEvent('virtlink-comments',{detail}));}
async function loadComments(postId,saved=false){const current=revision,request=++commentsRevision;try{const rows=await feed.comments(postId);if(current===revision&&request===commentsRevision)commentsEvent({postId,rows,saved});}catch{if(current===revision&&request===commentsRevision)commentsEvent({postId,error:'Could not load comments. Close and reopen to retry.'});}}
window.addEventListener('virtlink-like',async event=>{
 const {postId,liked}=event.detail;if(liking.has(postId))return;liking.add(postId);const current=revision;
 try{await feed.like(postId,liked);if(current===revision)await refreshFeed();}
 catch{if(current===revision)feedEvent({error:'Could not update your like. Try again.'});}
 finally{liking.delete(postId);window.dispatchEvent(new CustomEvent('virtlink-like-done',{detail:postId}));}
});
window.addEventListener('virtlink-comments-load',event=>loadComments(event.detail));
window.addEventListener('virtlink-comment-create',async event=>{
 if(commentBusy)return;commentBusy=true;const current=revision,{postId,body}=event.detail;
 try{await feed.comment(postId,body);if(current===revision){commentsEvent({postId,saved:true});await loadComments(postId);await refreshFeed();}}
 catch(error){if(current===revision)commentsEvent({postId,error:error.code==='P0001'?'Commenting limit reached. Try again later.':'Could not confirm your comment. Close and reopen before retrying.'});}
 finally{commentBusy=false;commentsEvent({postId,busy:false});}
});
window.addEventListener('virtlink-comment-delete',async event=>{
 const current=revision,{id,postId}=event.detail;
 try{await feed.removeComment(id);if(current===revision){await loadComments(postId);await refreshFeed();}}
 catch{if(current===revision)commentsEvent({postId,error:'Could not delete your comment. Try again.'});}
});
