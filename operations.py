"""Bounded background checks and sanitized diagnostics; never edits application code."""
import threading,time,json
from collections import deque
from datetime import datetime,timezone,timedelta
import free_data,storage
LOCK=threading.Lock()
STOP=threading.Event()
THREAD=None
STATE={'started_at':None,'last_cycle':None,'database':'NOT_CHECKED','checks':{},'errors':deque(maxlen=100)}
def stamp():return datetime.now(timezone.utc).isoformat()
def fault(area,code):
 # Never retain request bodies, URLs/query strings, email addresses, keys or exception text.
 with LOCK:STATE['errors'].append({'at':stamp(),'area':area[:40],'code':code[:60]})
def snapshot():
 with LOCK:result={**STATE,'checks':{k:dict(v) for k,v in STATE['checks'].items()},'errors':list(STATE['errors'])}
 result['running']=bool(THREAD and THREAD.is_alive())
 result['note']='Runs only while this server is awake. Retries public reads with backoff; records price alerts; never modifies code. This is not an external uptime monitor.'
 return result

def cycle(connect,tasks=None,clock=time.monotonic):
 tasks=tasks or {'crypto':free_data.crypto,'fx':free_data.forex,'news':free_data.news}
 for name,task in tasks.items():
  with LOCK:old=dict(STATE['checks'].get(name,{}))
  if clock()<old.get('next_due',0):continue
  try:
   result=task();status=result.get('status')
   if 'sources' in result:healthy=bool(result['sources']) and all(x.get('status') not in ('UNAVAILABLE','STALE','REFRESHING') for x in result['sources'])
   else:healthy=status not in ('UNAVAILABLE','STALE','REFRESHING',None)
   code='OK' if healthy else 'SOURCE_UNAVAILABLE'
  except Exception:healthy=False;code='SOURCE_EXCEPTION'
  failures=0 if healthy else old.get('failures',0)+1
  delay=60 if healthy else min(3600,60*2**min(failures,6))
  with LOCK:STATE['checks'][name]={'status':code,'checked_at':stamp(),'failures':failures,'next_due':clock()+delay,'retry_seconds':delay}
  if not healthy:fault(name,code)
 try:
  c=connect();c.execute('SELECT 1').fetchone()
  try:
   from launch_features import evaluate_alerts
   created=evaluate_alerts(c)
   with LOCK:STATE['checks']['alerts']={'status':'OK','checked_at':stamp(),'created':created}
  except Exception:
   c.rollback()
   with LOCK:STATE['checks']['alerts']={'status':'FAILED','checked_at':stamp()}
   fault('alerts','ALERT_CHECK_FAILED')
  with LOCK:STATE['database']='OK';STATE['last_cycle']=stamp()
  payload=snapshot();payload.pop('running',None)
  c.execute('INSERT INTO operation_runs(created_at,payload) VALUES(?,?)',(stamp(),json.dumps(payload)))
  c.execute('DELETE FROM operation_runs WHERE created_at<?',((datetime.now(timezone.utc)-timedelta(days=7)).isoformat(),));c.commit();c.close()
 except Exception:
  with LOCK:STATE['database']='UNAVAILABLE';STATE['last_cycle']=stamp()
  fault('database','DATABASE_UNAVAILABLE')
 finally:storage.cleanup()
def run(connect):
 while not STOP.is_set():
  try:cycle(connect)
  except Exception:fault('monitor','MONITOR_CYCLE_FAILED')
  STOP.wait(60)
def start(connect):
 global THREAD
 with LOCK:
  if THREAD and THREAD.is_alive():return
  STOP.clear();STATE['started_at']=stamp();THREAD=threading.Thread(target=run,args=(connect,),name='vantix-monitor',daemon=True);THREAD.start()
