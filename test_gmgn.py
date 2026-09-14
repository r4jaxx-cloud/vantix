"""GMGN adapter tests use fixtures and never contact the provider."""
import os,unittest
from unittest.mock import patch
import free_data,gmgn_service as g

class GMGNTests(unittest.TestCase):
 def setUp(self):free_data.CACHE.clear()
 def test_unconfigured_is_explicit(self):
  with patch.dict(os.environ,{},clear=True):
   result=g.trending();self.assertEqual(result['status'],'UNCONFIGURED');self.assertEqual(result['data'],[])
 def test_trending_normalizes_documented_fields(self):
  row={'address':'abc123','symbol':'WOW','name':'Wow Token','launchpad_platform':'Pump.fun','price':'0.1','market_cap':'1000','liquidity':'500','volume':'900','price_change_percent':'12.5','holder_count':'42','rug_ratio':'0.2','rank':1}
  with patch.dict(os.environ,{'GMGN_API_KEY':'test'}),patch.object(g,'request',return_value={'rank':[row]}):
   result=g.trending('sol','5m');item=result['data'][0]
  self.assertEqual(item['symbol'],'WOW');self.assertEqual(item['market_cap'],1000);self.assertEqual(item['status'],'PROVIDER_QUERY');self.assertNotIn('test',str(result))
 def test_fresh_uses_documented_new_creation_list(self):
  row={'address':'0x'+'a'*40,'symbol':'NEW','usd_market_cap':'1200','swaps_1m':'4','created_timestamp':'1700000000'}
  with patch.dict(os.environ,{'GMGN_API_KEY':'test'}),patch.object(g,'request',return_value={'new_creation':[row]}):
   item=g.fresh('bsc')['data'][0]
  self.assertEqual(item['market_cap'],1200);self.assertEqual(item['swaps'],4);self.assertIn('/bsc/token/',item['link'])
 def test_invalid_filters_rejected_before_request(self):
  with patch.object(g,'request') as request:
   with self.assertRaises(ValueError):g.trending('bad','5m')
   with self.assertRaises(ValueError):g.trending('sol','2m')
   request.assert_not_called()
if __name__=='__main__':unittest.main()
