import security,base64
from security import hashpw,checkpw
import free_data, storage, launch_features, mail_service, ai_service, operations, owner_reports, gmgn_service
from http.cookies import SimpleCookie
import json, os, re, threading, time, urllib.request, urllib.parse, urllib.error, sqlite3, hashlib, hmac, secrets, smtplib
from email.message import EmailMessage
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from datetime import datetime, timezone, timedelta

ROOT=Path(__file__).parent
DB=Path(os.getenv('VANTIX_DB_PATH',str(ROOT/'vantix.db')))
AUTH_LIMITS={}
AUTH_LOCK=threading.Lock()
PUBLIC_ROUTES={'/','/ask','/markets','/crypto','/trending','/stocks','/forex','/commodities','/economy','/news','/feed','/radar','/shield','/watchlist','/alerts','/research','/copilot','/sectors','/portfolio','/account','/admin','/reset-password','/privacy','/terms'}
def auth_allowed(ip):
    ip=security.private_id(ip)
    with AUTH_LOCK:
        tick=time.monotonic()
        old=[x for x in AUTH_LIMITS.get(ip,[]) if tick-x<60]
        if len(old)>=20:return False
        AUTH_LIMITS[ip]=old+[tick]
        if len(AUTH_LIMITS)>10000:
            for key in list(AUTH_LIMITS):
                if not AUTH_LIMITS[key] or tick-AUTH_LIMITS[key][-1]>=60:AUTH_LIMITS.pop(key,None)
        return True
BINANCE='https://api.binance.com/api/v3/ticker/24hr'
FRANK='https://api.frankfurter.app/latest?from=USD'
NEWS_RSS='https://news.google.com/rss/search?q=markets%20OR%20crypto%20OR%20economy%20OR%20stocks%20OR%20geopolitics&hl=en-GB&gl=GB&ceid=GB:en'


MAINT_LOCK=threading.Lock()
MAINT_LAST=0
def db():
    global MAINT_LAST
    c=storage.connect(DB,(ROOT/'launch_schema.sql').read_text())
    if time.monotonic()-MAINT_LAST>3600 and MAINT_LOCK.acquire(blocking=False):
        try:
            cutoff=iso(now()-timedelta(days=30));current=iso(now())
            for sql in ('DELETE FROM events WHERE created_at<?','DELETE FROM notifications WHERE created_at<?'):c.execute(sql,(cutoff,))
            for sql in ('DELETE FROM sessions WHERE expires_at<?','DELETE FROM verify_tokens WHERE expires_at<?','DELETE FROM reset_tokens WHERE expires_at<?'):c.execute(sql,(current,))
            c.execute('DELETE FROM security_audit WHERE created_at<?',(cutoff,));c.execute('DELETE FROM limits WHERE period<?',(cutoff[:10],));c.commit();MAINT_LAST=time.monotonic()
        finally:MAINT_LOCK.release()
    return c


def now(): return datetime.now(timezone.utc)
def iso(d): return d.isoformat()

def fetch(url, timeout=10, headers=None):
    h={'User-Agent':'VANTIX/1.0'}; h.update(headers or {})
    req=urllib.request.Request(url,headers=h)
    with urllib.request.urlopen(req,timeout=timeout) as r:return r.read()

def market_data():return free_data.market()['data']
def news_data():return free_data.news()['data']
def x_feed():return []  # Free-only build never calls a paid social API.

def send_verification(email, token):
    host=os.getenv('VANTIX_PUBLIC_URL','http://localhost:8000').rstrip('/')
    link=host+'/api/auth/verify?token='+urllib.parse.quote(token)
    sent=mail_service.send(email,'Verify your VANTIX account','Open this link to verify your email within 24 hours:\n'+link)
    return sent,None if sent else link


