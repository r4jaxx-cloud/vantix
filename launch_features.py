import security
import os,json,re,math,secrets,hashlib,threading
from datetime import datetime,timezone,timedelta
import ai_service,mail_service,free_data

def ts():return datetime.now(timezone.utc).isoformat()
def admin(u):return bool(u and u['verified'] and u['email'].lower() in {x.strip().lower() for x in os.getenv('ADMIN_EMAILS','').split(',') if x.strip()})
def record(c,uid,event,path=''):
 c.execute('INSERT INTO events(user_id,event,path,created_at) VALUES(?,?,?,?)',(uid,event,path,ts()));c.commit()
def valid_kind(k):return k in ('watchlist','portfolio','alerts')
def community_rows(c,viewer=0):
 rows=c.execute("SELECT u.id,coalesce(p.display_name,'Member '||u.id) display_name,(SELECT count(*) FROM posts x WHERE x.author_id=u.id AND NOT EXISTS(SELECT 1 FROM hidden_content h WHERE h.kind='post' AND h.target_id=x.id)) posts,(SELECT count(*) FROM comments x WHERE x.author_id=u.id AND NOT EXISTS(SELECT 1 FROM hidden_content h WHERE h.kind='comment' AND h.target_id=x.id)) comments,(SELECT count(*) FROM reactions r JOIN posts x ON x.id=r.post_id WHERE x.author_id=u.id AND r.user_id<>x.author_id AND NOT EXISTS(SELECT 1 FROM hidden_content h WHERE h.kind='post' AND h.target_id=x.id)) likes,(SELECT count(*) FROM follows WHERE followed_id=u.id) followers,(SELECT count(*) FROM follows WHERE follower_id=? AND followed_id=u.id) following FROM users u LEFT JOIN profiles p ON p.user_id=u.id WHERE u.verified=1 AND coalesce(p.banned,0)=0",(viewer,)).fetchall();out=[]
 for r in rows:
  x=dict(r);x['points']=x['posts']*5+x['comments']*2+x['likes']+x['followers']*3
  x['badge']='Market Leader' if x['points']>=100 else 'Analyst' if x['points']>=40 else 'Contributor' if x['points']>=10 else 'Member';out.append(x)
 out.sort(key=lambda x:(-x['points'],-x['followers'],x['id']))
 for i,x in enumerate(out[:25],1):x['rank']=i
 return out[:25]
ALERT_LOCK=threading.Lock()
def evaluate_alerts(c,user_id=None):
 """Record observed crossings atomically, including users with no open browser."""
 with ALERT_LOCK:
  with free_data.LOCK:source=free_data.CACHE.get('crypto',{}).copy()
  if source.get('status')!='SNAPSHOT':return 0
  quotes={}
  for quote in source.get('data',[]):
   try:
    age=(datetime.now(timezone.utc)-datetime.fromisoformat(quote['updated'])).total_seconds()
    price=float(quote['price'])
    if not 0<=age<=180 or not math.isfinite(price) or price<=0 or quote.get('quote')!='USDT' or quote.get('status','SNAPSHOT')!='SNAPSHOT':continue
    quotes[quote['symbol']]=quote
   except (ValueError,TypeError,KeyError):continue
  if not quotes:return 0
  after=0;created=0
  while True:
   args=[after]
   scope=''
   if user_id is not None:scope=' AND s.user_id=?';args.append(user_id)
   rows=c.execute("SELECT s.id,s.user_id,s.symbol,s.value,a.above FROM saved_items s JOIN users u ON u.id=s.user_id LEFT JOIN profiles p ON p.user_id=u.id LEFT JOIN alert_state a ON a.item_id=s.id WHERE s.kind='alerts' AND u.verified=1 AND coalesce(p.banned,0)=0 AND s.id>?"+scope+" ORDER BY s.id LIMIT 500",tuple(args)).fetchall()
   if not rows:break
   for rule in rows:
    after=rule['id'];quote=quotes.get(rule['symbol'])
    if not quote:continue
    try:threshold=float(rule['value'])
    except (ValueError,TypeError):continue
    if not math.isfinite(threshold) or threshold<=0:continue
    above=int(float(quote['price'])>=threshold)
    if rule['above'] is not None and rule['above']==above:continue
    try:
     # First write takes the database transaction lock; RETURNING claims one transition.
     c.execute("INSERT OR IGNORE INTO alert_state(item_id,above) SELECT id,0 FROM saved_items WHERE id=? AND kind='alerts'",(rule['id'],))
     changed=c.execute('UPDATE alert_state SET above=? WHERE item_id=? AND above<>? RETURNING item_id',(above,rule['id'],above)).fetchone()
     if changed and above:
      c.execute("INSERT INTO notifications(user_id,message,source,observed_at,created_at) SELECT user_id,?,?,?,? FROM saved_items WHERE id=? AND kind='alerts'",(rule['symbol']+' reached your threshold of '+str(rule['value'])+' USDT',quote.get('source','Provider'),quote['updated'],ts(),rule['id']))
      created+=1
     c.commit()
    except Exception:c.rollback();raise
  return created

