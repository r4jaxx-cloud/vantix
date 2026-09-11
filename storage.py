"""SQLite locally; authenticated libSQL HTTP for durable deployment storage."""
import os,json,sqlite3,threading
from urllib.parse import urlparse
from urllib.request import Request,urlopen

SCHEMA_LOCK=threading.Lock()
READY=set()
ACTIVE=threading.local()

def encode(v):
 if v is None:return {'type':'null'}
 if isinstance(v,(int,bool)):return {'type':'integer','value':str(int(v))}
 if isinstance(v,float):return {'type':'float','value':v}
 return {'type':'text','value':str(v)}
def decode(v):
 t=v['type'];x=v.get('value')
 return int(x) if t=='integer' else float(x) if t=='float' else None if t=='null' else x
class Cursor:
 def __init__(self,result):
  names=[x['name'] for x in result.get('cols',[])];self.rows=[dict(zip(names,map(decode,row))) for row in result.get('rows',[])];self.lastrowid=int(result['last_insert_rowid']) if result.get('last_insert_rowid') else None;self.rowcount=result.get('affected_row_count',0)
 def fetchone(self):return self.rows.pop(0) if self.rows else None
 def fetchall(self):rows=self.rows;self.rows=[];return rows
class Remote:
 def __init__(self):
  url=os.environ['LIBSQL_URL'].replace('libsql://','https://');p=urlparse(url)
  if p.scheme!='https' or not p.hostname or not p.hostname.endswith('.turso.io') or p.username or p.password:raise ValueError('LIBSQL_URL must be your HTTPS Turso database URL')
  self.url='https://'+p.netloc+'/v2/pipeline';self.key=os.environ['LIBSQL_AUTH_TOKEN'];self.baton=None;self.transaction=False;self.closed=False
 def pipeline(self,requests):
  payload={'requests':requests}
  if self.baton:payload['baton']=self.baton
  req=Request(self.url,data=json.dumps(payload).encode(),headers={'Authorization':'Bearer '+self.key,'Content-Type':'application/json'})
  try:
   with urlopen(req,timeout=8) as r:result=json.loads(r.read(3_000_000))
  except Exception:raise sqlite3.OperationalError('Persistent database unavailable') from None
  self.baton=result.get('baton')
  responses=[]
  for row in result['results']:
   if row['type']=='error':
    code=row.get('error',{}).get('code','')
    if 'CONSTRAINT' in code:raise sqlite3.IntegrityError('Database constraint rejected request')
    raise sqlite3.OperationalError('Database query failed')
   responses.append(row.get('response',{}).get('result',{}))
  return responses
 def execute(self,sql,args=()):
  if self.closed:raise sqlite3.OperationalError('Closed connection')
  is_write=sql.lstrip().upper().startswith(('INSERT','UPDATE','DELETE','REPLACE'))
  if is_write and not self.transaction:
   self.pipeline([{'type':'execute','stmt':{'sql':'BEGIN IMMEDIATE'}}]);self.transaction=True
  return Cursor(self.pipeline([{'type':'execute','stmt':{'sql':sql,'args':[encode(x) for x in args],'want_rows':True}}])[0])
 def executescript(self,sql):
  for statement in sql.split(';'):
   if statement.strip():self.execute(statement)
 def commit(self):
  if self.transaction:self.pipeline([{'type':'execute','stmt':{'sql':'COMMIT'}}]);self.transaction=False
 def rollback(self):
  if self.transaction:self.pipeline([{'type':'execute','stmt':{'sql':'ROLLBACK'}}]);self.transaction=False
 def close(self):
  if self.closed:return
  try:
   if self.transaction:self.rollback()
   if self.baton:self.pipeline([{'type':'close'}])
  finally:self.closed=True

def connect(path,schema):
 remote=bool(os.getenv('LIBSQL_URL'));key=os.getenv('LIBSQL_URL') or str(path)
 if os.getenv('VANTIX_ENV')=='production' and not remote:raise sqlite3.OperationalError('Production requires a persistent remote database')
 c=Remote() if remote else sqlite3.connect(path,timeout=10)
 if not remote:c.row_factory=sqlite3.Row;c.execute('PRAGMA foreign_keys=ON')
 try:
  with SCHEMA_LOCK:
   if key not in READY:c.executescript(schema);c.commit();READY.add(key)
 except Exception:c.close();raise
 if not hasattr(ACTIVE,'connections'):ACTIVE.connections=[]
 ACTIVE.connections.append(c);return c

def cleanup():
 for c in getattr(ACTIVE,'connections',[]):
  try:c.close()
  except Exception:pass
 ACTIVE.connections=[]
