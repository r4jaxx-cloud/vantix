// Interface-logic tests, not a browser or visual-layout test.
const fs=require('fs'),vm=require('vm'),assert=require('assert');
const html=fs.readFileSync(__dirname+'/index.html','utf8');
const nodes=new Map();const data=new Map();let storageBlocked=false;let alerts=[];
function node(id){if(!nodes.has(id))nodes.set(id,{id,value:'',innerHTML:'',textContent:'',style:{},querySelector:()=>null,querySelectorAll:()=>[],insertAdjacentHTML(_p,t){this.innerHTML+=t},append(){},prepend(){},focus(){},setSelectionRange(){}});return nodes.get(id)}
const ctx={console,URL,AbortController,Set,Number,Date,JSON,Array,Error,Promise,document:{getElementById:node,querySelectorAll:()=>[],addEventListener:()=>{},activeElement:null,hidden:false,createElement:()=>({style:{},appendChild(){},querySelector:()=>({appendChild(){},isConnected:true})})},localStorage:{getItem:k=>{if(storageBlocked)throw Error();return data.get(k)||null},setItem:(k,v)=>{if(storageBlocked)throw Error();data.set(k,v)},removeItem:k=>data.delete(k)},alert:x=>alerts.push(x),location:{pathname:'/'},history:{pushState:(_a,_b,path)=>ctx.location.pathname=path},window:{},setTimeout:()=>1,clearTimeout:()=>{},setInterval:()=>1,fetch:async()=>({ok:true,json:async()=>({data:[],sources:[],status:'UNAVAILABLE',authenticated:false})})};
vm.createContext(ctx);vm.runInContext(html.split('<script>')[1].split('</script>')[0],ctx);
let count=0;function check(label,fn){fn();count++;console.log('PASS '+label)}
check('malformed local storage cannot crash page',()=>{data.set('vantix_watch','{bad');assert.equal(vm.runInContext("saved('vantix_watch').length",ctx),0)});
check('non-array local storage is discarded',()=>{data.set('vantix_watch','{}');assert.equal(vm.runInContext("saved('vantix_watch').length",ctx),0)});
check('watchlist injection rejected',()=>{data.set('vantix_watch',JSON.stringify(["');alert(1);//",'BTC']));assert.equal(vm.runInContext("saved('vantix_watch').join(',')",ctx),'BTC')});
check('corrupted holdings rejected',()=>{data.set('vantix_portfolio',JSON.stringify([{symbol:'BTC',qty:-1},{symbol:'ETH',qty:'<img>'},{symbol:'SOL',qty:2}]));assert.equal(vm.runInContext("saved('vantix_portfolio').length",ctx),1)});
check('storage unavailable handled',()=>{storageBlocked=true;assert.equal(vm.runInContext("saved('vantix_watch').length",ctx),0);assert.equal(vm.runInContext("storageSet('x','y')",ctx),false);storageBlocked=false});
check('numeric formatting handles invalid values',()=>{assert.equal(vm.runInContext('money(Infinity)',ctx),'—');assert.equal(vm.runInContext("money('wrong')",ctx),'—')});
check('unsafe URLs rejected',()=>assert.equal(vm.runInContext("safeLink('javascript:alert(1)')",ctx),''));
check('negative portfolio quantities not saved',()=>{node('portSymbol').value='BTC';node('portQty').value='-4';const old=data.get('vantix_portfolio');vm.runInContext('addHolding()',ctx);assert.equal(data.get('vantix_portfolio'),old)});
check('nonfinite alert thresholds not saved',()=>{node('alertSymbol').value='BTC';node('alertPrice').value='Infinity';vm.runInContext('addAlert()',ctx);assert.equal(data.has('vantix_alerts'),false)});
check('quotes no longer imply USD for USDT',()=>assert(!vm.runInContext('money(123)',ctx).includes('$')));
check('AI response identifies source search',()=>{node('q').value='inflation';vm.runInContext('searchSources()',ctx);assert(node('chat').innerHTML.includes('Source search · no AI interpretation'))});
check('watchlist markup has no injected dynamic script',()=>{ctx.location.pathname='/watchlist';vm.runInContext('render()',ctx);assert(!node('page').innerHTML.includes("removeWatch('"));assert(node('page').innerHTML.includes('savedRows'))});
for(const route of ['/','/ask','/markets','/crypto','/trending','/stocks','/forex','/commodities','/economy','/news','/feed','/radar','/shield','/watchlist','/alerts','/research','/copilot','/sectors','/portfolio','/account','/admin','/reset-password','/privacy','/terms']){check('render logic '+route,()=>{ctx.location.pathname=route;node('countrySelect').value='GBR';vm.runInContext('render()',ctx);assert(node('page').innerHTML.includes('<h1>'))})}
console.log(count+' interface-logic checks passed (no browser rendering).');