def get(h,path,q,c,u):
 if path=='/api/capabilities':return 200,{'support_email':os.getenv('SUPPORT_EMAIL',''),'ai_configured':bool(ai_service.enabled()),'ai_providers':[p[0] for p in ai_service.enabled()],'persistent_storage':bool(os.getenv('LIBSQL_URL')),'email_configured':mail_service.configured(),'mode':'public' if os.getenv('VANTIX_ENV')=='production' else 'local'}
 if path=='/api/profile':
  if not u:return 401,{'message':'Sign in to view your profile.'}
  r=c.execute('SELECT display_name FROM profiles WHERE user_id=?',(u['id'],)).fetchone()
  score=next((x for x in community_rows(c) if x['id']==u['id']),{'points':0,'badge':'Member','followers':0})
  return 200,{'id':u['id'],'display_name':r['display_name'] if r else 'Member '+str(u['id']),'verified':bool(u['verified']),'admin':admin(u),'points':score['points'],'badge':score['badge'],'followers':score['followers']}
 if path=='/api/community':return 200,{'data':community_rows(c,u['id'] if u else 0),'authenticated':bool(u)}
 if path=='/api/saved':
  if not u:return 401,{'message':'Sign in to access saved items.'}
  kind=(q.get('kind') or ['watchlist'])[0]
  if not valid_kind(kind):return 400,{'message':'Invalid collection.'}
  return 200,{'data':[dict(r) for r in c.execute('SELECT id,kind,symbol,value,created_at FROM saved_items WHERE user_id=? AND kind=? ORDER BY id DESC LIMIT 500',(u['id'],kind)).fetchall()]}
 if path=='/api/notifications':
  if not u:return 401,{'message':'Sign in to view notifications.'}
  evaluate_alerts(c,u['id'])
  return 200,{'data':[dict(r) for r in c.execute('SELECT id,message,source,observed_at,created_at,read FROM notifications WHERE user_id=? ORDER BY id DESC LIMIT 100',(u['id'],)).fetchall()],'unread':c.execute('SELECT count(*) n FROM notifications WHERE user_id=? AND read=0',(u['id'],)).fetchone()['n']}

 if path=='/api/admin':
  if not admin(u):return 403,{'message':'Owner access required.'}
  def count(sql,args=()):return c.execute(sql,args).fetchone()['n']
  counts={name:count(sql) for name,sql in {'registrations':'SELECT count(*) n FROM users','verified_users':'SELECT count(*) n FROM users WHERE verified=1','posts':'SELECT count(*) n FROM posts','comments':'SELECT count(*) n FROM comments','reactions':'SELECT count(*) n FROM reactions','open_reports':"SELECT count(*) n FROM reports WHERE status='open'",'page_views':"SELECT count(*) n FROM events WHERE event='page_view'",'unique_visitors':"SELECT count(distinct visitor) n FROM events WHERE event='page_view'"}.items()}
  for name,days in [('daily_active',1),('weekly_active',7),('monthly_active',30)]:counts[name]=count('SELECT count(distinct user_id) n FROM events WHERE created_at>=?',((datetime.now(timezone.utc)-timedelta(days=days)).isoformat(),))
  reports=[dict(r) for r in c.execute("SELECT * FROM reports ORDER BY id DESC LIMIT 100").fetchall()]
  with free_data.LOCK:health=[{k:v.get(k) for k in ('source','status','checked_at','retrieved_at','message')} for v in free_data.CACHE.values()]
  usage=[dict(r) for r in c.execute('SELECT event,count(*) n FROM events GROUP BY event').fetchall()]
  pages=[dict(r) for r in c.execute("SELECT path,count(*) n FROM events WHERE event='page_view' GROUP BY path ORDER BY n DESC LIMIT 30").fetchall()]
  return 200,{'counts':counts,'reports':reports,'providers':health,'usage':usage,'pages':pages,'note':'Visitors/page views count opted-in browser events. Active users reflect recorded actions, not every passive reader.'}
 return None

