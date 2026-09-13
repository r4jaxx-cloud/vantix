"""Authentication and input primitives; no network calls."""
import hashlib,hmac,re,secrets,threading,unicodedata,os
from urllib.parse import urlsplit
from argon2 import PasswordHasher
from argon2.exceptions import VerificationError,InvalidHashError
_LOCAL_KEY=secrets.token_bytes(32)
def private_id(value):
 key=os.getenv('LIBSQL_AUTH_TOKEN','').encode() or _LOCAL_KEY
 return hmac.new(key,value.encode(),hashlib.sha256).hexdigest()
PH=PasswordHasher(time_cost=2,memory_cost=19456,parallelism=1)
HASH_SLOTS=threading.BoundedSemaphore(2)
def hashpw(password,s=None):
 with HASH_SLOTS:return PH.hash(password)
DUMMY_HASH=hashpw(secrets.token_urlsafe(32))
def checkpw(password,stored):
 if not isinstance(password,str) or len(password)>256:return False
 try:
  with HASH_SLOTS:
   if stored.startswith('$argon2id$'):return PH.verify(stored,password)
   algo,rounds,salt,expected=stored.split(':')
   if algo!='pbkdf2' or rounds!='600000':return False
   return hmac.compare_digest(hashlib.pbkdf2_hmac('sha256',password.encode(),salt.encode(),600000).hex(),expected)
 except (ValueError,TypeError,VerificationError,InvalidHashError):return False
def needs_rehash(stored):return not stored.startswith('$argon2id$') or PH.check_needs_rehash(stored)
def safeurl(value):
 try:
  if not isinstance(value,str) or len(value)>2048 or any(ord(c)<33 or ord(c)==127 for c in value) or '\\' in value:return ''
  p=urlsplit(value)
  if p.scheme not in ('http','https') or not p.hostname or p.username is not None or p.password is not None:return ''
  if p.port is not None and not 1<=p.port<=65535:return ''
  return value
 except ValueError:return ''
def valid_text(value,multiline=True):
 return isinstance(value,str) and all((c in '\n\t' and multiline) or (unicodedata.category(c) not in ('Cc','Cs') and c not in '\u202a\u202b\u202c\u202d\u202e\u2066\u2067\u2068\u2069') for c in value)
def validate_body(value):
 if isinstance(value,str):
  if not valid_text(value):raise ValueError('Invalid control characters')
 elif isinstance(value,dict):
  for k,v in value.items():
   validate_body(k)
   # Passwords are not normalized or silently transformed.
   if k!='password':validate_body(v)
   elif not isinstance(v,str) or any(unicodedata.category(c)=='Cs' for c in v):raise ValueError('Invalid password encoding')
 elif isinstance(value,list):
  for v in value:validate_body(v)
def audit(c,event,uid=None):
 c.execute('INSERT INTO security_audit(event,user_id,created_at) VALUES(?,?,strftime(\'%Y-%m-%dT%H:%M:%fZ\',\'now\'))',(event,uid));c.commit()
def auth_limit(c,email,ip,period):
 # Persisted, account-wide and account+peer limits; never trust client-supplied proxy headers.
 for label,value,limit in [('email',email,10),('email-ip',email+'|'+ip,6)]:
  bucket='auth-'+label+'-'+private_id(value)
  r=c.execute('INSERT INTO limits(bucket,period,count) VALUES(?,?,1) ON CONFLICT(bucket,period) DO UPDATE SET count=count+1 WHERE count<? RETURNING count',(bucket,period,limit)).fetchone();c.commit()
  if not r:return False
 return True
