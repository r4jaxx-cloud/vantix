"""Free public data adapters. No paid keys, synthetic fallbacks or invented timestamps."""
import json, os, re, time, threading, math
from datetime import datetime, timezone
from urllib.parse import urlencode, quote, urlparse
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError
import socket,ssl
from defusedxml import ElementTree as ET
from email.utils import parsedate_to_datetime

CACHE={}
INFLIGHT=set()
LOCK=threading.RLock()
COUNTRIES={'GBR':'United Kingdom','USA':'United States','CHN':'China','DEU':'Germany','JPN':'Japan','IND':'India','WLD':'World'}
INDICATORS={'NY.GDP.MKTP.KD.ZG':'GDP growth (%)','FP.CPI.TOTL.ZG':'Consumer inflation (%)','SL.UEM.TOTL.ZS':'Unemployment (%)','NV.AGR.TOTL.ZS':'Agriculture value added (% GDP)','NV.IND.TOTL.ZS':'Industry value added (% GDP)','NV.SRV.TOTL.ZS':'Services value added (% GDP)'}
RSS={'policy':('Federal Reserve','https://www.federalreserve.gov/feeds/press_all.xml'),'energy':('US EIA','https://www.eia.gov/rss/todayinenergy.xml')}

def stamp():return datetime.now(timezone.utc).isoformat()
def safeurl(value):
    p=urlparse(str(value or ''))
    return str(value) if p.scheme in ('http','https') and p.netloc else ''
def number(value):
    x=float(value)
    if not math.isfinite(x):raise ValueError('Nonfinite data')
    return x

def fetch(url):
    if urlparse(url).scheme!='https':raise ValueError('HTTPS provider required')
    headers={'User-Agent':'VANTIX public information reader','Accept':'application/json, application/xml, text/xml'}
    if 'data.sec.gov/' in url:
        contact=os.getenv('SEC_USER_AGENT','')
        if not contact or '@' not in contact:raise ValueError('SEC requires the site owner to configure an identifying contact address')
        headers['User-Agent']=contact
    with urlopen(Request(url,headers=headers),timeout=8) as r:
        raw=r.read(5_000_001)
    if len(raw)>5_000_000:raise ValueError('Response too large')
    return raw

def failure_details(exc):
    # Fixed messages only: never return raw response bodies or exception URLs.
    if isinstance(exc,HTTPError):
        code='HTTP_'+str(exc.code)
        explanation={401:'Provider requires authentication.',403:'Provider denied the request.',404:'Provider endpoint was not found.',429:'Provider rate limit reached.',451:'Provider reports a legal or regional restriction.'}.get(exc.code,'Provider returned an HTTP error.')
        return code,explanation
    reason=exc.reason if isinstance(exc,URLError) else exc
    if isinstance(reason,(TimeoutError,socket.timeout)):return 'TIMEOUT','Provider did not respond before the timeout.'
    if isinstance(reason,ssl.SSLError):return 'TLS_ERROR','Secure connection to the provider failed.'
    if isinstance(exc,(json.JSONDecodeError,ET.ParseError,UnicodeError)):return 'INVALID_RESPONSE','Provider returned an unreadable response.'
    if isinstance(exc,(ValueError,KeyError,TypeError)):return 'INVALID_DATA','Provider returned unexpected data.'
    return 'CONNECTION_ERROR','Provider connection failed.'

def cached(key,source,url,loader,ttl=300,cadence='PERIODIC'):
    with LOCK:
        old=CACHE.get(key)
        if old and time.monotonic()-old['_checked']<ttl:return {k:v for k,v in old.items() if not k.startswith('_')}
        if key in INFLIGHT:
            return {**({k:v for k,v in old.items() if not k.startswith('_')} if old else {'data':[],'source':source,'source_url':url,'retrieved_at':None,'checked_at':None}),'status':'STALE' if old and old['data'] else 'REFRESHING','message':'Source refresh in progress.'}
        INFLIGHT.add(key)
    checked=stamp()
    try:
        rows=loader()
        if not isinstance(rows,list):raise ValueError('Unexpected provider payload')
        result={'data':rows,'source':source,'source_url':url,'status':cadence if rows else 'EMPTY','checked_at':checked,'retrieved_at':checked,'message':None,'error_code':None}
    except Exception as e:
        error_code,detail=failure_details(e)
        result={'data':old['data'] if old else [],'source':source,'source_url':url,'status':'STALE' if old and old['data'] else 'UNAVAILABLE','checked_at':checked,'retrieved_at':old.get('retrieved_at') if old else None,'error_code':error_code,'message':detail+' '+('Last successful data retained.' if old and old['data'] else 'No observations available.')}
        if isinstance(e,ValueError) and str(e).startswith('SEC requires'):result['message']=str(e)
    with LOCK:
        INFLIGHT.discard(key)
        result['_checked']=time.monotonic();CACHE[key]=result
        if len(CACHE)>150:CACHE.pop(next(iter(CACHE)))
    return {k:v for k,v in result.items() if not k.startswith('_')}