def post(h,path,b,c,u,hashpw):
 if path in ('/api/auth/reset-request','/api/auth/resend'):
  email=str(b.get('email','')).strip().lower();r=c.execute('SELECT id,verified FROM users WHERE email=?',(email,)).fetchone()
  result={'ok':True,'message':'If this account is eligible, an email will be sent. Check your inbox and spam folder.'}
  if r and (path.endswith('reset-request') or not r['verified']):
   reset=path.endswith('reset-request');token=secrets.token_urlsafe(32);table='reset_tokens' if reset else 'verify_tokens'
   c.execute({'reset_tokens':'DELETE FROM reset_tokens WHERE user_id=?','verify_tokens':'DELETE FROM verify_tokens WHERE user_id=?'}[table],(r['id'],));c.execute({'reset_tokens':'INSERT INTO reset_tokens(token,user_id,expires_at) VALUES(?,?,?)','verify_tokens':'INSERT INTO verify_tokens(token,user_id,expires_at) VALUES(?,?,?)'}[table],(hashlib.sha256(token.encode()).hexdigest(),r['id'],(datetime.now(timezone.utc)+timedelta(minutes=30)).isoformat()));c.commit()
   base=os.getenv('VANTIX_PUBLIC_URL','http://localhost:8000').rstrip('/')
   link=base+('/reset-password#token='+token if reset else '/api/auth/verify?token='+token)
   sent=mail_service.send(email,'Reset your VANTIX password' if reset else 'Verify your VANTIX email','Open this link within 30 minutes:\n'+link+'\nIf you did not request this, ignore the email.')
   if not sent and os.getenv('VANTIX_ENV')!='production':result['dev_verification_url']=link
  return 200,result
 if path=='/api/auth/reset':
  token=str(b.get('token',''));pw=str(b.get('password',''))
  if not 8<=len(pw)<=256:return 400,{'message':'Use a password of 8–256 characters.'}
  # Compute before opening a remote write transaction.
  hashed=hashpw(pw);row=c.execute('SELECT user_id FROM reset_tokens WHERE token=? AND expires_at>?',(hashlib.sha256(token.encode()).hexdigest(),ts())).fetchone()
  if not row:return 400,{'message':'Reset link is invalid or expired.'}
  deleted=c.execute('DELETE FROM reset_tokens WHERE token=? AND expires_at>? RETURNING user_id',(hashlib.sha256(token.encode()).hexdigest(),ts())).fetchone()
  if not deleted:c.commit();return 400,{'message':'Reset link has already been used.'}
  c.execute('UPDATE users SET password_hash=? WHERE id=?',(hashed,row['user_id']));c.execute('DELETE FROM sessions WHERE user_id=?',(row['user_id'],));c.commit();security.audit(c,'password_reset',row['user_id']);return 200,{'ok':True,'message':'Password changed. Sign in again.'}
 if path=='/api/events':
  if b.get('consent') is not True:return 200,{'ok':True,'recorded':False}
  if not ai_service.reserve(c,'events-global',2000):return 429,{'message':'Analytics quota reached.'}
  visitor=str(b.get('visitor',''));route=str(b.get('path',''))
  if not re.fullmatch(r'[a-zA-Z0-9-]{16,64}',visitor) or not re.fullmatch(r'/[a-z-]*',route):return 400,{'message':'Invalid event.'}
  c.execute('INSERT INTO events(visitor,user_id,event,path,created_at) VALUES(?,?,?,?,?)',(visitor,u['id'] if u else None,'page_view',route,ts()));c.commit();return 200,{'ok':True,'recorded':True}
 if path not in ('/api/saved/add','/api/saved/remove','/api/profile','/api/community/follow','/api/feed/reaction','/api/feed/report','/api/admin/moderate','/api/notifications/read','/api/ai'):return None
 if not u or not u['verified']:return 401,{'message':'Sign in with a verified account.'}
 uid=u['id']
 if path=='/api/profile':
  name=str(b.get('display_name','')).strip()
  if not 2<=len(name)<=40 or any(ord(x)<32 for x in name):return 400,{'message':'Display name must be 2–40 characters.'}
  c.execute('INSERT INTO profiles(user_id,display_name) VALUES(?,?) ON CONFLICT(user_id) DO UPDATE SET display_name=excluded.display_name',(uid,name));c.commit();return 200,{'ok':True}
 if path=='/api/community/follow':
  try:target=int(b.get('user_id',0))
  except (TypeError,ValueError):return 400,{'message':'Invalid member.'}
  if target==uid:return 400,{'message':'You cannot follow yourself.'}
  if not c.execute('SELECT id FROM users WHERE id=? AND verified=1',(target,)).fetchone():return 404,{'message':'Member not found.'}
  if b.get('active') is True:c.execute('INSERT OR IGNORE INTO follows(follower_id,followed_id,created_at) VALUES(?,?,?)',(uid,target,ts()))
  else:c.execute('DELETE FROM follows WHERE follower_id=? AND followed_id=?',(uid,target))
  c.commit();return 200,{'ok':True}
 if path=='/api/saved/add':
  kind=b.get('kind');symbol=str(b.get('symbol','')).strip().upper();value=b.get('value')
  if not valid_kind(kind) or not re.fullmatch(r'[A-Z0-9/._-]{1,24}',symbol):return 400,{'message':'Invalid collection or symbol.'}
  if kind=='alerts' and symbol not in free_data.TRACKED_CRYPTO:return 400,{'message':'Alerts currently support: '+', '.join(free_data.TRACKED_CRYPTO)+'. Thresholds use USDT.'}
  if kind!='watchlist':
   try:value=float(value)
   except (TypeError,ValueError):return 400,{'message':'Enter a numeric value.'}
   if not math.isfinite(value) or value<=0 or value>1e15:return 400,{'message':'Use a positive finite value below 1 quadrillion.'}
  else:value=None
  if c.execute('SELECT count(*) n FROM saved_items WHERE user_id=?',(uid,)).fetchone()['n']>=500:return 400,{'message':'Saved-item limit reached.'}
  c.execute('INSERT INTO saved_items(user_id,kind,symbol,value,created_at) VALUES(?,?,?,?,?)',(uid,kind,symbol,value,ts()));record(c,uid,kind+'_add');return 200,{'ok':True}
 if path=='/api/saved/remove':
  try:item=int(b.get('id',0))
  except (ValueError,TypeError):return 400,{'message':'Invalid item.'}
  owned=c.execute('SELECT id FROM saved_items WHERE id=? AND user_id=?',(item,uid)).fetchone()
  if not owned:return 404,{'message':'Item not found.'}
  c.execute('DELETE FROM alert_state WHERE item_id=?',(item,));c.execute('DELETE FROM saved_items WHERE id=? AND user_id=?',(item,uid));c.commit();return 200,{'ok':True}
 if path=='/api/notifications/read':
  through=b.get('through')
  if not isinstance(through,int) or isinstance(through,bool) or through<1:return 400,{'message':'Choose notifications to mark read.'}
  c.execute('UPDATE notifications SET read=1 WHERE user_id=? AND id<=?',(uid,through));c.commit();return 200,{'ok':True}
 if path=='/api/feed/reaction':
  try:pid=int(b.get('post_id',0))
  except (ValueError,TypeError):return 400,{'message':'Invalid post.'}
  if not c.execute("SELECT id FROM posts WHERE id=? AND NOT EXISTS(SELECT 1 FROM hidden_content WHERE kind='post' AND target_id=posts.id)",(pid,)).fetchone():return 404,{'message':'Post not found.'}
  if b.get('active') is True:c.execute('INSERT OR IGNORE INTO reactions(user_id,post_id) VALUES(?,?)',(uid,pid))
  else:c.execute('DELETE FROM reactions WHERE user_id=? AND post_id=?',(uid,pid))
  c.commit();return 200,{'ok':True}
 if path=='/api/feed/report':
  kind=b.get('kind');reason=str(b.get('reason','')).strip()
  try:target=int(b.get('target_id',0))
  except (TypeError,ValueError):return 400,{'message':'Invalid target.'}
  if kind not in ('post','comment') or not 5<=len(reason)<=500:return 400,{'message':'Choose a post/comment and provide a 5–500 character reason.'}
  table='posts' if kind=='post' else 'comments'
  if not c.execute({'posts':'SELECT id FROM posts WHERE id=?','comments':'SELECT id FROM comments WHERE id=?'}[table],(target,)).fetchone():return 404,{'message':'Content not found.'}
  c.execute('INSERT INTO reports(user_id,kind,target_id,reason,created_at) VALUES(?,?,?,?,?)',(uid,kind,target,reason,ts()));record(c,uid,'report');return 200,{'ok':True}
 if path=='/api/admin/moderate':
  if not admin(u):return 403,{'message':'Owner access required.'}
  action=b.get('action');kind=b.get('kind')
  try:target=int(b.get('target_id',0))
  except (TypeError,ValueError):return 400,{'message':'Invalid target.'}
  if action in ('hide','restore') and kind in ('post','comment'):
   if not c.execute({'post':'SELECT id FROM posts WHERE id=?','comment':'SELECT id FROM comments WHERE id=?'}[kind],(target,)).fetchone():return 404,{'message':'Content not found.'}
   if action=='hide':c.execute('INSERT OR REPLACE INTO hidden_content(kind,target_id,moderator_id,created_at) VALUES(?,?,?,?)',(kind,target,uid,ts()))
   else:c.execute('DELETE FROM hidden_content WHERE kind=? AND target_id=?',(kind,target))
   c.execute("UPDATE reports SET status='reviewed' WHERE kind=? AND target_id=?",(kind,target))
  elif action in ('ban','unban') and kind=='user':
   if not c.execute('SELECT id FROM users WHERE id=?',(target,)).fetchone():return 404,{'message':'User not found.'}
   if target==uid:return 400,{'message':'You cannot suspend your own account.'}
   c.execute('INSERT INTO profiles(user_id,display_name,banned) VALUES(?,?,?) ON CONFLICT(user_id) DO UPDATE SET banned=excluded.banned',(target,'Member '+str(target),int(action=='ban')))
   if action=='ban':c.execute('DELETE FROM sessions WHERE user_id=?',(target,))
  else:return 400,{'message':'Invalid moderation action.'}
  c.execute('INSERT INTO audit(admin_id,action,target,created_at) VALUES(?,?,?,?)',(uid,action,str(kind)+':'+str(target),ts()));c.commit();return 200,{'ok':True}
 if path=='/api/ai':
  question=str(b.get('question','')).strip()
  if not 3<=len(question)<=1500:return 400,{'message':'Use a question of 3–1500 characters.'}
  if b.get('consent') is not True:return 400,{'message':'Confirm sending this question to the configured AI providers.'}
  history=b.get('history',[])
  if not isinstance(history,list) or len(history)>4 or any(not isinstance(x,dict) or x.get('role') not in ('user','assistant') or not isinstance(x.get('content'),str) or len(x['content'])>1500 for x in history):
   return 400,{'message':'Conversation context is invalid. Refresh and try again.'}
  history=[{'role':x['role'],'content':x['content']} for x in history]
  with free_data.LOCK:cache=dict(free_data.CACHE)
  result=ai_service.answer(question,uid,c,cache,history);record(c,uid,'ai_request');return (200 if result['status'] in ('AI_INTERPRETATION','SOURCE_FALLBACK') else 503),result
 return None
