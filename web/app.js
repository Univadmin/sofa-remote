'use strict';
if(!Element.prototype.replaceChildren)Element.prototype.replaceChildren=function(...children){this.textContent='';this.append(...children)};
const $=s=>document.querySelector(s), $$=s=>[...document.querySelectorAll(s)];
const labels={mouse:'⌖ Mouse',media:'▶ Medya',keyboard:'⌨ Klavye',browser:'▣ Tarayıcı / Sekmeler',apps:'▦ Uygulamalar',commands:'☷ Tüm butonlar',tools:'⚙ Araçlar',downloads:'↻ Güncelleme'};
const storage={get:(key,fallback)=>{try{return JSON.parse(localStorage.getItem(key))??fallback}catch{return fallback}},set:(key,value)=>localStorage.setItem(key,JSON.stringify(value))};
let paneTypes=storage.get('panes',['mouse','media']), shortcuts=[],ws,stopped=false,retry,sequence=0,pending=new Map(),toastTimer,tabsState={tabs:[],connected:false},tabsFingerprint='',fullMouse=storage.get('fullMouse',false),globalMouse=null,checkingUpdates=false,pcPrompted='',restartUntil=0;
const escaped=s=>String(s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const actionButton=(label,action,cls='')=>`<button class="${cls}" data-action="${escaped(JSON.stringify(action))}">${escaped(label)}</button>`;
const keyButton=(label,keys)=>actionButton(label,{type:'keys',keys});
function toast(message){
 const box=$('#toast');box.textContent=message;box.classList.add('show');clearTimeout(toastTimer);
 if(box.showPopover){try{if(box.matches(':popover-open'))box.hidePopover();box.showPopover()}catch{}}
 else {const parent=$('#sheet').open?$('#sheet'):document.body;parent.append(box)}
 toastTimer=setTimeout(()=>{box.classList.remove('show');try{box.hidePopover?.()}catch{}},4500);
}
function status(message,online=false){$('#connection').textContent='● '+message;$('#connection').classList.toggle('online',online)}
async function api(path,options={}){const controller=new AbortController(),timer=setTimeout(()=>controller.abort(),6000);try{const r=await fetch('/api/'+path,{...options,signal:controller.signal});if(!r.ok)throw new Error(await r.text());return await r.json()}finally{clearTimeout(timer)}}

function send(action,wait=false){
  if(ws?.readyState!==1){if(action.type!=='move'&&action.type!=='release')toast('Bilgisayar bağlı değil');return wait?Promise.reject(new Error('Bağlantı yok')):undefined}
  if(['keys','focus','window','launch','url','macro','tab'].includes(action.type)||(action.type==='button'&&action.down))resetTextInputs();
  const id=++sequence;ws.send(JSON.stringify({...action,id}));if(!wait)return;
  return new Promise((resolve,reject)=>{const timer=setTimeout(()=>{pending.delete(id);reject(new Error('Komut zaman aşımı'))},25000);pending.set(id,{resolve,reject,timer})});
}
function resetTextInputs(){window.SofaNative?.resetKeyboard?.();for(const area of $$('.keyboard-live')){area.value='';area.dataset.previous=''}}
function resetLive(){globalMouse?.reset();resetTextInputs();for(const box of $$('[data-drag]'))box.checked=false;for(const pad of $$('.touchpad'))pad.dispatchEvent(new Event('sofa-reset'))}
function connect(){
  clearTimeout(retry);if(stopped)return;if(ws?.readyState===0||ws?.readyState===1)return;
  ws=new WebSocket(`${location.protocol==='https:'?'wss':'ws'}://${location.host}/api/ws`);
  ws.onopen=()=>{status('Bağlı',true);resetLive();window.SofaNative?.connectionReady();refreshGlobalTabs()};
  ws.onmessage=event=>{const d=JSON.parse(event.data);if(d.type==='server-restarting'){restartUntil=Date.now()+300000;status('Bilgisayar güncelleniyor…');return}if(d.type==='keyboard-focus'){if(d.active)openPhoneKeyboard();return}if(d.type==='tabs'){applyTabs(d);return}const p=pending.get(d.id);if(p){clearTimeout(p.timer);pending.delete(d.id);d.type==='error'?p.reject(new Error(d.message)):p.resolve(d)}else if(d.type==='error')toast(d.message);if(d.type==='hello'&&d.version&&d.version!=='0.3.3'){location.reload();return}if(d.type==='hello'&&d.dryRun)status('Önizleme',true)};
  ws.onclose=()=>{for(const p of pending.values()){clearTimeout(p.timer);p.reject(new Error('Bağlantı kesildi'))}pending.clear();resetLive();status(stopped?'Bağlantı kesildi':'Tekrar bağlanıyor');if(!stopped)retry=setTimeout(load,2000)};
  ws.onerror=()=>status('Bilgisayar aranıyor');
}
let failures=0;
async function load(){if(stopped)return;try{await api('connect',{method:'POST'});shortcuts=await api('shortcuts');renderFavorites();connect();failures=0}catch{failures++;status('Bilgisayara ulaşılamıyor');if(failures>=30&&Date.now()>restartUntil)window.SofaNative?.discover();retry=setTimeout(load,2500)}}
function release(){send({type:'release'});resetLive()}
window.addEventListener('sofa-pause',release);document.addEventListener('visibilitychange',()=>{if(document.hidden)release();else if(!stopped&&ws?.readyState!==1)load()});
window.addEventListener('sofa-volume',e=>send({type:'keys',keys:[e.detail>0?'VOLUMEUP':'VOLUMEDOWN']}));
$('#connection').onclick=()=>{stopped=false;load()};
const keyCommands={'Geri':['ALT','LEFT'],'İleri':['ALT','RIGHT'],'Yenile':['CTRL','R'],'Adres çubuğu':['CTRL','L'],'Yeni sekme':['CTRL','T'],'Sekmeyi kapat':['CTRL','W'],'Sonraki sekme':['CTRL','TAB'],'Önceki sekme':['CTRL','SHIFT','TAB'],'Sekmeyi geri aç':['CTRL','SHIFT','T'],'Tam ekran (F11)':['F11'],'Pencere değiştir':['ALT','TAB'],'Masaüstü':['WIN','D'],'Başlat':['WIN'],'Ses artır':['VOLUMEUP'],'Ses azalt':['VOLUMEDOWN'],'Sessiz':['MUTE'],'Oynat/duraklat':['PLAYPAUSE'],'Durdur':['STOP'],'Önceki medya':['PREVIOUS'],'Sonraki medya':['NEXT'],'Sunum başlat':['F5'],'Sunum önceki':['PAGEUP'],'Sunum sonraki':['PAGEDOWN'],'Sunumu karart':['B']};
const special=['ESC','TAB','ENTER','BACKSPACE','SPACE','DELETE','HOME','END','PAGEUP','PAGEDOWN','INSERT','PRINTSCREEN','LEFT','UP','DOWN','RIGHT',...Array.from({length:12},(_,i)=>'F'+(i+1))];
const catalog=[...Object.entries(keyCommands).map(([name,keys])=>({name,action:{type:'keys',keys}})),...special.map(key=>({name:'Klavye · '+key,action:{type:'keys',keys:[key]}})),...['left','middle','right'].map(button=>({name:'Mouse · '+({left:'Sol',middle:'Orta',right:'Sağ'}[button])+' tık',action:{type:'click',button}})),...['youtube','netflix','generic'].flatMap(profile=>['play','back','forward','fullscreen','captions'].map(action=>({name:profile+' · '+({play:'Oynat/duraklat',back:'Geri sar',forward:'İleri sar',fullscreen:'Tam ekran',captions:'Altyazı'}[action]),action:{type:'profile',profile,action}}))),...Object.entries({chrome:'Chrome',edge:'Edge',firefox:'Firefox',explorer:'Dosya Gezgini',calculator:'Hesap Makinesi'}).map(([app,name])=>({name:'Uygulama · '+name,action:{type:'launch',app}})),...['lock','shutdown','restart','cancel'].map(action=>({name:'Güç · '+({lock:'Kilitle',shutdown:'Kapat',restart:'Yeniden başlat',cancel:'Kapatmayı iptal et'}[action]),action:{type:'power',action,confirm:true}}))];
function mouseMarkup(){return `<div class="touchpad" role="application" aria-label="Mouse yüzeyi"><span>⌖<br>Çift dokun + basılı tut: sürükle<br>İki parmak: kaydır / sağ tık</span></div><div class="grid three mouse-buttons">${['left','middle','right'].map((button,i)=>actionButton(['Sol tık','Orta','Sağ tık'][i],{type:'click',button})).join('')}</div><div class="row mouse-options"><label><input type="checkbox" data-drag> Sürükle</label><label>Hız <input type="range" data-speed min="0.5" max="4" step="0.1" value="${storage.get('speed',1.6)}"></label><label><input type="checkbox" data-lefty ${storage.get('lefty',false)?'checked':''}> Solak</label></div>`}
function mediaMarkup(){return `<div class="row"><select data-profile aria-label="Video sitesi"><option value="generic">Genel</option><option value="youtube">YouTube</option><option value="netflix">Netflix</option></select><small class="hint">Video odakta olmalı</small></div><div class="transport"><button data-video="back">⏪</button><button data-video="play" class="primary">▶ / Ⅱ</button><button data-video="forward">⏩</button></div><div class="grid three">${keyButton('Ses −',['VOLUMEDOWN'])}${keyButton('Sessiz',['MUTE'])}${keyButton('Ses +',['VOLUMEUP'])}<button data-video="fullscreen">⛶ Ekran</button><button data-video="captions">Altyazı</button>${keyButton('■ Durdur',['STOP'])}</div><div class="grid three">${keyButton('⏮',['PREVIOUS'])}${keyButton('Sistem ▶/Ⅱ',['PLAYPAUSE'])}${keyButton('⏭',['NEXT'])}</div>`}
function keyboardMarkup(){return `<textarea class="keyboard-live" aria-label="Anlık bilgisayar klavyesi" placeholder="Buraya yaz: PC’ye anında gider" autocomplete="off" autocapitalize="off" spellcheck="false"></textarea><div class="row"><small class="hint">Anlık giriş · Silme ve Enter destekli</small><button class="small" data-reset-live>Yeni alan</button></div><div class="grid four modifiers">${['CTRL','ALT','SHIFT','WIN'].map(k=>`<button data-mod="${k}">${k}</button>`).join('')}</div><div class="keygrid">${special.map(k=>`<button data-key="${k}">${k}</button>`).join('')}</div><div class="row"><input data-combo placeholder="CTRL+SHIFT+T" aria-label="Tuş birleşimi"><button data-send-combo>Gönder</button></div>`}
function browserMarkup(){return `<div class="row browser-title"><h3>Açık sekmeler</h3><button class="small" data-refresh-tabs>↻ Yenile</button></div><div data-tabs></div><details class="browser-navigation" open><summary>Tarayıcı kumandası</summary><div class="grid three">${Object.entries(keyCommands).slice(0,10).map(([name,keys])=>keyButton(name,keys)).join('')}</div></details>`}
function appsMarkup(){return `<div class="grid three">${Object.entries({chrome:'Chrome',edge:'Edge',firefox:'Firefox',explorer:'Dosyalar',calculator:'Hesap mak.'}).map(([app,name])=>actionButton(name,{type:'launch',app})).join('')}${keyButton('Alt + Tab',['ALT','TAB'])}</div><div class="row"><h3>Açık uygulamalar</h3><button class="small" data-refresh-apps>↻ Yenile</button></div><div data-windows></div>`}
function toolsMarkup(){return `<div class="grid"><button data-screen>Ekran önizlemesi</button>${keyButton('Masaüstü',['WIN','D'])}</div><img class="screen" alt="PC ekranı" hidden><h3>Metin panosu</h3><textarea data-clipboard aria-label="Metin panosu" placeholder="Paylaşılacak metin"></textarea><div class="grid"><button data-clip-get>PC’den getir</button><button data-clip-set>PC’ye kopyala</button></div><h3>Güç</h3><div class="grid">${catalog.filter(c=>c.action.type==='power').map(c=>actionButton(c.name.replace('Güç · ',''),c.action)).join('')}</div>`}
function catalogMarkup(){return '<div class="catalog"><input data-filter placeholder="Buton ara…" aria-label="Buton ara"><div data-command-list></div></div>'}
function renderPane(index){
 const root=$('#pane-'+index);let type=paneTypes[index];if(!labels[type])type='mouse';
 root.innerHTML=`<div class="pane-heading"><small>${index===0?'1':'2'}</small><select data-controller aria-label="${index+1}. kumanda seçimi">${Object.entries(labels).map(([key,label])=>`<option value="${key}" ${type===key?'selected':''}>${label}</option>`).join('')}</select></div><div class="pane-content ${type==='mouse'?'mouse-content':''}">${({mouse:mouseMarkup,media:mediaMarkup,keyboard:keyboardMarkup,browser:browserMarkup,apps:appsMarkup,commands:catalogMarkup,tools:toolsMarkup,downloads:downloadsMarkup}[type])()}</div>`;
 root.querySelector('[data-controller]').onchange=e=>{release();paneTypes[index]=e.target.value;storage.set('panes',paneTypes);renderPane(index)};
 setup(root,type);
}
function setup(root,type){
 const mods=new Set();
 root.onclick=async e=>{const b=e.target.closest('button');if(!b)return;
  try{
   if(b.dataset.action)await run(JSON.parse(b.dataset.action));
   else if(b.dataset.video)send({type:'profile',profile:root.querySelector('[data-profile]').value,action:b.dataset.video});
   else if(b.dataset.mod){const key=b.dataset.mod;mods.has(key)?mods.delete(key):mods.add(key);b.classList.toggle('selected',mods.has(key))}
   else if(b.dataset.key){send({type:'keys',keys:[...mods,b.dataset.key]});mods.clear();root.querySelectorAll('[data-mod]').forEach(x=>x.classList.remove('selected'))}
   else if(b.hasAttribute('data-send-combo'))send({type:'keys',keys:root.querySelector('[data-combo]').value.toUpperCase().split('+').map(k=>k.trim()).filter(Boolean)});
   else if(b.hasAttribute('data-reset-live')){const t=root.querySelector('.keyboard-live');t.value='';t.dataset.previous='';t.focus()}
   else if(b.hasAttribute('data-refresh-tabs'))await refreshTabs(root);
   else if(b.hasAttribute('data-refresh-apps'))await refreshApps(root);
   else if(b.hasAttribute('data-screen')){const d=await send({type:'screen'},true),img=root.querySelector('.screen');img.src='data:image/jpeg;base64,'+d.image;img.hidden=false}
   else if(b.hasAttribute('data-clip-get'))root.querySelector('[data-clipboard]').value=(await send({type:'clipboard_get'},true)).text;
   else if(b.hasAttribute('data-clip-set')){await send({type:'clipboard_set',text:root.querySelector('[data-clipboard]').value},true);toast('PC’ye kopyalandı')}
   else if(b.hasAttribute('data-check-updates'))await checkUpdates(root);
   else if(b.hasAttribute('data-install-update')){if(confirm('Windows kumandası yeniden başlatılarak güncellensin mi?'))await api('updates/install',{method:'POST'})}
   else if(b.hasAttribute('data-android-update'))window.SofaNative?.installUpdate();
  }catch(error){toast(error.message)}
 };
 if(type==='mouse')setupMouse(root);
 if(type==='keyboard')setupLive(root);
 if(type==='browser'){renderTabsList(root);refreshGlobalTabs()}
 if(type==='commands')setupCatalog(root);
 if(type==='downloads')refreshDownloads(root);
}
async function run(action){if(action.type==='click'){send({type:'button',button:action.button,down:true});send({type:'button',button:action.button,down:false});return}if(action.type==='power'&&!confirm('Bilgisayarın güç işlemi uygulansın mı?'))return;await send(action,true)}
function setupLive(root){const t=root.querySelector('.keyboard-live');t.dataset.previous='';
 const sync=()=>{const old=Array.from(t.dataset.previous||''),next=Array.from(t.value);let prefix=0;while(prefix<old.length&&prefix<next.length&&old[prefix]===next[prefix])prefix++;if(prefix===old.length&&prefix===next.length)return;if(ws?.readyState!==1){t.value='';t.dataset.previous='';toast('Bağlantı yok; yazı gönderilmedi');return}send({type:'edit',delete:old.length-prefix,text:next.slice(prefix).join('')});t.dataset.previous=t.value};
 t.addEventListener('input',e=>{if(!e.isComposing)sync()});t.addEventListener('compositionend',sync);
 t.addEventListener('beforeinput',e=>{if(e.inputType==='insertLineBreak'||e.inputType==='insertParagraph'){e.preventDefault();sync();send({type:'keys',keys:['ENTER']});t.value='';t.dataset.previous=''}else if(e.inputType==='deleteContentBackward'&&!t.value){e.preventDefault();send({type:'keys',keys:['BACKSPACE']})}});
}
function gestureOptions(extra={}){return {
 move:(x,y)=>send({type:'move',x,y}),scroll:amount=>send({type:'scroll',amount}),
 button:(button,down)=>send({type:'button',button,down}),click:button=>{send({type:'button',button,down:true});send({type:'button',button,down:false})},
 speed:()=>storage.get('speed',1.6),lefty:()=>storage.get('lefty',false),schedule:callback=>window.requestAnimationFrame(callback),cancelFrame:id=>window.cancelAnimationFrame(id),...extra
}}
function setupMouse(root){
 const pad=root.querySelector('.touchpad'),engine=new MouseGesture(gestureOptions({manual:()=>root.querySelector('[data-drag]').checked}));
 pad.addEventListener('sofa-reset',()=>engine.reset());
 pad.onpointerdown=e=>{e.preventDefault();pad.setPointerCapture(e.pointerId);engine.down(e)};
 pad.onpointermove=e=>engine.move(e);pad.onpointerup=e=>engine.up(e);pad.onpointercancel=()=>{engine.reset();send({type:'release'})};
 root.querySelector('[data-drag]').onchange=e=>send({type:'button',button:'left',down:e.target.checked});
 root.querySelector('[data-speed]').onchange=e=>storage.set('speed',Number(e.target.value));root.querySelector('[data-lefty]').onchange=e=>storage.set('lefty',e.target.checked);
}
function setupFullMouse(){
 let suppressUntil=0,replaying=false;const owners=new Map();
 globalMouse=new HoldMouse(gestureOptions({delay:(f,ms)=>setTimeout(f,ms),cancelDelay:id=>clearTimeout(id),activate:()=>{window.getSelection()?.removeAllRanges();suppressUntil=performance.now()+900;window.SofaNative?.vibrate?.()}}));
 const allowed=e=>fullMouse&&!$('#sheet').open&&!e.target.closest('.touchpad,#top-tabs,select,input[type=range],input[type=checkbox]');
 document.addEventListener('pointerdown',e=>{
  if(!allowed(e))return;
  if(e.cancelable)e.preventDefault();
  owners.set(e.pointerId,{scroll:e.target.closest('.favorites,.pane-content'),target:e.target.closest('button,a,summary,label,input,textarea,[contenteditable=true]')});
  globalMouse.down(e);
 },{capture:true,passive:false});
 document.addEventListener('pointermove',e=>{
  if(!owners.has(e.pointerId))return;const result=globalMouse.move(e);if(!result)return;
  if(e.cancelable)e.preventDefault();
  if(result.active)suppressUntil=performance.now()+900;
  else if(result.moved){const scroll=owners.get(e.pointerId).scroll;if(scroll){if(scroll.matches('.favorites'))scroll.scrollLeft-=result.dx;else scroll.scrollTop-=result.dy;}}
 },{capture:true,passive:false});
 document.addEventListener('pointerup',e=>{
  const owner=owners.get(e.pointerId);if(!owner)return;owners.delete(e.pointerId);
  const result=globalMouse.up(e);if(!result)return;
  if(e.cancelable)e.preventDefault();suppressUntil=performance.now()+900;
  if(!result.active&&!result.moved&&owner.target?.isConnected){
   replaying=true;
   if(owner.target.matches('input,textarea,[contenteditable=true]')){owner.target.focus({preventScroll:true});if(owner.target.matches('.keyboard-live'))window.SofaNative?.showKeyboard?.()}
   else owner.target.click();
   replaying=false;
  }
 },{capture:true,passive:false});
 document.addEventListener('pointercancel',e=>{if(owners.has(e.pointerId)){owners.clear();globalMouse.reset()}},true);
 for(const name of ['contextmenu','selectstart','dragstart'])document.addEventListener(name,e=>{if(allowed(e)){e.preventDefault();e.stopImmediatePropagation()}},true);
 document.addEventListener('click',e=>{if(!replaying&&allowed(e)&&performance.now()<suppressUntil){e.preventDefault();e.stopImmediatePropagation()}},true);
 document.body.classList.toggle('full-mouse',fullMouse);
}

function iconFor(item){
 const page=item.actions?.find(a=>a.type==='url')?.url;if(!page)return null;
 let match=tabsState.tabs.find(t=>t.url===page);if(!match){try{match=tabsState.tabs.find(t=>{try{return new URL(t.url).hostname===new URL(page).hostname}catch{return false}})}catch{}}
 return tabIcon(match)||pageIcon(page);
}
function pageIcon(url){try{if(['https:','http:'].includes(new URL(url).protocol))return '/api/icon?url='+encodeURIComponent(url)}catch{}return null}
function tabIcon(tab){if(!tab)return null;const icon=tab.favicon||'';if(icon.startsWith('data:image/'))return icon;return pageIcon(tab.url)}
function iconElement(item){const span=document.createElement('span'),url=item.tab?tabIcon(item.tab):iconFor(item);span.className='site-icon';span.textContent=item.icon||'🌐';
 if(url){const image=document.createElement('img');image.src=url;image.alt='';image.referrerPolicy='no-referrer';image.onerror=()=>image.replaceWith(document.createTextNode(item.icon||'🌐'));span.replaceChildren(image)}return span;
}
async function refreshGlobalTabs(){if(ws?.readyState!==1)return;try{applyTabs(await send({type:'tabs'},true))}catch{}}
function applyTabs(result){const fingerprint=JSON.stringify([result.connected,result.tabs]);tabsState={tabs:result.tabs||[],connected:!!result.connected};if(fingerprint===tabsFingerprint)return;tabsFingerprint=fingerprint;renderTopTabs();renderFavorites();for(const root of $$('.controller'))if(root.querySelector('[data-tabs]'))renderTabsList(root)}
function renderTopTabs(){const strip=$('#top-tabs');strip.replaceChildren();if(!tabsState.tabs.length){const empty=document.createElement('span');empty.className='empty-tabs';empty.textContent='▣';empty.title='Açık tarayıcı sekmesi yok';strip.append(empty);return}
 for(const tab of tabsState.tabs){const b=document.createElement('button');b.className=tab.active?'active':'';b.setAttribute('aria-label',tab.title||'Sekmeye geç');b.setAttribute('aria-pressed',String(tab.active));b.title=tab.title||tab.url;b.append(iconElement({tab,icon:'🌐'}));b.onclick=()=>{if(!b._held&&!b._skipClick)run({type:'tab',action:'activate',tabId:tab.id}).catch(e=>toast(e.message))};setupTabHold(b,tab);strip.append(b)}
}

async function closeTopTab(tabId){
 try{await run({type:'tab',action:'close',tabId});if($('#sheet').open)$('#sheet').close();await refreshGlobalTabs();toast('Sekme kapatıldı')}
 catch(e){toast('Sekme kapatılamadı: '+e.message)}
}
window.addEventListener('sofa-tab-close',e=>closeTopTab(Number(e.detail)));
function setupTabHold(button,tab){
 let timer,start;
 const cancel=()=>{clearTimeout(timer);timer=null};
 button.addEventListener('pointerdown',e=>{
  button._held=false;start={x:e.clientX,y:e.clientY};
  if(e.pointerType==='touch'&&e.cancelable)e.preventDefault();
  timer=setTimeout(()=>{
   button._held=true;window.getSelection()?.removeAllRanges();
   if(window.SofaNative?.tabMenu){release();window.SofaNative.tabMenu(tab.id,tab.title||tab.url||'Sekme');return}
   sheet('Sekme',`<p>${escaped(tab.title||tab.url||'Sekme')}</p><button id="close-top-tab" class="wide">Sekmeyi kapat</button>`);$('#close-top-tab').onclick=()=>closeTopTab(tab.id);
  },450);
 });
 button.addEventListener('pointermove',e=>{if(start&&Math.hypot(e.clientX-start.x,e.clientY-start.y)>10)cancel()});
 button.addEventListener('pointerup',e=>{cancel();if(e.pointerType==='touch'){e.preventDefault();if(!button._held)run({type:'tab',action:'activate',tabId:tab.id}).catch(e=>toast(e.message));button._skipClick=true;setTimeout(()=>button._skipClick=false,700)}});
 for(const name of ['pointercancel','pointerleave'])button.addEventListener(name,cancel);
 button.addEventListener('contextmenu',e=>e.preventDefault());
}

function renderFavorites(){$('#favorites').replaceChildren();shortcuts.forEach((item,index)=>{const b=document.createElement('button');b.title=item.name;b.setAttribute('aria-label',item.name);b.append(iconElement(item));b.onclick=async()=>{try{await send({type:'macro',index},true)}catch(e){toast(e.message)}};$('#favorites').append(b)})}
async function save(items){shortcuts=await api('shortcuts',{method:'PUT',headers:{'Content-Type':'application/json'},body:JSON.stringify(items)});renderFavorites();toast('Kaydedildi')}
function setupCatalog(root){const filter=root.querySelector('[data-filter]'),list=root.querySelector('[data-command-list]');const render=()=>{list.replaceChildren();for(const c of catalog.filter(c=>c.name.toLocaleLowerCase('tr').includes(filter.value.toLocaleLowerCase('tr')))){const row=document.createElement('div');row.className='list-item';const name=document.createElement('span');name.textContent=c.name;const play=document.createElement('button');play.className='small';play.textContent='Çalıştır';play.onclick=()=>run(c.action).catch(e=>toast(e.message));row.append(name,play);if(['keys','profile','launch'].includes(c.action.type)){const add=document.createElement('button');add.className='small';add.textContent='＋';add.title='Kısayola ekle';add.onclick=()=>save([...shortcuts,{name:c.name,icon:'⚡',actions:[c.action]}]).catch(e=>toast(e.message));row.append(add)}list.append(row)}};filter.oninput=render;render()}
async function refreshTabs(root){await refreshGlobalTabs();renderTabsList(root)}
function renderTabsList(root){
 const list=root.querySelector('[data-tabs]');if(!list)return;list.replaceChildren();
 if(!tabsState.connected){const p=document.createElement('p');p.className='hint';p.textContent='Sekme bağlantısı bekleniyor. Bilgisayardaki Sofa Remote Tabs eklentisi açık olmalı.';list.append(p);return}
 if(!tabsState.tabs.length){const p=document.createElement('p');p.className='hint';p.textContent='Açık sekme yok';list.append(p)}
 for(const tab of tabsState.tabs){const card=document.createElement('article');card.className='tab-card';const heading=document.createElement('div');heading.className='tab-card-heading';
 heading.append(iconElement({tab,icon:'🌐'}));const title=document.createElement('button');title.className='tab-select';title.textContent=(tab.active?'● ':'')+(tab.title||tab.url||'Sekme');title.title=tab.title||tab.url;
 title.onclick=()=>run({type:'tab',action:'activate',tabId:tab.id}).catch(e=>toast(e.message));
 const close=document.createElement('button');close.className='small';close.textContent='✕';close.setAttribute('aria-label','Sekmeyi kapat');close.onclick=async()=>{try{await run({type:'tab',action:'close',tabId:tab.id});await refreshGlobalTabs()}catch(e){toast(e.message)}};
 heading.append(title,close);const actions=document.createElement('div');actions.className='tab-card-actions';for(const [action,label] of [['reload','↻ Yenile'],['duplicate','⧉ Kopyala']]){const b=document.createElement('button');b.className='small';b.textContent=label;b.onclick=async()=>{try{await run({type:'tab',action,tabId:tab.id});await refreshGlobalTabs()}catch(e){toast(e.message)}};actions.append(b)}card.append(heading,actions);list.append(card)}
}
async function refreshApps(root){const {windows}=await send({type:'windows'},true),list=root.querySelector('[data-windows]');list.replaceChildren();for(const w of windows){const row=document.createElement('div');row.className='list-item';const title=document.createElement('button');title.textContent=w.title;title.className='title';title.onclick=()=>run({type:'focus',id:w.id}).catch(e=>toast(e.message));row.append(title);const actions=document.createElement('div');actions.className='grid four';for(const [action,name] of [['minimize','Küçült'],['maximize','Büyüt'],['restore','Geri al'],['close','Kapat']]){const b=document.createElement('button');b.className='small';b.textContent=name;b.onclick=async()=>{if(action==='close'&&!confirm(w.title+' kapatılsın mı?'))return;try{await run({type:'window',handle:w.id,action});await refreshApps(root)}catch(e){toast(e.message)}};actions.append(b)}row.append(actions);list.append(row)}}
function sheet(title,html){release();$('#sheet-title').textContent=title;$('#sheet-body').innerHTML=html;$('#sheet').showModal()}
$('#close-sheet').onclick=()=>$('#sheet').close();$('#sheet').addEventListener('click',e=>{if(e.target===$('#sheet'))$('#sheet').close()});
$('#layout').onclick=()=>{sheet('Ekran ve mouse','<label class="setting-switch"><input type="checkbox" id="full-mouse-setting" '+(fullMouse?'checked':'')+'> Bütün ekranı mouse olarak kullan</label><p class="hint">Yarım saniye basılı tut, ardından kaydır: mouse hareket eder. Parmağını kaldırınca sol tık yapılır. Tek dokunuş uygulamayı normal kullanır. Normal mouse yüzeyi her zaman çalışır.</p><p class="hint">Normal mouse: çift dokun, ikinci dokunuşu basılı tutup kaydırarak sürükle.</p><div class="grid"><button id="stack">▤ Üst üste</button><button id="side">▥ Yan yana</button></div>');$('#full-mouse-setting').onchange=e=>{release();fullMouse=e.target.checked;storage.set('fullMouse',fullMouse);document.body.classList.toggle('full-mouse',fullMouse);toast(fullMouse?'Tam ekran mouse açık':'Normal mouse açık')};$('#stack').onclick=()=>setLayout(false);$('#side').onclick=()=>setLayout(true)};
function setLayout(side){$('#workspace').classList.toggle('side',side);storage.set('side',side);$('#sheet').close()}
$('#shortcuts').onclick=()=>{sheet('Kısayollar ve makrolar','<input id="shortcut-name" placeholder="Kısayol adı" aria-label="Kısayol adı"><input id="shortcut-url" placeholder="https://…" type="url" aria-label="Site adresi"><input id="shortcut-icon" placeholder="Makro sembolü (ör. 🎬)" maxlength="12"><button id="add-shortcut" class="primary wide">Site ekle</button><div id="shortcut-list"></div><details><summary>Makroları düzenle / yedekle</summary><textarea id="macro-json" aria-label="Makrolar"></textarea><button id="save-macros" class="wide">Kaydet</button></details>');$('#macro-json').value=JSON.stringify(shortcuts,null,2);const list=$('#shortcut-list');shortcuts.forEach((item,index)=>{const row=document.createElement('div');row.className='row list-item';const name=document.createElement('span');name.className='title';name.textContent=item.name;const del=document.createElement('button');del.textContent='Sil';del.onclick=async()=>{try{await save(shortcuts.filter((_,i)=>i!==index));$('#sheet').close()}catch(e){toast(e.message)}};row.append(iconElement(item),name,del);list.append(row)});$('#add-shortcut').onclick=async()=>{try{await save([...shortcuts,{name:$('#shortcut-name').value.trim(),icon:$('#shortcut-icon').value||'🌐',actions:[{type:'url',url:$('#shortcut-url').value.trim()}]}]);$('#sheet').close()}catch(e){toast(e.message)}};$('#save-macros').onclick=async()=>{try{await save(JSON.parse($('#macro-json').value));$('#sheet').close()}catch(e){toast(e.message)}}};
function downloadsMarkup(){return `<div class="update-info" aria-live="polite"><p data-update-status>PC sürümü okunuyor…</p><p data-android-status></p></div><button class="primary wide" data-check-updates>Güncellemeleri kontrol et</button>`}
function nativeUpdateInfo(){try{const raw=window.SofaNative?.updateInfo?.();if(raw)return JSON.parse(raw)}catch{}return storage.get('androidUpdate',null)}
async function refreshDownloads(root){try{const d=await api('updates'),status=root.querySelector('[data-update-status]');if(!status)return;const state={idle:'Hazır',checking:'Kontrol ediliyor',current:'Güncel',available:'Yeni sürüm var',downloading:'İndiriliyor',ready:'Güncelleme hazır',error:'Kontrol yapılamadı'}[d.state]||d.state;status.textContent=`Windows v${d.current} · Son sürüm v${d.latest} · ${state}`;
 const native=nativeUpdateInfo(),android=root.querySelector('[data-android-status]');if(android)android.textContent=native?`Android${native.current?' v'+native.current:''}${native.latest?' · Son sürüm v'+native.latest:''} · ${native.message||''}`:window.SofaNative?'Android sürümü kontrol ediliyor…':'';
 if(checkingUpdates&&d.ready&&pcPrompted!==d.latest){pcPrompted=d.latest;if(confirm('Windows v'+d.latest+' indirildi. PC kumandası yeniden başlatılarak güncellensin mi?')){restartUntil=Date.now()+300000;await api('updates/install',{method:'POST'})}}
 }catch(e){const status=root.querySelector('[data-update-status]');if(status)status.textContent=e.message}}
async function checkUpdates(root){if(window.SofaNative&&!window.SofaNative.updateInfo&&/kurulmaya hazır/i.test(storage.get('androidUpdate',{}).message||'')){window.SofaNative.installUpdate();return}checkingUpdates=true;toast('Güncellemeler kontrol ediliyor…');const b=root.querySelector('[data-check-updates]');if(b)b.disabled=true;
 try{window.SofaNative?.checkUpdates();await api('updates/check',{method:'POST'});await refreshDownloads(root)}finally{if(b)b.disabled=false}}
$('#downloads').onclick=()=>{sheet('Güncelleme',downloadsMarkup());setup($('#sheet-body'),'downloads')};
let legacyInstallOffered='';
window.addEventListener('sofa-update',e=>{storage.set('androidUpdate',e.detail);if(checkingUpdates&&window.SofaNative&&!window.SofaNative.updateInfo&&/kurulmaya hazır/i.test(e.detail.message||'')&&legacyInstallOffered!==e.detail.message){legacyInstallOffered=e.detail.message;window.SofaNative.installUpdate()}if(checkingUpdates)toast(e.detail.message);for(const root of $$('.controller, #sheet-body'))if(root.querySelector('[data-update-status]'))refreshDownloads(root)});
$('#devices').onclick=()=>{if(window.SofaNative){window.SofaNative.discover();return}sheet('Bilgisayar bağlantısı','<p>Şu an: '+escaped(location.host)+'</p><p class="hint">Otomatik yerel ağ taraması Android uygulamasındadır. Tarayıcıda bilgisayarın yerel adresini açabilirsin.</p><button id="reconnect" class="wide">Yeniden bağlan</button><button id="disconnect" class="wide">Bağlantıyı kes</button>');$('#reconnect').onclick=()=>{stopped=false;load();$('#sheet').close()};$('#disconnect').onclick=()=>{stopped=true;clearTimeout(retry);release();ws?.close();$('#sheet').close()}};
$('#workspace').classList.toggle('side',storage.get('side',false));[0,1].forEach(renderPane);setupFullMouse();renderTopTabs();load();
window.visualViewport?.addEventListener('resize',()=>document.documentElement.style.setProperty('--screen-height',window.visualViewport.height+'px'));
setInterval(()=>{for(const root of $$('.controller, #sheet-body'))if(root.querySelector('[data-update-status]'))refreshDownloads(root)},1500);
setInterval(()=>{if(!document.hidden)refreshGlobalTabs()},4000);

function openPhoneKeyboard(){
 if(document.hidden||$('#sheet').open)return;
 resetTextInputs();
 if(window.SofaNative?.showKeyboard){window.SofaNative.showKeyboard();return}
 let field=document.querySelector('.keyboard-live');
 if(!field){paneTypes[1]='keyboard';storage.set('panes',paneTypes);renderPane(1);field=document.querySelector('#pane-1 .keyboard-live')}
 field.focus({preventScroll:true});
 if(!window.SofaNative)toast('Yazmak için klavye alanına dokun');
}

window.addEventListener('sofa-native-edit',e=>{send({type:'edit',delete:e.detail.delete,text:e.detail.text})});
window.addEventListener('sofa-native-key',e=>send({type:'keys',keys:[e.detail]}));
