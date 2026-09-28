"""Browser regression checks for the isolated concept preview."""
import functools, http.server, pathlib, threading, unittest
from playwright.sync_api import sync_playwright
ROOT=pathlib.Path(__file__).resolve().parent
class PreviewTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.http=http.server.ThreadingHTTPServer(('127.0.0.1',0),functools.partial(http.server.SimpleHTTPRequestHandler,directory=str(ROOT/'dist')))
  threading.Thread(target=cls.http.serve_forever,daemon=True).start()
  cls.pw=sync_playwright().start();cls.browser=cls.pw.chromium.launch()
  cls.url=f'http://127.0.0.1:{cls.http.server_port}/'
 @classmethod
 def tearDownClass(cls):
  cls.browser.close();cls.pw.stop();cls.http.shutdown();cls.http.server_close()
 def test_preview(self):
  page=self.browser.new_page(viewport={'width':1440,'height':1000});errors=[]
  page.on('pageerror',lambda e:errors.append(str(e)))
  page.goto(self.url)
  page.locator('.heroCity').wait_for()
  self.assertTrue(page.locator('.heroCity').evaluate('(i)=>i.complete && i.naturalWidth>0'))
  page.screenshot(path=str(ROOT/'welcome-preview.png'),full_page=True)
  page.get_by_role('button',name='Sign Up',exact=True).click()
  self.assertTrue(page.get_by_text('Public accounts are not open yet.',exact=False).is_visible())
  self.assertEqual(page.locator('input[type=password]').count(),0)
  page.get_by_role('button',name='Close dialog').click()
  for route in ['feed','network','jobs','communities','events','marketplace','messages','profile','saved','world','security']:
   page.goto(self.url+'#'+route)
   page.locator('main h1').wait_for()
   self.assertFalse(page.evaluate('document.documentElement.scrollWidth > innerWidth'),route)
   if route in ['feed','world','profile','jobs','messages']:
    page.screenshot(path=str(ROOT/(route+'-preview.png')),full_page=True)
  page.goto(self.url+'#feed')
  page.get_by_role('textbox',name='Write a post').fill('<img src=x onerror="alert(1)"> Preview post')
  page.get_by_role('button',name='Post',exact=True).click()
  self.assertTrue(page.get_by_text('<img src=x onerror="alert(1)"> Preview post',exact=True).is_visible())
  self.assertEqual(page.locator('.bodyText img').count(),0)
  page.locator('[data-action="save"]').first.click()
  page.goto(self.url+'#saved');self.assertEqual(page.locator('.post').count(),1)
  page.goto(self.url+'#network')
  page.get_by_role('button',name='Follow Emma Taylor',exact=True).click()
  self.assertTrue(page.get_by_role('button',name='Unfollow Emma Taylor',exact=True).is_visible())
  page.get_by_role('textbox',name='Filter people').fill('insurance')
  page.locator('#networkFilter').get_by_role('button',name='Search',exact=True).click()
  self.assertEqual(page.locator('.personCard').count(),1)
  page.locator('#globalSearch').fill('developer');page.locator('#searchForm').evaluate('(f)=>f.requestSubmit()')
  self.assertTrue(page.get_by_role('heading',name='Search results').is_visible())
  self.assertTrue(page.get_by_text('Emma Taylor',exact=True).first.is_visible())
  page.goto(self.url+'#profile');page.get_by_role('button',name='Edit profile',exact=True).click()
  page.get_by_role('textbox',name='Display name',exact=True).fill('Demo Person')
  page.get_by_role('button',name='Save preview profile').click()
  self.assertTrue(page.get_by_role('heading',name='Demo Person',exact=True).is_visible())
  page.reload();self.assertTrue(page.get_by_role('heading',name='Demo Person',exact=True).is_visible())
  page.goto(self.url+'#messages');page.get_by_role('textbox',name='Write a sample message').fill('Sample, not delivered')
  page.get_by_role('button',name='Save sample message').click()
  self.assertTrue(page.get_by_text('Sample, not delivered',exact=True).is_visible())
  page.goto(self.url+'#world');page.get_by_role('button',name='Jobs Hub',exact=True).click()
  self.assertTrue(page.get_by_role('link',name='Explore opportunities').is_visible())
  page.set_viewport_size({'width':390,'height':844})
  for route in ['welcome','feed','network','jobs','communities','events','marketplace','messages','profile','world','security']:
   page.goto(self.url+'#'+route);page.locator('main h1').wait_for()
   self.assertFalse(page.evaluate('document.documentElement.scrollWidth > innerWidth'),route+' mobile overflow')
   if route in ['welcome','feed','world','profile']:
    page.screenshot(path=str(ROOT/(route+'-mobile-preview.png')),full_page=True)
  self.assertEqual(errors,[])
  page.close()
if __name__=='__main__':unittest.main()
