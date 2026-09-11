import os,json
from urllib.request import Request,urlopen

def configured():return bool(os.getenv('BREVO_API_KEY') and os.getenv('MAIL_FROM'))
def send(email,subject,text):
 if not configured():return False
 payload={'sender':{'name':'VANTIX','email':os.environ['MAIL_FROM']},'to':[{'email':email}],'subject':subject,'textContent':text}
 try:
  with urlopen(Request('https://api.brevo.com/v3/smtp/email',data=json.dumps(payload).encode(),headers={'api-key':os.environ['BREVO_API_KEY'],'Content-Type':'application/json'}),timeout=10) as r:return 200<=r.status<300
 except Exception:return False
