"""Account-scoped conversations. Public groups require membership to read or post."""
import re,sqlite3
from datetime import datetime,timezone
import ai_service

def stamp():return datetime.now(timezone.utc).isoformat()
def integer(value):
 if isinstance(value,bool):raise ValueError()
 n=int(value)
 if n<1 or n>9223372036854775807:raise ValueError()
 return n

def member(c,uid):
 return c.execute("SELECT u.id,coalesce(p.display_name,'Member '||u.id) display_name FROM users u LEFT JOIN profiles p ON p.user_id=u.id WHERE u.id=? AND u.verified=1 AND coalesce(p.banned,0)=0",(uid,)).fetchone()
def blocked(c,a,b):return bool(c.execute('SELECT 1 FROM chat_blocks WHERE (user_id=? AND blocked_id=?) OR (user_id=? AND blocked_id=?)',(a,b,b,a)).fetchone())
def thread(c,uid,data):
 group=data.get('group_id');peer=data.get('peer_id')
 if bool(group)==bool(peer):raise ValueError('Choose one conversation.')
 if group:
  gid=integer(group)
  row=c.execute('SELECT g.* FROM chat_groups g JOIN chat_members m ON m.group_id=g.id WHERE g.id=? AND m.user_id=?',(gid,uid)).fetchone()
  if not row:raise PermissionError('Join this group to read or send messages.')
  return 'g:'+str(gid),'m.group_id=?',(gid,),dict(row)
 pid=integer(peer);row=member(c,pid)
 if pid==uid or not row:raise PermissionError('Member unavailable.')
 return 'u:'+str(pid),'((m.sender_id=? AND m.recipient_id=?) OR (m.sender_id=? AND m.recipient_id=?))',(uid,pid,pid,uid),{'id':pid,'name':row['display_name'],'blocked':blocked(c,uid,pid),'blocked_by_you':bool(c.execute('SELECT 1 FROM chat_blocks WHERE user_id=? AND blocked_id=?',(uid,pid)).fetchone())}

