"""Read-only GMGN OpenAPI adapter. Trading and private keys are intentionally excluded."""
import json, os, threading, time, uuid
from urllib.parse import urlencode
from urllib.request import Request, urlopen

import free_data

HOST='https://openapi.gmgn.ai'
CHAINS=('sol','bsc','base','eth')
INTERVALS=('1m','5m','1h','6h','24h')
QUOTE_TYPES={'sol':[4,5,3,1,13,0],'bsc':[6,7,1,16,8,3,9,10,2,17,18,0],'base':[11,3,12,13,0],'eth':[20,11,8,3,12,1,0]}
RATE_LOCK=threading.Lock()
LAST_REQUEST=0.0

def configured():return bool(os.getenv('GMGN_API_KEY','').strip())
def num(value):
 try:return free_data.number(value)
 except (TypeError,ValueError):return None
def text(value,limit=200):return str(value or '')[:limit]
def token_link(chain,address):
 allowed=address and len(address)<=64 and all(c.isalnum() or c in '_-' for c in address)
 return 'https://gmgn.ai/'+chain+'/token/'+address if allowed else 'https://gmgn.ai/'

def request(method,path,query=None,body=None):
 global LAST_REQUEST
 key=os.getenv('GMGN_API_KEY','').strip()
 if not key:raise ValueError('GMGN API key is not configured')
 params={**(query or {}),'timestamp':int(time.time()),'client_id':str(uuid.uuid4())}
 url=HOST+path+'?'+urlencode(params,doseq=True)
 payload=json.dumps(body,separators=(',',':')).encode() if body is not None else None
 with RATE_LOCK:
  wait=1-(time.monotonic()-LAST_REQUEST)
  if wait>0:time.sleep(wait)
  LAST_REQUEST=time.monotonic()
 with urlopen(Request(url,data=payload,method=method,headers={'X-APIKEY':key,'Content-Type':'application/json','User-Agent':'VANTIX/1.0'}),timeout=4) as response:
  raw=response.read(2_000_001)
 if len(raw)>2_000_000:raise ValueError('GMGN response too large')
 envelope=json.loads(raw)
 if not isinstance(envelope,dict) or envelope.get('code')!=0 or not isinstance(envelope.get('data'),dict):raise ValueError('GMGN returned an invalid response')
 return envelope['data']

def normalized(row,chain,fresh=False):
 address=text(row.get('address'),64)
 item={'address':address,'chain':chain,'symbol':text(row.get('symbol'),32),'name':text(row.get('name'),120),'platform':text(row.get('launchpad_platform'),60),'exchange':text(row.get('exchange'),60),'link':token_link(chain,address),'source':'GMGN OpenAPI','status':'PROVIDER_QUERY'}
 fields={'price':'price','market_cap':'usd_market_cap' if fresh else 'market_cap','liquidity':'liquidity','volume':'volume_1h' if fresh else 'volume','price_change':'price_change_percent','holders':'holder_count','swaps':'swaps_1m' if fresh else 'swaps','rug_ratio':'rug_ratio','top10_rate':'top_10_holder_rate','insider_rate':'rat_trader_amount_rate','bundler_rate':'bundler_trader_amount_rate' if fresh else 'bundler_rate','smart_money':'smart_degen_count','kol_count':'renowned_count'}
 for target,source in fields.items():item[target]=num(row.get(source))
 item['created_at']=num(row.get('created_timestamp' if fresh else 'creation_timestamp'))
 item['honeypot']=text(row.get('is_honeypot'),12) or None
 item['wash_trading']=row.get('is_wash_trading') if isinstance(row.get('is_wash_trading'),bool) else None
 item['rank']=num(row.get('rank'))
 return item

def unavailable(kind):
 return {'data':[],'source':'GMGN OpenAPI','source_url':'https://gmgn.ai/ai','status':'UNCONFIGURED','checked_at':free_data.stamp(),'retrieved_at':None,'message':'GMGN read-only API is ready but the site owner must add GMGN_API_KEY in Render.','error_code':'NOT_CONFIGURED','kind':kind}

def trending(chain='sol',interval='5m'):
 if chain not in CHAINS or interval not in INTERVALS:raise ValueError('Unsupported GMGN chain or interval')
 if not configured():return unavailable('trending')
 url='https://gmgn.ai/ai'
 def load():
  data=request('GET','/v1/market/rank',{'chain':chain,'interval':interval,'limit':30,'order_by':'volume','direction':'desc'})
  rows=data.get('rank')
  if not isinstance(rows,list):raise ValueError('GMGN rank list missing')
  return [normalized(x,chain) for x in rows[:30] if isinstance(x,dict)]
 return {**free_data.cached('gmgn-trending-'+chain+'-'+interval,'GMGN OpenAPI',url,load,30,'PROVIDER_QUERY'),'kind':'trending','chain':chain,'interval':interval}

def fresh(chain='sol'):
 if chain not in CHAINS:raise ValueError('Unsupported GMGN chain')
 if not configured():return unavailable('fresh')
 url='https://gmgn.ai/ai'
 section={'filters':['offchain','onchain'],'launchpad_platform_v2':True,'limit':30,'quote_address_type':QUOTE_TYPES[chain]}
 def load():
  data=request('POST','/v1/trenches',{'chain':chain},{'version':'v2','new_creation':section})
  rows=data.get('new_creation')
  if not isinstance(rows,list):raise ValueError('GMGN new-token list missing')
  return [normalized(x,chain,True) for x in rows[:30] if isinstance(x,dict)]
 return {**free_data.cached('gmgn-fresh-'+chain,'GMGN OpenAPI',url,load,30,'PROVIDER_QUERY'),'kind':'fresh','chain':chain}