def binance_crypto():
    url='https://data-api.binance.vision/api/v3/ticker/24hr?'+urlencode({'symbols':json.dumps(['BTCUSDT','ETHUSDT','BNBUSDT','SOLUSDT','DOGEUSDT','XRPUSDT','ADAUSDT'],separators=(',',':'))})
    def parse():
        raw=json.loads(fetch(url))
        if not isinstance(raw,list):raise ValueError('Expected ticker list')
        return [{'symbol':x['symbol'][:-4],'price':number(x['lastPrice']),'change':number(x['priceChangePercent']),'volume':number(x['quoteVolume']),'quote':'USDT','source':'Binance','source_url':'https://www.binance.com/en/trade/'+x['symbol'][:-4]+'_USDT','status':'SNAPSHOT','updated':datetime.fromtimestamp(number(x['closeTime'])/1000,timezone.utc).isoformat()} for x in raw if x.get('symbol') in ('BTCUSDT','ETHUSDT','BNBUSDT','SOLUSDT','DOGEUSDT','XRPUSDT','ADAUSDT')]
    return cached('crypto-binance','Binance',url,parse,60,'SNAPSHOT')

TRACKED_CRYPTO=('BTC','ETH','BNB','SOL','DOGE','XRP','ADA')

def bybit_crypto():
    url='https://api.bybit.com/v5/market/tickers?category=spot'
    def parse():
        raw=json.loads(fetch(url))
        if not isinstance(raw,dict) or raw.get('retCode')!=0 or raw.get('result',{}).get('category')!='spot':raise ValueError('Invalid spot response')
        updated=datetime.fromtimestamp(number(raw['time'])/1000,timezone.utc).isoformat()
        rows=[]
        for x in raw['result']['list']:
            symbol=x.get('symbol','')
            if symbol not in [s+'USDT' for s in TRACKED_CRYPTO]:continue
            price=number(x['lastPrice']);volume=number(x['turnover24h'])
            if price<=0 or volume<0:continue
            rows.append({'symbol':symbol[:-4],'price':price,'change':number(x['price24hPcnt'])*100,'volume':volume,'quote':'USDT','source':'Bybit','source_url':'https://www.bybit.com/en/trade/spot/'+symbol[:-4]+'/USDT','status':'SNAPSHOT','updated':updated,'timestamp_kind':'Provider response time'})
        return rows
    return cached('crypto-bybit','Bybit',url,parse,60,'SNAPSHOT')

def crypto():
    # Two independently cached public spot feeds. Prefer fresh observations to stale ones.
    sources=[binance_crypto(),bybit_crypto()];rows=[]
    for symbol in TRACKED_CRYPTO:
        options=[]
        for source in sources:
            for row in source['data']:
                if row['symbol']==symbol:
                    candidate={**row,'retrieved_at':source['retrieved_at'],'status':'STALE' if source['status'] in ('STALE','REFRESHING') else row['status']}
                    options.append(candidate)
        choice=next((r for r in options if r['status']=='SNAPSHOT'),options[0] if options else None)
        if choice:rows.append(choice)
    result={'data':rows,'sources':sources,'source':'Crypto providers','source_url':None,'checked_at':stamp(),'retrieved_at':max((x['retrieved_at'] for x in sources if x.get('retrieved_at')),default=None),'status':'SNAPSHOT' if rows and any(r['status']=='SNAPSHOT' for r in rows) else 'STALE' if rows else 'UNAVAILABLE'}
    with LOCK:CACHE['crypto']={**result,'_checked':time.monotonic()}
    return result

