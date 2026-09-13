"""Configuration gate, not a substitute for live integration testing."""
import os
import security
from urllib.parse import urlparse

def check():
 errors=[]
 for key in ('LIBSQL_URL','LIBSQL_AUTH_TOKEN','BREVO_API_KEY','MAIL_FROM','SUPPORT_EMAIL','ADMIN_EMAILS','SEC_USER_AGENT'):
  if not os.getenv(key):errors.append(key+' required')
 p=urlparse(os.getenv('VANTIX_PUBLIC_URL',''))
 if not security.safeurl(os.getenv('VANTIX_PUBLIC_URL','')) or p.scheme!='https' or not p.hostname or p.path not in ('','/') or p.query or p.fragment or p.username:errors.append('VANTIX_PUBLIC_URL must be the HTTPS site origin')
 d=urlparse(os.getenv('LIBSQL_URL','').replace('libsql://','https://'))
 if d.scheme!='https' or not d.hostname or not d.hostname.endswith('.turso.io') or d.username or d.password:errors.append('Valid Turso database URL required')
 for key in ('MAIL_FROM','SUPPORT_EMAIL','ADMIN_EMAILS','SEC_USER_AGENT'):
  if os.getenv(key) and '@' not in os.environ[key]:errors.append(key+' must contain a real email contact')
 if os.getenv('FREE_ACCOUNTS_CONFIRMED')!='1':errors.append('Confirm free plans and disable paid upgrades: FREE_ACCOUNTS_CONFIRMED=1')
 return errors
if __name__=='__main__':
 errors=check()
 print('\n'.join(errors) if errors else 'Configuration present. Live database, email, AI and browser checks still required.')
 raise SystemExit(bool(errors))

