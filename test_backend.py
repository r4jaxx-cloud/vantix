import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent))
import importlib.util,tempfile,threading,json,urllib.request,urllib.error, pathlib
spec=importlib.util.spec_from_file_location('app',str(pathlib.Path(__file__).with_name('server.py'))); m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
tmp=tempfile.TemporaryDirectory(); m.DB=pathlib.Path(tmp.name)/'test.db';m.db().close()
server=m.ThreadingHTTPServer(('127.0.0.1',0),m.H);threading.Thread(target=server.serve_forever,daemon=True).start(); base='http://127.0.0.1:'+str(server.server_port)
def call(path,body=None,token=None):
 req=urllib.request.Request(base+path,data=json.dumps(body).encode() if body is not None else None,headers={'Content-Type':'application/json',**({'Cookie':'vantix_session='+token} if token else {})})
 try:r=urllib.request.urlopen(req)
 except urllib.error.HTTPError as e:r=e
 raw=r.read();return r.status,json.loads(raw) if 'application/json' in r.headers.get('Content-Type','') else raw.decode()
checks=[]
def ck(label,condition):
 assert condition,label
 checks.append(label)
try:
 for path in ['/','/markets','/crypto','/trending','/forex','/stocks','/commodities','/economy','/news','/feed','/shield','/radar','/watchlist','/alerts','/research','/copilot','/sectors','/portfolio']:
  ck('Route '+path,call(path)[0]==200)
 ck('Unknown page is 404',call('/page-does-not-exist')[0]==404)
 ck('Invalid email rejected',call('/api/auth/register',{'email':'bad\n@example.test','password':'password123'})[0]==400)
 ck('Oversized password rejected',call('/api/auth/register',{'email':'a@example.test','password':'x'*257})[0]==400)
 ck('Non-object JSON rejected',call('/api/auth/register',[])[0]==400)
 ck('Anonymous account lookup',call('/api/auth/me')[1]['authenticated']==False)
 ck('Anonymous posting denied',call('/api/feed/post',{'body':'test'})[0]==401)
 status,j=call('/api/auth/register',{'email':'preview@example.test','password':'preview-test-password'})
 ck('Registration',status==200)
 ck('Unverified login denied',call('/api/auth/login',{'email':'preview@example.test','password':'preview-test-password'})[0]==403)
 ck('Verification',call('/api/auth/verify?'+j['dev_verification_url'].split('?')[1])[0]==200)
 status,j=call('/api/auth/login',{'email':'preview@example.test','password':'preview-test-password'});token=j['token'];ck('Verified login',status==200)
 ck('Account response excludes password hash','password_hash' not in call('/api/auth/me',token=token)[1]['user'])
 ck('Unsafe source rejected',call('/api/feed/post',{'body':'test','source_url':'javascript:alert(1)'},token)[0]==400)
 status,j=call('/api/feed/post',{'body':'Preview test','source_url':'https://example.com'},token);ck('Verified posting',status==200);pid=j['id']
 ck('Negative comment id rejected',call('/api/feed/comment',{'post_id':-1,'body':'test'},token)[0]==400)
 ck('Malformed comment handled',call('/api/feed/comment',{'post_id':'bad','body':'test'},token)[0]==400)
 ck('Verified comment',call('/api/feed/comment',{'post_id':pid,'body':'test'},token)[0]==200)
 feed=call('/api/feed')[1]['data'];ck('Feed persisted',len(feed)==1 and len(feed[0]['comments_list'])==1);ck('Public feed excludes email','email' not in json.dumps(feed))
 c=m.db();c.execute('UPDATE users SET verified=0');c.commit();c.close()
 ck('Existing session cannot bypass verification',call('/api/feed/post',{'body':'test'},token)[0]==401)
 ck('Logout',call('/api/auth/logout',{},token)[0]==200);ck('Session revoked',not call('/api/auth/me',token=token)[1]['authenticated'])
 ck('AI requires verified account',call('/api/ai',{'question':'Why?'})[0]==401)
 ck('Invalid economic country handled',call('/api/economy?country=INVALID')[0]==400)
 ck('Invalid filing CIK handled',call('/api/filings?cik=invalid')[0]==400)
 ck('Unknown news topic handled',call('/api/news?topic=invalid')[0]==400)
 ck('GMGN is explicit when not configured',call('/api/gmgn/trending')[1]['status']=='UNCONFIGURED')
 ck('Invalid GMGN filters rejected',call('/api/gmgn/trending?chain=bad')[0]==400)
 ck('Unknown API is 404',call('/api/missing')[0]==404)
 ck('Shield defaults unknown',call('/api/shield?token=abc')[1]['status']=='UNKNOWN')
 def fail(*a,**k):raise OSError('Provider unavailable')
 m.fetch=fail
 m.free_data.CACHE.clear();m.free_data.fetch=fail
 ck('Provider failure creates no market data',call('/api/market')[1]['data']==[])
 ck('Provider failure creates no news',call('/api/news')[1]['data']==[])
 print(json.dumps({'passed':len(checks),'checks':checks},indent=2))
 pathlib.Path(__file__).with_name('VALIDATION.json').write_text(json.dumps({'passed':len(checks),'checks':checks,'limits':['No browser visual QA performed','Real provider connectivity not validated','Remote database adapter tested separately; live connection not validated','Not ready for public deployment']},indent=2))
finally:server.shutdown();server.server_close();tmp.cleanup()
