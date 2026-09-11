import unittest,sqlite3,json
from pathlib import Path
from unittest.mock import patch
import operations,owner_reports,free_data
class Operations(unittest.TestCase):
 def setUp(self):
  self.c=sqlite3.connect(':memory:');self.c.row_factory=sqlite3.Row;self.c.executescript(Path(__file__).with_name('launch_schema.sql').read_text())
  self.c.execute("INSERT INTO users(id,email,password_hash,verified,created_at) VALUES(1,'owner@example.test','NEVER_EXPORT',1,'2026-09-11')");self.c.commit()
  operations.STATE['checks']={};operations.STATE['errors'].clear();free_data.CACHE.clear()
 def tearDown(self):self.c.close()
 def test_csv_excludes_credentials(self):
  _,_,text=owner_reports.report(self.c,'accounts');self.assertIn('owner@example.test',text);self.assertNotIn('NEVER_EXPORT',text);self.assertNotIn('password',text)
 def test_formula_injection(self):
  self.assertEqual(owner_reports.cell('  =HYPERLINK("bad")'),'\'  =HYPERLINK("bad")');self.assertEqual(owner_reports.cell('@SUM(1)'),"'@SUM(1)")
 def test_pagination(self):self.assertNotIn('owner@example.test',owner_reports.report(self.c,'accounts',1)[2])
 def test_report_real_counts(self):self.assertIn('Registered accounts,1',owner_reports.report(self.c,'summary')[2])
 def test_retry_backoff_without_exception_secrets(self):
  def fail():raise ValueError('secret-value')
  # Database connection intentionally fails; monitor must still retain source failure state.
  def dbfail():raise OSError('db-secret')
  operations.cycle(dbfail,{'fixture':fail},lambda:100)
  first=operations.snapshot();self.assertEqual(first['checks']['fixture']['failures'],1)
  operations.cycle(dbfail,{'fixture':fail},lambda:101)
  self.assertEqual(operations.snapshot()['checks']['fixture']['failures'],1)
  operations.cycle(dbfail,{'fixture':lambda:{'status':'PUBLISHED'}},lambda:1000)
  result=operations.snapshot();self.assertEqual(result['checks']['fixture']['failures'],0);self.assertNotIn('secret',json.dumps(result))
 def test_missing_security_unknown(self):
  with patch('free_data.fetch',return_value=b'{"code":1,"result":{}}'):self.assertEqual(free_data.token_security('56','0x'+'1'*40)['status'],'UNKNOWN')
 def test_security_fields_missing_not_safe(self):
  address='0x'+'1'*40
  with patch('free_data.fetch',return_value=json.dumps({'code':1,'result':{address:{'is_honeypot':'0'}}}).encode()):
   x=free_data.token_security('56',address);self.assertEqual(x['status'],'EVIDENCE_RETURNED');self.assertTrue(any(r['value']=='Unknown' for r in x['data']));self.assertNotIn('SAFE',json.dumps(x))
 def test_pair_timestamp_not_invented(self):
  data=[{'chainId':'bsc','baseToken':{'symbol':'ABC'},'quoteToken':{'symbol':'USDT'},'priceUsd':'2','url':'https://dexscreener.com/bsc/fixture'}]
  with patch('free_data.fetch',return_value=json.dumps(data).encode()):
   row=free_data.token_pairs('bsc','0x'+'1'*40)['data'][0];self.assertIsNone(row['updated']);self.assertEqual(row['price'],2)
 def test_news_index_date_not_publication_date(self):
  data={'articles':[{'url':'https://example.test/news','title':'Fixture','seendate':'20260911T000000Z','domain':'example.test'}]}
  with patch('free_data.fetch',return_value=json.dumps(data).encode()):
   row=free_data.world_news()['data'][0];self.assertIsNone(row['published']);self.assertEqual(row['status'],'INDEXED')
if __name__=='__main__':unittest.main()
