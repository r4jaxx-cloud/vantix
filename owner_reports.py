"""Owner-only CSV and printable HTML reports. Explicit columns exclude credentials."""
import csv,io,html,json
from datetime import datetime,timezone,timedelta
import operations

def cell(value):
 value='' if value is None else str(value)
 # Neutralize spreadsheet formulas, including whitespace-prefixed payloads.
 return "'"+value if value.lstrip().startswith(('=','+','-','@')) or value.startswith(('\t','\r','\n')) else value

def csv_text(columns,rows):
 buf=io.StringIO(newline='');writer=csv.writer(buf);writer.writerow(columns)
 for row in rows:writer.writerow([cell(row.get(k,'')) for k in columns])
 return '\ufeff'+buf.getvalue()

def report(c,kind,after=0):
 if kind=='accounts':
  rows=[dict(r) for r in c.execute("SELECT u.id,u.email,coalesce(p.display_name,'Member '||u.id) display_name,u.verified,coalesce(p.banned,0) suspended,u.created_at,(SELECT max(e.created_at) FROM events e WHERE e.user_id=u.id) last_recorded_action FROM users u LEFT JOIN profiles p ON p.user_id=u.id WHERE u.id>? ORDER BY u.id LIMIT 5000",(after,)).fetchall()]
  return 'text/csv; charset=utf-8','vantix-accounts.csv',csv_text(['id','email','display_name','verified','suspended','created_at','last_recorded_action'],rows)
 cutoff=(datetime.now(timezone.utc)-timedelta(days=30)).isoformat()
 counts=[]
 for label,sql,args in [('Registered accounts','SELECT count(*) n FROM users',()),('Verified accounts','SELECT count(*) n FROM users WHERE verified=1',()),('Community posts','SELECT count(*) n FROM posts',()),('Comments','SELECT count(*) n FROM comments',()),('Open reports',"SELECT count(*) n FROM reports WHERE status='open'",()),('Opted-in page views (30 days)',"SELECT count(*) n FROM events WHERE event='page_view' AND created_at>=?",(cutoff,)),('Opted-in browser visitors (30 days)',"SELECT count(distinct visitor) n FROM events WHERE event='page_view' AND created_at>=?",(cutoff,)),('Active accounts (30 days)','SELECT count(distinct user_id) n FROM events WHERE created_at>=?',(cutoff,))]:
  counts.append({'metric':label,'value':c.execute(sql,args).fetchone()['n']})
 if kind=='summary':return 'text/csv; charset=utf-8','vantix-summary.csv',csv_text(['metric','value'],counts)
 if kind=='daily':
  rows=[dict(r) for r in c.execute("SELECT substr(created_at,1,10) day,event,count(*) events,count(distinct user_id) accounts,count(distinct visitor) browsers FROM events WHERE created_at>=? GROUP BY day,event ORDER BY day DESC,event",(cutoff,)).fetchall()]
  return 'text/csv; charset=utf-8','vantix-daily-usage.csv',csv_text(['day','event','events','accounts','browsers'],rows)
 if kind=='health':
  rows=[dict(r) for r in c.execute('SELECT id,created_at,payload FROM operation_runs WHERE id>? ORDER BY id LIMIT 5000',(after,)).fetchall()]
  return 'text/csv; charset=utf-8','vantix-health.csv',csv_text(['id','created_at','payload'],rows)
 if kind!='print':raise ValueError('Unknown report')
 esc=lambda x:html.escape(str(x));state=operations.snapshot()
 body='<!doctype html><html lang="en"><meta charset="utf-8"><title>VANTIX owner report</title><style>body{font:16px system-ui;max-width:900px;margin:40px auto;padding:20px}td,th{text-align:left;padding:10px;border-bottom:1px solid #ccc}table{width:100%;border-collapse:collapse}@media print{button{display:none}}</style><h1>VANTIX owner report</h1><p>Generated '+esc(datetime.now(timezone.utc).isoformat())+'</p><p>Account/content totals are cumulative. Activity is the last 30 days of retained events. Optional browser analytics undercount visitors and are capped at 2,000 events per day. Active accounts count recorded actions, not all readers.</p><table><tr><th>Metric</th><th>Value</th></tr>'
 body+=''.join('<tr><td>'+esc(r['metric'])+'</td><td>'+esc(r['value'])+'</td></tr>' for r in counts)+'</table><h2>Background checks</h2><p>'+esc(state['note'])+'</p><p>Database: '+esc(state['database'])+' · Last cycle: '+esc(state['last_cycle'])+'</p><table>'
 body+=''.join('<tr><td>'+esc(k)+'</td><td>'+esc(v['status'])+'</td><td>'+esc(v['checked_at'])+'</td></tr>' for k,v in state['checks'].items())+'</table><h2>Recent errors in this process</h2>'
 body+=''.join('<p>'+esc(e['at'])+' · '+esc(e['area'])+' · '+esc(e['code'])+'</p>' for e in state['errors'][-20:])+'<p>Use your browser’s Print command to save this report as PDF.</p></html>'
 return 'text/html; charset=utf-8','vantix-report.html',body
