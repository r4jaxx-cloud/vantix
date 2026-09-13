import os,json
from urllib.request import Request,urlopen

def configured():return bool(os.getenv('BREVO_API_KEY') and os.getenv('MAIL_FROM'))
def send(email,subject,text):
 if not configured():return False
 payload={'sender':{'name':'VANTIX','email':os.environ['MAIL_FROM']},'to':[{'email':email}],'subject':subject,'textContent':text}
 try:
  with urlopen(Request('https://api.brevo.com/v3/smtp/email',data=json.dumps(payload).encode(),headers={'api-key':os.environ['BREVO_API_KEY'],'Content-Type':'application/json'}),timeout=10) as r:return 200<=r.status<300
 except Exception:return False


# Bounded background queue keeps account existence and provider latency out of responses.
# Jobs are best-effort in memory; callers can retry if a host restart interrupts delivery.
import queue,threading
_JOBS=queue.Queue(maxsize=32)
_START=threading.Lock()
_STARTED=False
def enqueue(job):
 global _STARTED
 with _START:
  if not _STARTED:
   def worker():
    while True:
     task=_JOBS.get()
     try:task()
     except Exception:
      import operations
      operations.fault('email_job','DELIVERY_FAILED')
     finally:_JOBS.task_done()
   for _ in range(2):threading.Thread(target=worker,daemon=True).start()
   _STARTED=True
 try:_JOBS.put_nowait(job);return True
 except queue.Full:return False
