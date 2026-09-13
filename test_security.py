"""Local regressions: no production accounts or external providers touched."""
import unittest,sqlite3,tempfile,threading,hashlib,json,os
from pathlib import Path
from unittest.mock import patch
from types import SimpleNamespace
from concurrent.futures import ThreadPoolExecutor
import security,server,launch_features,storage
class Security(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.path=Path(self.tmp.name)/'test.db'
  self.schema=Path(__file__).with_name('launch_schema.sql').read_text()
  c=self.connect();c.execute('INSERT INTO users(email,password_hash,verified,created_at) VALUES(?,?,1,?)',('member@example.test',security.hashpw('initial-password'),server.iso(server.now())));c.commit();c.close()
 def tearDown(self):storage.cleanup();self.tmp.cleanup()
 def connect(self):
  c=sqlite3.connect(self.path,timeout=10);c.row_factory=sqlite3.Row;c.executescript(self.schema);return c
 def test_argon_and_legacy(self):
  hashed=security.hashpw('密码 test-password');self.assertTrue(hashed.startswith('$argon2id$'));self.assertTrue(security.checkpw('密码 test-password',hashed));self.assertFalse(security.checkpw('wrong',hashed))
  salt='fixture';old='pbkdf2:600000:'+salt+':'+hashlib.pbkdf2_hmac('sha256',b'old-password',salt.encode(),600000).hex()
  self.assertTrue(security.checkpw('old-password',old));self.assertTrue(security.needs_rehash(old));self.assertFalse(security.checkpw('x','pbkdf2:999999999:s:a'))
 def test_cookie_only(self):
  self.assertEqual(server.request_token(SimpleNamespace(headers={'Authorization':'Bearer x'})),'')
  self.assertEqual(server.request_token(SimpleNamespace(headers={'Cookie':'vantix_session=x'})),'x')
 def test_production_csrf_missing_origin_config(self):
  class H:
   headers={'Origin':'https://attacker.test','Host':'attacker.test','Content-Type':'application/json'}
   def send(self,code,body):self.code=code
   def post_route(self):raise AssertionError('Reached handler')
  h=H()
  with patch.dict(os.environ,{'VANTIX_ENV':'production'},clear=True):server.H.do_POST(h)
  self.assertEqual(h.code,403)
 def test_source_urls(self):
  for value in ['javascript:alert(1)','https://user:pass@example.com','https://example.com:99999','https://example.com\\evil','https://example.com\n@evil.test','//example.com']:
   self.assertEqual(security.safeurl(value),'',value)
  self.assertEqual(security.safeurl('https://example.com/news?q=1'),'https://example.com/news?q=1')
 def test_unicode(self):
  security.validate_body({'body':'日本語 العربية café 👋\nnews','password':'e\u0301Password'})
  for x in ['bad\x00text','bad\u202etext','bad\ud800']:
   with self.assertRaises(ValueError):security.validate_body({'body':x})
 def test_persistent_limits(self):
  for i in range(6):
   c=self.connect();self.assertTrue(security.auth_limit(c,'email@example.test','127.0.0.1','2026-09-13T01:00'));c.close()
  c=self.connect();self.assertFalse(security.auth_limit(c,'email@example.test','127.0.0.1','2026-09-13T01:00'));c.close()
 def test_concurrent_reset_one_winner(self):
  token='fixture-reset';c=self.connect();c.execute('INSERT INTO reset_tokens VALUES(?,?,?)',(hashlib.sha256(token.encode()).hexdigest(),1,'2099-01-01'));c.execute('INSERT INTO sessions VALUES(?,?,?)',('session',1,'2099-01-01'));c.commit();c.close()
  def reset(i):
   c=self.connect()
   try:return launch_features.post(None,'/api/auth/reset',{'token':token,'password':'new-password-'+str(i)},c,None,security.hashpw)[0]
   finally:c.close()
  with ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(reset,[1,2]))
  self.assertEqual(sorted(results),[200,400]);c=self.connect();self.assertEqual(c.execute('SELECT count(*) FROM sessions').fetchone()[0],0);c.close()
 def test_expired_reset(self):
  token='expired';c=self.connect();c.execute('INSERT INTO reset_tokens VALUES(?,?,?)',(hashlib.sha256(token.encode()).hexdigest(),1,'2000-01-01'));c.commit()
  self.assertEqual(launch_features.post(None,'/api/auth/reset',{'token':token,'password':'new-password'},c,None,security.hashpw)[0],400);c.close()
 def test_production_email_response_does_not_query_existence(self):
  import io
  class H:
   client_address=('127.0.0.1',1)
   def send(self,code,body):self.result=(code,json.loads(body))
  results=[]
  for email in ['member@example.test','absent@example.test']:
   h=H();h.path='/api/auth/register';body=json.dumps({'email':email,'password':'valid-password'}).encode();h.headers={'Content-Length':str(len(body))};h.rfile=io.BytesIO(body)
   with patch.dict(os.environ,{'VANTIX_ENV':'production'}),patch('server.db',side_effect=self.connect),patch('mail_service.enqueue',return_value=True):server.H.post_route(h)
   results.append(h.result)
  self.assertEqual(results[0],results[1]);self.assertEqual(results[0][0],200)
 def test_audit_excludes_secrets(self):
  c=self.connect();security.audit(c,'password_reset',1);row=dict(c.execute('SELECT * FROM security_audit').fetchone());self.assertEqual(set(row),{'id','event','user_id','created_at'});c.close()
 def test_ip_not_stored_in_limit_keys(self):
  ip='192.0.2.123';server.AUTH_LIMITS.clear();server.auth_allowed(ip)
  self.assertNotIn(ip,str(server.AUTH_LIMITS))
  c=self.connect();security.auth_limit(c,'member@example.test',ip,'2026-09-13T02:00')
  self.assertNotIn(ip,str([tuple(r) for r in c.execute('SELECT * FROM limits')]));c.close()
 def test_generic_error_no_secret(self):
  class H:
   def get_route(self):raise RuntimeError('password=private-secret database-host')
   def send(self,code,body):self.result=(code,body)
  h=H();server.H.do_GET(h);self.assertEqual(h.result[0],503);self.assertNotIn('private-secret',h.result[1])
 def test_sql_kind_whitelist(self):
  c=self.connect();u=c.execute('SELECT * FROM users').fetchone()
  result=launch_features.get(None,'/api/saved',{'kind':["watchlist' OR 1=1 --"]},c,u)
  self.assertEqual(result[0],400);self.assertEqual(c.execute('SELECT count(*) FROM users').fetchone()[0],1);c.close()
if __name__=='__main__':unittest.main()