def forex():
    url='https://api.frankfurter.dev/v2/rates?base=USD&quotes=GBP,EUR,JPY,CHF,CAD,AUD&providers=ecb'
    def parse():
        raw=json.loads(fetch(url))
        return [{'symbol':'USD/'+x['quote'],'price':number(x['rate']),'change':None,'quote':x['quote'],'source':'ECB via Frankfurter','source_url':'https://frankfurter.dev/','status':'REFERENCE','updated':x['date']} for x in raw if x.get('base')=='USD' and x.get('quote') in ('GBP','EUR','JPY','CHF','CAD','AUD')]
    return cached('fx','ECB via Frankfurter',url,parse,3600,'REFERENCE')

def rss(topic):
    source,url=RSS[topic]
    def parse():
        root=ET.fromstring(fetch(url));items=root.findall('./channel/item')
        if root.tag!='rss':raise ValueError('Expected RSS')
        return [{'title':i.findtext('title') or 'Untitled release','link':safeurl(i.findtext('link')),'published':i.findtext('pubDate') or None,'source':source,'category':topic,'status':'PUBLISHED'} for i in items[:30]]
    return cached(topic,source,url,parse,300,'PUBLISHED')

def events():
    url='https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/significant_week.geojson'
    def parse():
        raw=json.loads(fetch(url))
        return [{'title':x['properties']['title'],'link':safeurl(x['properties']['url']),'published':datetime.fromtimestamp(number(x['properties']['time'])/1000,timezone.utc).isoformat(),'source':'USGS','category':'world','status':'REPORTED'} for x in raw['features'][:30]]
    return cached('events','USGS',url,parse,120,'REPORTED')

def economy(country='GBR',sector=False):
    if country not in COUNTRIES:raise ValueError('Unsupported country')
    codes=list(INDICATORS)[3:] if sector else list(INDICATORS)[:3]
    url='https://api.worldbank.org/v2/country/'+country+'/indicator/'+';'.join(codes)+'?source=2&format=json&per_page=1000&mrnev=1'
    def parse():
        raw=json.loads(fetch(url))
        if not isinstance(raw,list) or len(raw)!=2 or not isinstance(raw[1],list):raise ValueError('Invalid observations')
        latest={}
        for x in raw[1]:
            code=x['indicator']['id']
            if x.get('value') is None or code not in codes:continue
            if code not in latest or str(x['date'])>latest[code]['updated']:
                latest[code]={'title':INDICATORS[code],'value':number(x['value']),'updated':str(x['date']),'country':COUNTRIES[country],'source':'World Bank, World Development Indicators','link':'https://data.worldbank.org/indicator/'+code,'status':'ANNUAL'}
        return list(latest.values())
    return cached('sector' +country if sector else 'economy'+country,'World Bank',url,parse,86400,'ANNUAL')

def filings(cik):
    if not re.fullmatch(r'\d{1,10}',cik):raise ValueError('Enter a numeric SEC CIK (1–10 digits)')
    cik=cik.zfill(10);url='https://data.sec.gov/submissions/CIK'+cik+'.json'
    def parse():
        raw=json.loads(fetch(url));r=raw['filings']['recent'];rows=[]
        for i,acc in enumerate(r['accessionNumber'][:25]):
            rows.append({'title':raw['name']+' · '+r['form'][i],'published':r['filingDate'][i],'link':'https://www.sec.gov/Archives/edgar/data/'+str(int(cik))+'/'+acc.replace('-','')+'/'+quote(r['primaryDocument'][i],safe=''),'source':'SEC EDGAR','status':'FILED'})
        return rows
    return cached('filings'+cik,'SEC EDGAR',url,parse,600,'FILED')

def market():
    a=crypto();b=forex();rows=[]
    for result in (a,b):
        for row in result['data']:rows.append({**row,'status':'STALE' if result['status']=='STALE' else row['status'],'retrieved_at':result['retrieved_at']})
    return {'data':rows,'sources':a.get('sources',[a])+[b],'checked_at':stamp()}

