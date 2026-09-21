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
  page.goto(base+'/');assert page.locator('#globalSearchResults').is_hidden()
  page.locator('#globalSearchInput').fill('bitcoin');page.locator('#globalSearchResults').wait_for();assert 'Bitcoin' in page.locator('#globalSearchResults').inner_text()
  page.locator('#globalSearchInput').fill('');assert page.locator('#globalSearchResults').is_hidden()
  page.locator('a[data-route="/radar"]').click();page.wait_for_url('**/radar')
  persisted=page.evaluate("""()=>{marketData=[{symbol:'BTC',price:60000,change:4,volume:100000,quote:'USDT',source:'fixture',status:'LIVE',updated:'now'}];applyRadarFilters();document.querySelector('.radarRow').open=true;applyRadarFilters();return document.querySelector('.radarRow').open}""");assert persisted
  page.get_by_role('button',name='Open live chart').click();page.wait_for_url('**/crypto');assert page.locator('.chartWorkspace').count()==1
  page.goto(base+'/markets');page.wait_for_function('window.chartLoaded===true');assert page.locator('[onclick]').count()==0
  page.locator('#chartSearch').fill('ethereum');assert page.locator('#chartAsset option').count()==1
  page.get_by_role('button',name='+ Compare',exact=True).click();assert page.locator('.chartCard').count()==2
  page.locator('#chartStyle').select_option('2');assert page.locator('.chartHost script').first.text_content().find('"style":"2"')>=0
  page.locator('.chartCard').first.get_by_role('button',name='Price alert',exact=True).click()
  page.locator('#quickAlertPrice').fill('90000')
  page.route('**/api/saved/add',lambda r:r.fulfill(content_type='application/json',body='{"ok":true}'))
  with page.expect_request('**/api/saved/add') as save:
   page.get_by_role('button',name='Save alert',exact=True).click()
  assert save.value.post_data_json=={'kind':'alerts','symbol':'BTC','value':90000}
  page.get_by_text('Alert saved. View it on your Alerts page.',exact=True).wait_for()
  page.locator('#marketToolDialog').get_by_role('button',name='Close',exact=True).click()
  page.evaluate("newsData=[{title:'Bitcoin policy update',source:'Fixture',category:'finance',link:'https://example.com',published:'now',status:'PUBLISHED'}]")
  page.locator('.chartCard').first.get_by_role('button',name='Related news',exact=True).click()
  page.locator('#marketToolDialog').get_by_role('button',name='Bitcoin policy update',exact=False).click()
  assert page.locator('#marketToolDialog').get_by_text('Headline-only source record.',exact=False).is_visible()
  assert page.url==base+'/markets'
  page.locator('#marketToolDialog').get_by_role('button',name='Close',exact=True).click()
  assert "script-src-attr 'none'" in page.request.get(base+'/').headers['content-security-policy']
  page.evaluate("document.body.insertAdjacentHTML('beforeend','<img src=x onerror=\"window.injected=true\">')")
  page.wait_for_timeout(100);assert page.evaluate('window.injected!==true')
  page.goto(base+'/account');page.locator('[data-command="registerUser()"]').wait_for()
  escaped=page.evaluate('esc(\'<img src=x onerror="alert(1)">\')');assert '&lt;img' in escaped
  assert page.evaluate("safeLink('https://user:pass@example.com')")==''
  page.evaluate("dispatchCommand(\"go('/crypto')\")");page.wait_for_url('**/crypto')
  page.evaluate("dispatchCommand(\"go('/trending')\")");page.wait_for_url('**/trending')
  page.get_by_role('heading',name='Trending Coins').wait_for()
  assert 'not a safety guarantee' in page.locator('#page').inner_text()
  page.evaluate("gmgnData.trending=[{symbol:'BTC',name:'Bitcoin',chain:'sol',price_change:4,volume:1000,liquidity:500,market_cap:5000,address:'fixtureAddress'}];gmgnUsable.trending=true;applyGmgnFilters()")
  page.locator('[data-coin-kind="trending"]').click();page.locator('#coinDialog[open]').wait_for();assert 'price move' in page.locator('#coinDialog').inner_text().lower();assert page.locator('#coinDialog').get_by_text('Ask VANTIX').count()==0
  page.route('**/api/notifications',lambda r:r.fulfill(content_type='application/json',body='{"data":[{"id":7,"message":"BTC threshold fixture","source":"fixture","observed_at":"now","read":0}],"unread":1}'))
  page.route('**/api/notifications/read',lambda r:r.fulfill(content_type='application/json',body='{"ok":true}'))
  page.set_viewport_size({'width':390,'height':844})
  page.goto(base+'/alerts');page.get_by_text('BTC threshold fixture',exact=False).wait_for()
  assert page.locator('#savedSymbol').evaluate('(el)=>el.tagName')=='SELECT'
  assert page.locator('#savedSymbol option').count()==12
  assert page.locator('#unreadAlerts').text_content()=='1'
  with page.expect_request('**/api/notifications/read') as acknowledged:
   page.get_by_role('button',name='Mark displayed alerts read').click()
  assert acknowledged.value.post_data_json=={'through':7}
  # Two isolated local accounts: live group delivery, private inbox and shared alert access.
  c=server.db();ids=[]
  for email in ('chat-a@example.test','chat-b@example.test'):
   cur=c.execute('INSERT INTO users(email,password_hash,verified,created_at) VALUES(?,?,1,?)',(email,server.hashpw('chat-fixture-password'),server.iso(server.now())));ids.append(cur.lastrowid)
  c.commit();c.close()
  contexts=[browser.new_context(viewport={'width':390,'height':844}),browser.new_context()]
  for context,email,name,handle in zip(contexts,('chat-a@example.test','chat-b@example.test'),('Chat Alice','Chat Bob'),('chat_alice','chat_bob')):
   assert context.request.post(base+'/api/auth/login',data={'email':email,'password':'chat-fixture-password'}).ok
   assert context.request.post(base+'/api/chat/profile',data={'display_name':name,'handle':handle,'bio':'Market discussion fixture'}).ok
  a=contexts[0].new_page();b=contexts[1].new_page()
  for tab in (a,b):tab.on('pageerror',lambda e:errors.append(str(e)));tab.goto(base+'/feed')
  a.get_by_role('button',name='Groups',exact=True).click();a.get_by_label('New group name').fill('Browser market group');a.get_by_role('button',name='Create group',exact=True).click()
  a.locator('#chatTitle').get_by_text('Browser market group',exact=True).wait_for()
  b.get_by_role('button',name='Groups',exact=True).click();b.get_by_role('button',name='Join group',exact=True).click();b.locator('#chatTitle').get_by_text('Browser market group',exact=True).wait_for()
  a.locator('#chatBody').fill('Live group fixture');a.get_by_role('button',name='Send message',exact=True).click()
  b.locator('#chatMessages').get_by_text('Live group fixture',exact=True).wait_for(timeout=15000)
  a.get_by_role('button',name='People',exact=True).click();a.locator('#memberSearch').fill('chat_bob');a.get_by_role('button',name='Search members',exact=True).click()
  a.locator('#chatPeople').get_by_role('button',name='Follow',exact=True).click();a.locator('#chatPeople').get_by_role('button',name='Unfollow',exact=True).wait_for()
  a.locator('#chatPeople').get_by_role('button',name='Message',exact=True).click();a.locator('#chatTitle').get_by_text('Chat Bob',exact=True).wait_for()
  a.locator('#chatBody').fill('<img src=x onerror=alert(1)> private fixture');a.get_by_role('button',name='Send message',exact=True).click();a.locator('#chatMessages').get_by_text('<img src=x onerror=alert(1)> private fixture',exact=True).wait_for()
  b.get_by_role('button',name='Messages',exact=True).click();b.locator('#chatInbox').get_by_role('button',name='Chat Alice',exact=True).click()
  b.locator('#chatMessages').get_by_text('<img src=x onerror=alert(1)> private fixture',exact=True).wait_for();assert b.locator('#chatMessages img').count()==0
  b.get_by_role('button',name='Block member',exact=True).click();b.get_by_role('button',name='Unblock member',exact=True).wait_for();assert b.locator('#chatSend').is_disabled()
  a.goto(base+'/alerts');a.locator('#savedSymbol').select_option('BTC');a.locator('#savedValue').fill('100000');a.get_by_role('button',name='Add',exact=True).click();a.locator('#savedRows').get_by_text('100000 USDT threshold',exact=False).wait_for()
  assert a.get_by_role('button',name='Register',exact=True).count()==0
  for context in contexts:context.close()
  assert not errors,errors;browser.close();print('Browser search, CSP, navigation, charts and coin-detail regressions passed')
finally:s.shutdown();s.server_close()
