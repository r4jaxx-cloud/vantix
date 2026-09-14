"""Real browser regressions against local fixtures; external market services mocked."""
import tempfile,threading,re,hashlib
from pathlib import Path
from playwright.sync_api import sync_playwright
import server,free_data
server.DB=Path(tempfile.mkdtemp())/'browser.db';server.db().close()
free_data.fetch=lambda *a: (_ for _ in ()).throw(OSError('offline fixture'))
s=server.BoundedServer(('127.0.0.1',0),server.H);threading.Thread(target=s.serve_forever,daemon=True).start();base='http://127.0.0.1:'+str(s.server_port)
try:
 with sync_playwright() as p:
  browser=p.chromium.launch();page=browser.new_page();errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
  page.route('https://s3.tradingview.com/**',lambda r:r.fulfill(content_type='application/javascript',body='window.chartLoaded=true;'))
  page.goto(base+'/');page.get_by_role('button',name='World news',exact=True).click();page.wait_for_url('**/news')
  page.goto(base+'/markets');page.wait_for_function('window.chartLoaded===true');assert page.locator('[onclick]').count()==0
  assert "script-src-attr 'none'" in page.request.get(base+'/').headers['content-security-policy']
  page.evaluate("document.body.insertAdjacentHTML('beforeend','<img src=x onerror=\"window.injected=true\">')")
  page.wait_for_timeout(100);assert page.evaluate('window.injected!==true')
  page.goto(base+'/account');page.locator('[data-command="registerUser()"]').wait_for()
  escaped=page.evaluate('esc(\'<img src=x onerror="alert(1)">\')');assert '&lt;img' in escaped
  assert page.evaluate("safeLink('https://user:pass@example.com')")==''
  page.evaluate("dispatchCommand(\"go('/crypto')\")");page.wait_for_url('**/crypto')
  page.evaluate("dispatchCommand(\"go('/trending')\")");page.wait_for_url('**/trending')
  page.get_by_role('heading',name='Trending & Fresh Coins').wait_for()
  assert 'not a recommendation' in page.locator('#page').inner_text()
  assert not errors,errors;browser.close();print('Browser CSP, navigation, charts and escaping regressions passed')
finally:s.shutdown();s.server_close()