def get(path,q,c,u):
 if not u or not u['verified']:return 401,{'message':'Sign in with a verified account to join the community.'}
 uid=u['id'];data={k:v[0] for k,v in q.items() if v}
 if path=='/api/chat/members':
  search=str(data.get('search','')).strip()[:80]
  rows=c.execute("SELECT u.id,coalesce(p.display_name,'Member '||u.id) display_name,(SELECT count(*) FROM follows f WHERE f.followed_id=u.id) followers,(SELECT count(*) FROM follows f WHERE f.follower_id=u.id) following_count,EXISTS(SELECT 1 FROM follows f WHERE f.follower_id=? AND f.followed_id=u.id) following,EXISTS(SELECT 1 FROM chat_blocks b WHERE b.user_id=? AND b.blocked_id=u.id) blocked FROM users u LEFT JOIN profiles p ON p.user_id=u.id LEFT JOIN social_profiles sp ON sp.user_id=u.id WHERE u.verified=1 AND coalesce(p.banned,0)=0 AND instr(lower(coalesce(p.display_name,'Member '||u.id)||' '||coalesce(sp.handle,'')),lower(?))>0 ORDER BY u.id DESC LIMIT 50",(uid,uid,search)).fetchall()
  return 200,{'data':[dict(r) for r in rows],'user_id':uid}
 if path=='/api/chat/profile':
  try:pid=integer(data.get('user_id',uid))
  except (ValueError,TypeError):return 400,{'message':'Invalid member.'}
  info=member(c,pid)
  if not info:return 404,{'message':'Member unavailable.'}
  profile=c.execute('SELECT handle,bio FROM social_profiles WHERE user_id=?',(pid,)).fetchone()
  followers=c.execute("SELECT u.id,coalesce(p.display_name,'Member '||u.id) display_name FROM follows f JOIN users u ON u.id=f.follower_id LEFT JOIN profiles p ON p.user_id=u.id WHERE f.followed_id=? AND u.verified=1 AND coalesce(p.banned,0)=0 ORDER BY f.created_at DESC LIMIT 50",(pid,)).fetchall()
  following=c.execute("SELECT u.id,coalesce(p.display_name,'Member '||u.id) display_name FROM follows f JOIN users u ON u.id=f.followed_id LEFT JOIN profiles p ON p.user_id=u.id WHERE f.follower_id=? AND u.verified=1 AND coalesce(p.banned,0)=0 ORDER BY f.created_at DESC LIMIT 50",(pid,)).fetchall()
  posts=c.execute("SELECT id,body,created_at FROM posts WHERE author_id=? AND NOT EXISTS(SELECT 1 FROM hidden_content h WHERE h.kind='post' AND h.target_id=posts.id) ORDER BY id DESC LIMIT 10",(pid,)).fetchall()
  return 200,{'profile':{**dict(info),**(dict(profile) if profile else {'handle':'','bio':''})},'followers':[dict(r) for r in followers],'following':[dict(r) for r in following],'posts':[dict(r) for r in posts],'is_self':pid==uid}
 if path=='/api/chat/groups':
  rows=c.execute('SELECT g.*,EXISTS(SELECT 1 FROM chat_members m WHERE m.group_id=g.id AND m.user_id=?) joined,(SELECT count(*) FROM chat_members m WHERE m.group_id=g.id) members FROM chat_groups g WHERE instr(lower(g.name),lower(?))>0 ORDER BY joined DESC,g.id DESC LIMIT 100',(uid,str(data.get('search',''))[:80])).fetchall()
  return 200,{'data':[dict(r) for r in rows],'user_id':uid}
 if path=='/api/chat/inbox':
  rows=c.execute("SELECT u.id,coalesce(p.display_name,'Member '||u.id) name,max(m.id) last_id,sum(CASE WHEN m.recipient_id=? AND m.id>coalesce(r.through,0) THEN 1 ELSE 0 END) unread FROM chat_messages m JOIN users u ON u.id=CASE WHEN m.sender_id=? THEN m.recipient_id ELSE m.sender_id END LEFT JOIN profiles p ON p.user_id=u.id LEFT JOIN chat_reads r ON r.user_id=? AND r.thread='u:'||u.id WHERE m.group_id IS NULL AND (m.sender_id=? OR m.recipient_id=?) AND coalesce(p.banned,0)=0 AND NOT EXISTS(SELECT 1 FROM hidden_content h WHERE h.kind='message' AND h.target_id=m.id) GROUP BY u.id ORDER BY last_id DESC LIMIT 100",(uid,uid,uid,uid,uid)).fetchall()
  return 200,{'data':[dict(r) for r in rows]}
 if path=='/api/chat/messages':
  try:
   key,where,args,info=thread(c,uid,data)
   before=integer(data['before']) if data.get('before') else 9223372036854775807
  except (ValueError,TypeError):return 400,{'message':'Invalid conversation or page.'}
  except PermissionError as e:return 403,{'message':str(e)}
  rows=c.execute("SELECT m.id,m.sender_id,m.body,m.created_at,coalesce(p.display_name,'Member '||m.sender_id) display_name FROM chat_messages m LEFT JOIN profiles p ON p.user_id=m.sender_id WHERE "+where+" AND m.id<? AND NOT EXISTS(SELECT 1 FROM hidden_content h WHERE h.kind='message' AND h.target_id=m.id) ORDER BY m.id DESC LIMIT 100",(*args,before)).fetchall()
  return 200,{'data':[dict(r) for r in reversed(rows)],'conversation':info,'user_id':uid,'has_more':len(rows)==100}
 return 404,{'message':'Chat endpoint not found.'}

