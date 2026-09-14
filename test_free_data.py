"""Contract and failure tests use fixtures, never production demo data."""
import json, time, unittest
from unittest.mock import patch
import free_data as d

class FreeDataTests(unittest.TestCase):
 def setUp(self):d.CACHE.clear()
 def test_crypto_observation_time_and_quote(self):
  with patch.object(d,'fetch',return_value=json.dumps([{'symbol':'BTCUSDT','lastPrice':'60000','priceChangePercent':'2','quoteVolume':'1000','closeTime':1700000000000}]).encode()):
   result=d.crypto();self.assertEqual(result['data'][0]['quote'],'USDT');self.assertTrue(result['data'][0]['updated'].startswith('2023-'));self.assertEqual(result['status'],'SNAPSHOT')
 def test_fx_is_reference_not_live(self):
  with patch.object(d,'fetch',return_value=b'[{"base":"USD","quote":"GBP","rate":0.75,"date":"2025-01-02"}]'):
   row=d.forex()['data'][0];self.assertEqual(row['status'],'REFERENCE');self.assertEqual(row['updated'],'2025-01-02')
 def test_null_and_latest_economic_observations(self):
  rows=[{'indicator':{'id':'FP.CPI.TOTL.ZG'},'value':v,'date':year} for v,year in [(None,'2026'),(3,'2024'),(2,'2025')]]
  with patch.object(d,'fetch',return_value=json.dumps([{},rows]).encode()):
   result=d.economy();self.assertEqual(len(result['data']),1);self.assertEqual(result['data'][0]['value'],2);self.assertEqual(result['status'],'ANNUAL')
 def test_failure_does_not_invent_data(self):
  with patch.object(d,'fetch',side_effect=OSError('offline')):
   self.assertEqual(d.forex()['status'],'UNAVAILABLE');self.assertEqual(d.forex()['data'],[])
 def test_stale_preserves_original_retrieval_and_observation(self):
  r=d.cached('test','source','https://example.com',lambda:[{'updated':'2024','value':12}],0)
  def fail():raise OSError()
  stale=d.cached('test','source','https://example.com',fail,0)
  self.assertEqual(stale['retrieved_at'],r['retrieved_at']);self.assertEqual(stale['status'],'STALE');self.assertEqual(stale['data'],r['data'])
 def test_cache_limits_requests(self):
  with patch.object(d,'fetch',return_value=b'[]') as f:d.crypto();d.crypto();self.assertEqual(f.call_count,2)
 def test_rss_external_links_sanitized(self):
  with patch.object(d,'fetch',return_value=b'<rss><channel><item><title>Test</title><link>javascript:alert(1)</link><pubDate>Tue, 01 Jan 2019 00:00:00 GMT</pubDate></item></channel></rss>'):
   row=d.rss('energy')['data'][0];self.assertEqual(row['link'],'');self.assertEqual(row['source'],'US EIA')
 def test_sec_filings(self):
  raw={'name':'Fixture company','filings':{'recent':{'accessionNumber':['0001-22-000001'],'form':['10-K'],'filingDate':['2022-01-02'],'primaryDocument':['report.htm']}}}
  with patch.object(d,'fetch',return_value=json.dumps(raw).encode()):
   row=d.filings('1')['data'][0];self.assertEqual(row['published'],'2022-01-02');self.assertIn('/1/000122000001/report.htm',row['link'])
 def test_untrusted_inputs_rejected(self):
  for f,x in [(d.filings,'https://localhost'),(d.economy,'../../etc')]:
   with self.assertRaises(ValueError):f(x)
 def test_nonfinite_rejected(self):
  with self.assertRaises(ValueError):d.number('NaN')
 def test_usgs_timestamp(self):
  with patch.object(d,'fetch',return_value=json.dumps({'features':[{'properties':{'title':'Fixture event','time':1700000000000,'url':'https://earthquake.usgs.gov/example'}}]}).encode()):
   self.assertTrue(d.events()['data'][0]['published'].startswith('2023-'))

class ProviderConcurrency(unittest.TestCase):
 def slow(self,source):
  time.sleep(0.1);return {'data':[],'source':source,'source_url':'https://example.test','status':'PUBLISHED','checked_at':'2026-09-13T00:00:00+00:00','retrieved_at':None,'message':None,'error_code':None}
 def test_news_sources_do_not_delay_each_other(self):
  started=time.monotonic()
  with patch.object(d,'rss',side_effect=lambda topic:self.slow(topic)),patch.object(d,'events',side_effect=lambda:self.slow('events')),patch.object(d,'world_news',side_effect=lambda:self.slow('world')):
   response=d.news()
  self.assertEqual(len(response['sources']),4);self.assertLess(time.monotonic()-started,0.3)
 def test_market_groups_do_not_delay_each_other(self):
  started=time.monotonic()
  crypto=lambda:(time.sleep(0.1) or {**self.slow('crypto'),'status':'SNAPSHOT','sources':[]})
  with patch.object(d,'crypto',side_effect=crypto),patch.object(d,'forex',side_effect=lambda:self.slow('forex')):
   response=d.market()
  self.assertIn('sources',response);self.assertLess(time.monotonic()-started,0.25)

if __name__=='__main__':unittest.main()