def email_action(path,email,password=''):
    c=db()
    try:
        security.audit(c,'email_request')
        if path!='/api/auth/register':
            launch_features.post(None,path,{'email':email},c,None,hashpw);return
        hashed=hashpw(password)
        try:
            cur=c.execute('INSERT INTO users(email,password_hash,created_at) VALUES(?,?,?)',(email,hashed,iso(now())))
            uid=cur.lastrowid;tok=secrets.token_urlsafe(32)
            c.execute('INSERT INTO verify_tokens(token,user_id,expires_at) VALUES(?,?,?)',(token_hash(tok),uid,iso(now()+timedelta(hours=24))));c.commit()
            security.audit(c,'registration',uid)
        except sqlite3.IntegrityError:c.rollback();return
        send_verification(email,tok)
    finally:c.close();storage.cleanup()

def request_token(h):
    try:
        cookie=SimpleCookie();cookie.load(h.headers.get('Cookie',''));value=cookie.get('vantix_session')
        if value:return value.value
    except Exception:pass
    return ''
def token_hash(token):return hashlib.sha256(token.encode()).hexdigest()
def user_from_request(h):
    token=request_token(h)
    if not token:return None
    c=db();r=c.execute('SELECT u.* FROM sessions s JOIN users u ON u.id=s.user_id WHERE s.token=? AND s.expires_at>? AND NOT EXISTS(SELECT 1 FROM profiles p WHERE p.user_id=u.id AND p.banned=1)',(token_hash(token),iso(now()))).fetchone();c.close();return r

def json_body(h):
    n=int(h.headers.get('Content-Length','0'))
    if n<0 or n>16384: raise ValueError('Request too large')
    value=json.loads(h.rfile.read(n) or '{}')
    if not isinstance(value,dict): raise ValueError('Expected object')
    security.validate_body(value)
    return value