def post(path,b,c,u):
 if not u or not u['verified']:return 401,{'message':'Sign in with a verified account to chat.'}
 uid=u['id']
 try:
  if path=='/api/chat/profile':
   handle=str(b.get('handle','')).strip().lower();bio=str(b.get('bio','')).strip();name=str(b.get('display_name','')).strip()
   if not re.fullmatch(r'[a-z0-9_]{3,24}',handle) or len(bio)>280 or not 2<=len(name)<=40 or any(ord(ch)<32 for ch in name):return 400,{'message':'Use a 3–24 character username (letters, numbers, underscore), a 2–40 character name and bio up to 280 characters.'}
   try:
    c.execute('INSERT INTO social_profiles(user_id,handle,bio) VALUES(?,?,?) ON CONFLICT(user_id) DO UPDATE SET handle=excluded.handle,bio=excluded.bio',(uid,handle,bio))
    c.execute('INSERT INTO profiles(user_id,display_name) VALUES(?,?) ON CONFLICT(user_id) DO UPDATE SET display_name=excluded.display_name',(uid,name));c.commit()
   except sqlite3.IntegrityError:c.rollback();return 409,{'message':'That username is already taken.'}
   return 200,{'ok':True}
  if path=='/api/chat/groups/create':
   name=str(b.get('name','')).strip()
   if not 3<=len(name)<=60 or any(ord(ch)<32 for ch in name):return 400,{'message':'Use a group name of 3–60 characters.'}
   if c.execute('SELECT count(*) n FROM chat_groups WHERE owner_id=?',(uid,)).fetchone()['n']>=20:return 400,{'message':'You can create up to 20 groups.'}
   cur=c.execute('INSERT INTO chat_groups(owner_id,name,created_at) VALUES(?,?,?)',(uid,name,stamp()));gid=cur.lastrowid
   c.execute('INSERT INTO chat_members(group_id,user_id) VALUES(?,?)',(gid,uid));c.commit();return 200,{'id':gid}
  if path=='/api/chat/groups/join':
   gid=integer(b.get('group_id'));row=c.execute('SELECT * FROM chat_groups WHERE id=?',(gid,)).fetchone()
   if not row:return 404,{'message':'Group not found.'}
   if b.get('active') is True:
    c.execute('INSERT OR IGNORE INTO chat_members(group_id,user_id) VALUES(?,?)',(gid,uid))
   else:
    if row['owner_id']==uid:return 400,{'message':'Group creators remain members of their group.'}
    c.execute('DELETE FROM chat_members WHERE group_id=? AND user_id=?',(gid,uid))
   c.commit();return 200,{'ok':True}
  if path=='/api/chat/block':
   pid=integer(b.get('peer_id'))
   if pid==uid or not member(c,pid):return 404,{'message':'Member unavailable.'}
   if b.get('active') is True:c.execute('INSERT OR IGNORE INTO chat_blocks(user_id,blocked_id) VALUES(?,?)',(uid,pid))
   else:c.execute('DELETE FROM chat_blocks WHERE user_id=? AND blocked_id=?',(uid,pid))
   c.commit();return 200,{'ok':True}
  if path in ('/api/chat/send','/api/chat/read'):
   key,where,args,info=thread(c,uid,b)
   if path.endswith('/read'):
    through=integer(b.get('through'))
    row=c.execute('SELECT max(m.id) last FROM chat_messages m WHERE '+where,args).fetchone()
    through=min(through,row['last'] or 0)
    c.execute('INSERT INTO chat_reads(user_id,thread,through) VALUES(?,?,?) ON CONFLICT(user_id,thread) DO UPDATE SET through=max(through,excluded.through)',(uid,key,through));c.commit();return 200,{'ok':True}
   if info.get('blocked'):return 403,{'message':'Messaging is blocked for this conversation.'}
   body=str(b.get('body','')).strip();nonce=str(b.get('client_id',''))
   if not 1<=len(body)<=2000 or not re.fullmatch(r'[A-Za-z0-9-]{16,80}',nonce):return 400,{'message':'Use 1–2000 characters and a valid message ID.'}
   old=c.execute('SELECT * FROM chat_messages WHERE sender_id=? AND client_id=?',(uid,nonce)).fetchone()
   gid=info['id'] if key.startswith('g:') else None;pid=info['id'] if key.startswith('u:') else None
   if old:
    if old['body']!=body or old['group_id']!=gid or old['recipient_id']!=pid:return 409,{'message':'Message ID already used.'}
    return 200,{'id':old['id']}
   if not ai_service.reserve(c,'chat-'+str(uid),300):return 429,{'message':'Daily message limit reached. Try tomorrow.'}
   cur=c.execute('INSERT INTO chat_messages(sender_id,recipient_id,group_id,body,client_id,created_at) VALUES(?,?,?,?,?,?) ON CONFLICT(sender_id,client_id) DO NOTHING RETURNING id',(uid,pid,gid,body,nonce,stamp()));row=cur.fetchone();c.commit()
   if not row:return 409,{'message':'Message already submitted. Refresh this conversation.'}
   return 200,{'id':row['id']}
  if path in ('/api/chat/report','/api/chat/delete'):
   mid=integer(b.get('message_id'));row=c.execute('SELECT * FROM chat_messages WHERE id=?',(mid,)).fetchone()
   if not row:return 404,{'message':'Message not found.'}
   if row['group_id']:thread(c,uid,{'group_id':row['group_id']})
   elif uid not in (row['sender_id'],row['recipient_id']):return 403,{'message':'Message unavailable.'}
   if path.endswith('/delete'):
    if row['sender_id']!=uid:return 403,{'message':'Only the sender can delete this message.'}
    c.execute("INSERT OR IGNORE INTO hidden_content(kind,target_id,moderator_id,created_at) VALUES('message',?,?,?)",(mid,uid,stamp()))
   else:
    reason=str(b.get('reason','')).strip()
    if not 5<=len(reason)<=500:return 400,{'message':'Use a reason of 5–500 characters.'}
    c.execute("INSERT INTO reports(user_id,kind,target_id,reason,created_at) VALUES(?,'message',?,?,?)",(uid,mid,reason,stamp()))
   c.commit();return 200,{'ok':True}
 except (ValueError,TypeError):return 400,{'message':'Invalid chat request.'}
 except PermissionError as e:return 403,{'message':str(e)}
 return 404,{'message':'Chat endpoint not found.'}