def news(topic='all'):
    keys=['policy','energy','world'] if topic=='all' else [topic]
    functions=[events if k=='world' else (lambda k=k:rss(k)) for k in keys]
    if 'world' in keys:functions.append(world_news)
    results=[f() for f in functions];rows=[]
    for result in results:
        rows.extend({**r,'status':'STALE' if result['status']=='STALE' else r['status']} for r in result['data'])
    def dated(x):
        try:return parsedate_to_datetime(x['published']).timestamp()
        except Exception:
            try:return datetime.fromisoformat(x['published']).timestamp()
            except Exception:return 0
    rows.sort(key=dated,reverse=True)
    return {'data':rows[:60],'sources':results,'checked_at':stamp()}

def token_pairs(chain,address):
    if chain not in ('bsc','ethereum','solana'):raise ValueError('Choose BNB Chain, Ethereum or Solana')
    if not re.fullmatch(r'0x[a-fA-F0-9]{40}' if chain!='solana' else r'[1-9A-HJ-NP-Za-km-z]{32,44}',address):raise ValueError('Enter a valid token address for the selected chain')
    url='https://api.dexscreener.com/token-pairs/v1/'+chain+'/'+address
    def parse():
        raw=json.loads(fetch(url))
        if not isinstance(raw,list):raise ValueError('Unexpected pair response')
        rows=[]
        for x in raw[:20]:
            if x.get('chainId')!=chain:continue
            rows.append({'title':str(x.get('baseToken',{}).get('symbol','Token'))+'/'+str(x.get('quoteToken',{}).get('symbol','?')),'chain':chain,'pair':x.get('pairAddress'),'price':number(x['priceUsd']) if x.get('priceUsd') is not None else None,'liquidity':number(x['liquidity']['usd']) if isinstance(x.get('liquidity'),dict) and x['liquidity'].get('usd') is not None else None,'link':safeurl(x.get('url')),'source':'DEX Screener','status':'PROVIDER_SNAPSHOT','updated':None})
        return rows
    return cached('dex-'+chain+'-'+address,'DEX Screener',url,parse,120,'PROVIDER_SNAPSHOT')

def token_security(chain,address):
    if chain not in ('1','56'):raise ValueError('Choose Ethereum or BNB Chain for this security check')
    if not re.fullmatch(r'0x[a-fA-F0-9]{40}',address):raise ValueError('Enter a valid EVM contract address')
    address=address.lower();url='https://api.gopluslabs.io/api/v1/token_security/'+chain+'?contract_addresses='+address
    def parse():
        raw=json.loads(fetch(url))
        if raw.get('code')!=1:raise ValueError('Security source rejected request')
        row=raw.get('result',{}).get(address)
        if not isinstance(row,dict) or not row:return []
        fields={'is_honeypot':'Honeypot flag','is_mintable':'Mintable flag','is_proxy':'Proxy contract','is_blacklisted':'Blacklist capability','can_take_back_ownership':'Ownership reclaim flag','is_open_source':'Open-source contract'}
        return [{'title':label,'field':key,'value':'Yes' if row.get(key)=='1' else 'No' if row.get(key)=='0' else 'Unknown','source':'GoPlus Security','status':'REPORTED','link':'https://gopluslabs.io/token-security/'+chain+'/'+address} for key,label in fields.items()]
    r=cached('security-'+chain+'-'+address,'GoPlus Security',url,parse,600,'REPORTED')
    return {**r,'status':'EVIDENCE_RETURNED' if r['data'] and r['status']=='REPORTED' else 'UNKNOWN','message':'Provider-reported flags, not a safety verdict. No single check rules out a scam. Missing fields remain unknown.' if r['data'] and r['status']=='REPORTED' else 'Fresh security evidence unavailable. Do not treat this as a safe result.'}

def world_news():
    url='https://api.gdeltproject.org/api/v2/doc/doc?'+urlencode({'query':'(economy OR markets OR geopolitics OR climate)','mode':'artlist','format':'json','maxrecords':30,'sort':'datedesc','timespan':'24h'})
    def parse():
        raw=json.loads(fetch(url));articles=raw.get('articles')
        if not isinstance(articles,list):raise ValueError('Unexpected news response')
        rows=[]
        for x in articles[:30]:
            link=safeurl(x.get('url'))
            if not link:continue
            rows.append({'title':str(x.get('title','Untitled'))[:500],'link':link,'published':None,'seen_at':x.get('seendate'),'source':str(x.get('domain','Publisher'))+' via GDELT','category':'world','status':'INDEXED'})
        return rows
    return cached('world-news','GDELT news index',url,parse,900,'INDEXED')