class H(BaseHTTPRequestHandler):
    def setup(self):
        super().setup(); self.connection.settimeout(50)
    def log_message(self,*args): pass
    def send(self,code,body,ctype='application/json'):
        if ctype.startswith('text/html'):
            scripts=re.findall(r'<script>([\s\S]*?)</script>',body)
            hashes=' '.join("'sha256-"+base64.b64encode(hashlib.sha256(x.encode()).digest()).decode()+"'" for x in scripts)
            self.csp="default-src 'self'; script-src "+hashes+" https://s3.tradingview.com; script-src-attr 'none'; style-src 'self' 'unsafe-inline'; img-src 'self' data: https://*.tradingview.com; connect-src 'self' wss://data-stream.binance.vision wss://stream.bybit.com wss://ws-feed.exchange.coinbase.com; frame-src https://*.tradingview.com; object-src 'none'; base-uri 'none'; frame-ancestors 'none'; form-action 'self'"
        b=body.encode(); self.send_response(code); self.send_header('Content-Type',ctype); self.send_header('Content-Length',str(len(b))); self.send_header('Cache-Control','no-store'); self.send_header('X-Content-Type-Options','nosniff'); self.send_header('X-Frame-Options','DENY'); self.send_header('Referrer-Policy','no-referrer'); 
        self.send_header('Content-Security-Policy',getattr(self,'csp',"default-src 'none'; frame-ancestors 'none'; base-uri 'none'"))
        for cookie in getattr(self,'out_cookies',[]):self.send_header('Set-Cookie',cookie)
        if getattr(self,'download_name',None):self.send_header('Content-Disposition','attachment; filename="'+self.download_name+'"')
        self.end_headers(); self.wfile.write(b)
    def session_cookie(self,token='',clear=False):
        suffix='; Secure' if os.getenv('VANTIX_ENV')=='production' else ''
        self.out_cookies.append('vantix_session='+token+'; HttpOnly; SameSite=Lax; Path=/; Max-Age='+('0' if clear else '604800')+suffix)
    def do_GET(self):
        self.out_cookies=[]
        try:self.get_route()
        except (BrokenPipeError,ConnectionResetError):pass
        except Exception as e:
            operations.fault('request',type(e).__name__);self.send(503,json.dumps({'message':'Service temporarily unavailable. Please try again.'}))
        finally:storage.cleanup()
    def do_POST(self):
        self.out_cookies=[]
        origin=self.headers.get('Origin')
        expected=os.getenv('VANTIX_PUBLIC_URL','').rstrip('/')
        production=os.getenv('VANTIX_ENV')=='production'
        if (production and (not expected or not origin or origin!=expected)) or (not production and origin and origin!=(expected or 'http://'+self.headers.get('Host',''))):return self.send(403,json.dumps({'message':'Request origin rejected.'}))
        if self.headers.get('Content-Type','').split(';')[0]!='application/json':return self.send(415,json.dumps({'message':'Use application/json.'}))
        try:self.post_route()
        except (BrokenPipeError,ConnectionResetError):pass
        except Exception as e:
            operations.fault('request',type(e).__name__);self.send(503,json.dumps({'message':'Service temporarily unavailable. Please try again.'}))
        finally:storage.cleanup()
    def get_route(self):
        p=urllib.parse.urlparse(self.path); q=urllib.parse.parse_qs(p.query)
        if p.path in ('/api/admin/operations','/api/admin/export'):
            u=user_from_request(self)
            if not launch_features.admin(u):return self.send(403,json.dumps({'message':'Owner access required.'}))
            if p.path.endswith('operations'):return self.send(200,json.dumps(operations.snapshot()))
            try:
                kind=(q.get('kind') or ['summary'])[0];after=int((q.get('after') or ['0'])[0])
                if after<0:raise ValueError()
                c=db();ctype,name,body=owner_reports.report(c,kind,after)
                c.execute('INSERT INTO audit(admin_id,action,target,created_at) VALUES(?,?,?,?)',(u['id'],'export',kind,iso(now())));c.commit();c.close()
            except ValueError:return self.send(400,json.dumps({'message':'Invalid report request.'}))
            self.download_name=name;return self.send(200,body,ctype)
        if p.path in ('/api/capabilities','/api/profile','/api/community','/api/saved','/api/notifications','/api/admin'):
            c=db();result=launch_features.get(self,p.path,q,c,user_from_request(self));c.close()
            if result:return self.send(result[0],json.dumps(result[1]))
        if p.path=='/api/health':
            return self.send(200,json.dumps({'ok':True,'service':'VANTIX','mode':'free-only','note':'Service health is not provider health. Each data response reports its own status.'}))
        if p.path=='/api/market': return self.send(200,json.dumps(free_data.market()))
        if p.path in ('/api/gmgn/trending','/api/gmgn/fresh'):
            chain=(q.get('chain') or ['sol'])[0];interval=(q.get('interval') or ['5m'])[0]
            try:result=gmgn_service.trending(chain,interval) if p.path.endswith('trending') else gmgn_service.fresh(chain)
            except ValueError:return self.send(400,json.dumps({'message':'Choose a supported GMGN chain and interval.'}))
            return self.send(200,json.dumps(result))
        if p.path=='/api/news':
            topic=(q.get('topic') or ['all'])[0]
            if topic not in ('all','world','energy','policy'):return self.send(400,json.dumps({'message':'Unknown news topic'}))
            return self.send(200,json.dumps(free_data.news(topic)))
        if p.path in ('/api/economy','/api/sectors','/api/filings'):
            try:
                result=free_data.filings((q.get('cik') or [''])[0]) if p.path=='/api/filings' else free_data.economy((q.get('country') or ['GBR'])[0],p.path=='/api/sectors')
            except ValueError as e:return self.send(400,json.dumps({'message':str(e)}))
            return self.send(200,json.dumps(result))
        if p.path=='/api/social': return self.send(200,json.dumps({'data':[],'configured':False,'status':'UNAVAILABLE','message':'Paid social APIs are disabled in the free-only build. Community posts are available in VANTIX Feed.'}))
        if p.path=='/api/feed':
            c=db();u=user_from_request(self);uid=u['id'] if u else 0;mode=(q.get('sort') or ['latest'])[0]
            if mode not in ('latest','trending','following'):c.close();return self.send(400,json.dumps({'message':'Invalid feed sort.'}))
            rows=c.execute("SELECT p.*,coalesce(pr.display_name,'Member '||p.author_id) display_name,coalesce(l.label,'Community commentary') label,(SELECT count(*) FROM reactions r WHERE r.post_id=p.id) reactions,(SELECT count(*) FROM reactions r WHERE r.post_id=p.id AND r.user_id=?) reacted,(SELECT count(*) FROM follows f WHERE f.followed_id=p.author_id) followers,(SELECT count(*) FROM follows f WHERE f.follower_id=? AND f.followed_id=p.author_id) following FROM posts p LEFT JOIN profiles pr ON pr.user_id=p.author_id LEFT JOIN post_labels l ON l.post_id=p.id WHERE NOT EXISTS(SELECT 1 FROM hidden_content h WHERE h.kind='post' AND h.target_id=p.id) ORDER BY p.id DESC LIMIT 100",(uid,uid)).fetchall();out=[]
            ids=[r['id'] for r in rows];groups={x:[] for x in ids}
            if ids:
                query="SELECT c.id,c.post_id,c.author_id,c.body,c.created_at,coalesce(pr.display_name,'Member '||c.author_id) display_name FROM comments c LEFT JOIN profiles pr ON pr.user_id=c.author_id WHERE c.post_id IN ("+','.join('?' for _ in ids)+") AND NOT EXISTS(SELECT 1 FROM hidden_content h WHERE h.kind='comment' AND h.target_id=c.id) ORDER BY c.id DESC LIMIT 500"
                for item in c.execute(query,ids).fetchall():
                    if len(groups[item['post_id']])<50:groups[item['post_id']].append(dict(item))
            for row in rows:
                comments=list(reversed(groups[row['id']]));item={**dict(row),'comments_list':comments,'comments':len(comments),'can_follow':bool(uid and uid!=row['author_id'])};out.append(item)
            if mode=='following':out=[x for x in out if x['following']]
            elif mode=='trending':out.sort(key=lambda x:(-(x['reactions']*3+x['comments']*2),-x['id']))
            c.close();return self.send(200,json.dumps({'data':out[:50],'sort':mode}))
        if p.path=='/api/auth/verify':
            tok=(q.get('token') or [''])[0]; c=db(); r=c.execute('SELECT * FROM verify_tokens WHERE token=? AND expires_at>?',(token_hash(tok),iso(now()))).fetchone()
            if not r:c.close();return self.send(400,json.dumps({'ok':False,'message':'Verification link is invalid or expired.'}))
            c.execute('UPDATE users SET verified=1 WHERE id=?',(r['user_id'],)); c.execute('DELETE FROM verify_tokens WHERE token=?',(token_hash(tok),)); c.commit(); c.close(); return self.send(200,'<html><body style="font-family:system-ui;background:#020711;color:white;padding:40px"><h1>VANTIX account verified</h1><p>You can now return to VANTIX and sign in.</p></body></html>','text/html; charset=utf-8')
        if p.path=='/api/auth/me':
            u=user_from_request(self); return self.send(200,json.dumps({'authenticated':bool(u),'user':{'id':u['id'],'email':u['email'],'verified':bool(u['verified']),'admin':launch_features.admin(u)} if u else None}))
        if p.path in ('/api/shield','/api/token-pairs'):
            chain=(q.get('chain') or [''])[0];token=(q.get('token') or [''])[0].strip()
            if not chain:return self.send(200,json.dumps({'status':'UNKNOWN','message':'Select a chain before checking this token.','data':[]}))
            # Fixed provider URLs, validated addresses, and a shared request cap.
            if not auth_allowed('token-lookup'):return self.send(429,json.dumps({'message':'Token lookups are busy. Please wait a minute.'}))
            try:result=free_data.token_security(chain,token) if p.path=='/api/shield' else free_data.token_pairs(chain,token)
            except ValueError as e:return self.send(400,json.dumps({'status':'UNKNOWN','message':str(e),'data':[]}))
            return self.send(200,json.dumps(result))
        if p.path.startswith('/api/'): return self.send(404,json.dumps({'error':'Not found'}))
        if p.path=='/manifest.webmanifest':return self.send(200,(ROOT/'manifest.webmanifest').read_text(encoding='utf-8'),'application/manifest+json')
        if p.path=='/sw.js':return self.send(200,(ROOT/'sw.js').read_text(encoding='utf-8'),'application/javascript; charset=utf-8')
        if p.path=='/icon.svg':return self.send(200,(ROOT/'icon.svg').read_text(encoding='utf-8'),'image/svg+xml')
        if (p.path.rstrip('/') or '/') not in PUBLIC_ROUTES:return self.send(404,'Page not found','text/plain; charset=utf-8')
        f=ROOT/'index.html'; return self.send(200,f.read_text(encoding='utf-8'),'text/html; charset=utf-8')
    def post_route(self):
        if self.path.startswith('/api/auth/') and not auth_allowed(self.client_address[0]):return self.send(429,json.dumps({'ok':False,'message':'Too many sign-in attempts. Please wait a minute.'}))
        try: body=json_body(self)
        except Exception:return self.send(400,json.dumps({'error':'Invalid JSON'}))
        if self.path in ('/api/auth/register','/api/auth/login','/api/auth/reset-request','/api/auth/resend'):
            email=str(body.get('email','')).strip().lower()
            c=db();allowed=security.auth_limit(c,email,self.client_address[0],now().strftime('%Y-%m-%dT%H:%M'));c.close()
            if not allowed:return self.send(429,json.dumps({'message':'Too many authentication requests. Please try later.'}))
        if os.getenv('VANTIX_ENV')=='production' and self.path in ('/api/auth/register','/api/auth/reset-request','/api/auth/resend'):
            email=str(body.get('email','')).strip().lower();pw=body.get('password','')
            if not re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+',email) or len(email)>254 or (self.path.endswith('register') and (not isinstance(pw,str) or not 8<=len(pw)<=256)):
                return self.send(400,json.dumps({'message':'Use a valid email and a password of 8–256 characters.'}))
            action=self.path
            if not mail_service.enqueue(lambda:email_action(action,email,pw)):return self.send(503,json.dumps({'message':'Email requests are busy. Please try later.'}))
            return self.send(200,json.dumps({'ok':True,'message':'If eligible, check your email to continue.'}))
        extra_paths=('/api/auth/reset-request','/api/auth/reset','/api/auth/resend','/api/events','/api/saved/add','/api/saved/remove','/api/profile','/api/community/follow','/api/feed/reaction','/api/feed/report','/api/admin/moderate','/api/notifications/read','/api/ai')
        if self.path in extra_paths:
            c=db();u=user_from_request(self)
            if u and self.path not in ('/api/events','/api/notifications/read'):
                minute=now().strftime('%Y-%m-%dT%H:%M');r=c.execute('INSERT INTO limits(bucket,period,count) VALUES(?,?,1) ON CONFLICT(bucket,period) DO UPDATE SET count=count+1 WHERE count<30 RETURNING count',('write-'+str(u['id']),minute)).fetchone();c.commit()
                if not r:c.close();return self.send(429,json.dumps({'message':'Please wait before trying again.'}))
            result=launch_features.post(self,self.path,body,c,u,hashpw);c.close()
            if result:return self.send(result[0],json.dumps(result[1]))
        if self.path=='/api/auth/logout':
            c=db(); c.execute('DELETE FROM sessions WHERE token=?',(token_hash(request_token(self)),)); c.commit(); security.audit(c,'logout');c.close(); self.session_cookie(clear=True); return self.send(200,json.dumps({'ok':True}))
        if self.path=='/api/auth/register':
            email=str(body.get('email','')).strip().lower(); pw=str(body.get('password',''))
            if not re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+',email) or len(email)>254 or not 8<=len(pw)<=256:return self.send(400,json.dumps({'ok':False,'message':'Use a valid email and a password of 8–256 characters.'}))
            hashed=hashpw(pw)
            c=db()
            try:
                cur=c.execute('INSERT INTO users(email,password_hash,created_at) VALUES(?,?,?)',(email,hashed,iso(now()))); uid=cur.lastrowid; tok=secrets.token_urlsafe(32); c.execute('INSERT INTO verify_tokens(token,user_id,expires_at) VALUES(?,?,?)',(token_hash(tok),uid,iso(now()+timedelta(hours=24)))); c.commit()
            except sqlite3.IntegrityError:c.rollback();c.close();return self.send(200,json.dumps({'ok':True,'message':'If eligible, check your email to continue.'}))
            c.close(); sent,dev=send_verification(email,tok); return self.send(200,json.dumps({'ok':True,'message':'If eligible, check your email to continue.','dev_verification_url':dev if not sent and os.getenv('VANTIX_ENV')!='production' else None}))
        if self.path=='/api/auth/login':
            email=str(body.get('email','')).strip().lower(); pw=str(body.get('password','')); c=db(); u=c.execute('SELECT * FROM users WHERE email=?',(email,)).fetchone()
            if not checkpw(pw,u['password_hash'] if u else security.DUMMY_HASH) or not u:security.audit(c,'login_failed');c.close();return self.send(401,json.dumps({'ok':False,'message':'Invalid email or password.'}))
            banned=c.execute('SELECT banned FROM profiles WHERE user_id=?',(u['id'],)).fetchone()
            if banned and banned['banned']:c.close();return self.send(403,json.dumps({'message':'Account suspended. Contact the site owner.'}))
            if not u['verified']:c.close();return self.send(403,json.dumps({'ok':False,'message':'Verify your email before signing in.'}))
            authenticated_hash=u['password_hash']
            if security.needs_rehash(u['password_hash']):
                upgraded=hashpw(pw);c.execute('UPDATE users SET password_hash=? WHERE id=? AND password_hash=?',(upgraded,u['id'],u['password_hash']));c.commit();authenticated_hash=upgraded
            tok=secrets.token_urlsafe(32)
            issued=c.execute('INSERT INTO sessions(token,user_id,expires_at) SELECT ?,id,? FROM users WHERE id=? AND password_hash=? AND verified=1 AND NOT EXISTS(SELECT 1 FROM profiles WHERE user_id=users.id AND banned=1) RETURNING user_id',(token_hash(tok),iso(now()+timedelta(days=7)),u['id'],authenticated_hash)).fetchone()
            if not issued:c.rollback();c.close();return self.send(401,json.dumps({'message':'Account changed. Please sign in again.'}))
            launch_features.record(c,u['id'],'login');security.audit(c,'login',u['id']);c.close();self.session_cookie(tok);return self.send(200,json.dumps({'ok':True,'authenticated':True,'token':tok if os.getenv('VANTIX_ENV')!='production' else None,'user':{'id':u['id'],'email':u['email'],'verified':True}}))
        if self.path in ('/api/feed/post','/api/feed/comment'):
            u=user_from_request(self)
            if u:
                c=db();allowed=ai_service.reserve(c,'community-'+str(u['id']),100);c.close()
                if not allowed:return self.send(429,json.dumps({'message':'Daily community posting limit reached.'}))
        if self.path=='/api/feed/post':
            u=user_from_request(self)
            if not u or not u['verified']:return self.send(401,json.dumps({'ok':False,'message':'Sign in with a verified account to post.'}))
            bodytxt=str(body.get('body','')).strip(); src=str(body.get('source_url','')).strip(); label=str(body.get('source_label','')).strip()
            if len(src)>2048 or len(label)>200:return self.send(400,json.dumps({'ok':False,'message':'Source URL or label is too long.'}))
            if src and not security.safeurl(src): return self.send(400,json.dumps({'ok':False,'message':'Source must be an http or https URL.'}))
            if not bodytxt or len(bodytxt)>1000:return self.send(400,json.dumps({'ok':False,'message':'Post must be 1–1000 characters.'}))
            c=db(); cur=c.execute('INSERT INTO posts(author_id,body,source_url,source_label,created_at) VALUES(?,?,?,?,?)',(u['id'],bodytxt,src,label,iso(now()))); pid=cur.lastrowid;label=str(body.get('label','Community commentary'));label=label if label in ('Community commentary','AI Interpretation','Rumour','Prediction') else 'Community commentary';c.execute('INSERT INTO post_labels(post_id,label) VALUES(?,?)',(pid,label));launch_features.record(c,u['id'],'feed_post');c.close();return self.send(200,json.dumps({'ok':True,'id':pid}))
        if self.path=='/api/feed/comment':
            u=user_from_request(self)
            if not u or not u['verified']:return self.send(401,json.dumps({'ok':False,'message':'Sign in with a verified account to comment.'}))
            
            try: pid=int(body.get('post_id',0))
            except (ValueError,TypeError): return self.send(400,json.dumps({'ok':False,'message':'Invalid post id.'}))
            if pid<=0:return self.send(400,json.dumps({'ok':False,'message':'Invalid post id.'}))
            txt=str(body.get('body','')).strip()
            if not txt or len(txt)>500:return self.send(400,json.dumps({'ok':False,'message':'Comment must be 1–500 characters.'}))
            c=db(); exists=c.execute("SELECT id FROM posts WHERE id=? AND NOT EXISTS(SELECT 1 FROM hidden_content WHERE kind='post' AND target_id=posts.id)",(pid,)).fetchone()
            if not exists:c.close();return self.send(404,json.dumps({'ok':False,'message':'Post not found.'}))
            c.execute('INSERT INTO comments(post_id,author_id,body,created_at) VALUES(?,?,?,?)',(pid,u['id'],txt,iso(now())));launch_features.record(c,u['id'],'feed_comment');c.close();return self.send(200,json.dumps({'ok':True}))
        if self.path=='/api/ai':
            return self.send(503,json.dumps({'status':'UNAVAILABLE','answer':'Ask VANTIX is unavailable in this preview. Sourced market and news grounding has not yet been implemented.'}))
        return self.send(404,json.dumps({'error':'Not found'}))

class BoundedServer(ThreadingHTTPServer):
    daemon_threads=True
    request_queue_size=64
    def __init__(self,*args,**kwargs):self.slots=threading.BoundedSemaphore(32);super().__init__(*args,**kwargs)
    def process_request(self,request,address):
        if not self.slots.acquire(blocking=False):
            try:request.settimeout(1);request.sendall(b'HTTP/1.1 503 Service Unavailable\r\nRetry-After: 5\r\nConnection: close\r\nContent-Length: 0\r\n\r\n')
            finally:self.shutdown_request(request)
            return
        try:super().process_request(request,address)
        except Exception:self.slots.release();raise
    def process_request_thread(self,request,address):
        try:super().process_request_thread(request,address)
        finally:self.slots.release()

if __name__=='__main__':
    if os.getenv('VANTIX_ENV')=='production':
        from preflight import check
        missing=check()
        if missing:raise SystemExit('Launch configuration incomplete: '+', '.join(missing))
    db().close(); operations.start(db); BoundedServer((os.getenv('HOST','127.0.0.1'),int(os.getenv('PORT','8000'))),H).serve_forever()
