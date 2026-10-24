'use strict';
const $=s=>document.querySelector(s), $$=s=>[...document.querySelectorAll(s)];
let ws, reconnectTimer, stopped=false, sequence=0, shortcuts=[], modifiers=new Set(), pending=new Map();
let toastTimer;
function toast(message){$('#toast').textContent=message;$('#toast').classList.add('show');clearTimeout(toastTimer);toastTimer=setTimeout(()=>$('#toast').classList.remove('show'),4000)}
function status(text,online=false){$('#connection').textContent='● '+text;$('#connection').classList.toggle('online',online)}
async function api(path,options={}){const response=await fetch('/api/'+path,options);if(!response.ok){const error=new Error(await response.text());error.status=response.status;throw error}return response.json()}
function send(data,wait=false){
  if(!ws||ws.readyState!==WebSocket.OPEN){if(data.type!=='move')toast('Bağlantı yok');return wait?Promise.reject(new Error('Bağlantı yok')):undefined}
  const id=++sequence;ws.send(JSON.stringify({...data,id}));
  if(!wait)return;
  return new Promise((resolve,reject)=>{const timer=setTimeout(()=>{pending.delete(id);reject(new Error('Komut zaman aşımı'))},8000);pending.set(id,{resolve,reject,timer})});
}
function rejectPending(){for(const p of pending.values()){clearTimeout(p.timer);p.reject(new Error('Bağlantı kesildi'))}pending.clear()}
function connect(){
  clearTimeout(reconnectTimer);if(stopped)return;
  status('Bağlanıyor');ws=new WebSocket(`${location.protocol==='https:'?'wss':'ws'}://${location.host}/api/ws`);
  ws.onopen=()=>status('Ev ağına bağlı',true);
  ws.onmessage=event=>{const data=JSON.parse(event.data);const p=pending.get(data.id);if(p){clearTimeout(p.timer);pending.delete(data.id);data.type==='error'?p.reject(new Error(data.message)):p.resolve(data)}else if(data.type==='error')toast(data.message);if(data.type==='hello'&&data.dryRun)toast('Demo modu: bilgisayara gerçek komut gönderilmiyor')};
  ws.onclose=()=>{rejectPending();resetTouch();status(stopped?'Bağlantı kapalı':'Yeniden bağlanıyor');if(!stopped)reconnectTimer=setTimeout(async()=>{try{await api('shortcuts');connect()}catch(error){if(error.status===401)showPair();else reconnectTimer=setTimeout(connect,3000)}},2000)};
  ws.onerror=()=>status('Bağlantı kurulamadı');
}
function showPair(){stopped=true;clearTimeout(reconnectTimer);if(ws)ws.close();$('#pair').hidden=false;$('#controls').hidden=true;status('Eşleştirme gerekli')}
async function load(){try{shortcuts=await api('shortcuts');$('#pair').hidden=true;$('#controls').hidden=false;renderShortcuts();stopped=false;connect()}catch(error){if(error.status===401)showPair();else{status('Sunucuya erişilemiyor');toast(error.message)}}}
$('#pair-form').onsubmit=async event=>{event.preventDefault();try{await api('pair',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({pin:$('#pin').value})});$('#pin').value='';await load()}catch(error){toast(error.message)}};
$('#disconnect').onclick=()=>{stopped=true;clearTimeout(reconnectTimer);ws?.close();status('Bağlantı kapalı')};
$('#connection').onclick=()=>{if(!ws||ws.readyState!==1){stopped=false;load()}};
$$('[data-tab]').forEach(button=>button.onclick=()=>{$$('[data-tab]').forEach(b=>b.classList.toggle('active',b===button));$$('.panel').forEach(p=>p.classList.toggle('active',p.id===button.dataset.tab))});
function keys(list){send({type:'keys',keys:list})}
$$('[data-key]').forEach(b=>b.onclick=()=>keys([b.dataset.key]));
$$('[data-combo]').forEach(b=>b.onclick=()=>keys(b.dataset.combo.split('+')));
$$('[data-action]').forEach(b=>b.onclick=()=>send(JSON.parse(b.dataset.action)));
$$('[data-profile]').forEach(b=>b.onclick=()=>send({type:'profile',profile:$('#profile').value,action:b.dataset.profile}));
function click(button){send({type:'button',button,down:true});send({type:'button',button,down:false})}
$$('[data-click]').forEach(b=>b.onclick=()=>click(b.dataset.click));
const special=['ESC','TAB','ENTER','BACKSPACE','SPACE','DELETE','HOME','END','PAGEUP','PAGEDOWN','INSERT','PRINTSCREEN','LEFT','UP','DOWN','RIGHT',...Array.from({length:12},(_,i)=>'F'+(i+1)),...Array.from('ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789')];
for(const key of special){const b=document.createElement('button');b.textContent=key;b.onclick=()=>{keys([...modifiers,key]);modifiers.clear();$$('[data-mod]').forEach(x=>x.classList.remove('selected'))};$('#keys').append(b)}
$$('[data-mod]').forEach(b=>b.onclick=()=>{const k=b.dataset.mod;modifiers.has(k)?modifiers.delete(k):modifiers.add(k);b.classList.toggle('selected',modifiers.has(k))});
$('#send-combo').onclick=()=>keys($('#combo').value.toUpperCase().split('+').map(x=>x.trim()).filter(Boolean));
$('#send-text').onclick=()=>{if($('#text').value)send({type:'text',text:$('#text').value})};
$('#search').onclick=async()=>{const query=$('#text').value.trim();if(!query)return;try{await send({type:'url',url:'https://www.google.com/search?q='+encodeURIComponent(query)},true)}catch(e){toast(e.message)}};
const browserActions={'← Geri':['ALT','LEFT'],'İleri →':['ALT','RIGHT'],'Yenile':['CTRL','R'],'Adres çubuğu':['CTRL','L'],'Yeni sekme':['CTRL','T'],'Sekmeyi kapat':['CTRL','W'],'Sonraki sekme':['CTRL','TAB'],'Sekmeyi geri aç':['CTRL','SHIFT','T'],'Tarayıcı tam ekran':['F11'],'Pencere değiştir':['ALT','TAB'],'Masaüstü':['WIN','D'],'Başlat':['WIN']};
for(const [name,combo] of Object.entries(browserActions)){const b=document.createElement('button');b.textContent=name;b.onclick=()=>keys(combo);$('#browser').append(b)}
const pointers=new Map();let gesture=null,frame=null,mx=0,my=0,scrollY=0;
function resetTouch(){pointers.clear();gesture=null;mx=my=scrollY=0;$('#drag').checked=false}
function flushMove(){frame=null;if(mx||my){send({type:'move',x:Math.max(-1000,Math.min(1000,Math.round(mx))),y:Math.max(-1000,Math.min(1000,Math.round(my)))});mx=my=0}}
const pad=$('#touchpad');
pad.onpointerdown=e=>{e.preventDefault();pad.setPointerCapture(e.pointerId);pointers.set(e.pointerId,{x:e.clientX,y:e.clientY});if(!gesture)gesture={start:performance.now(),distance:0,fingers:1};gesture.fingers=Math.max(gesture.fingers,pointers.size)};
pad.onpointermove=e=>{const old=pointers.get(e.pointerId);if(!old||!gesture)return;const dx=e.clientX-old.x,dy=e.clientY-old.y;pointers.set(e.pointerId,{x:e.clientX,y:e.clientY});gesture.distance+=Math.abs(dx)+Math.abs(dy);if(pointers.size>=2){scrollY+=dy;if(Math.abs(scrollY)>18){const amount=Math.trunc(scrollY/18);send({type:'scroll',amount:Math.max(-20,Math.min(20,amount))});scrollY-=amount*18}}else{const speed=Number($('#speed').value);mx+=dx*speed;my+=dy*speed;if(!frame)frame=requestAnimationFrame(flushMove)}};
pad.onpointerup=e=>{pointers.delete(e.pointerId);if(!pointers.size&&gesture){if(gesture.distance<12&&performance.now()-gesture.start<350&&!$('#drag').checked)click(gesture.fingers>=2?'right':$('#lefty').checked?'right':'left');gesture=null;scrollY=0}};
pad.onpointercancel=()=>{send({type:'release'});resetTouch()};
$('#drag').onchange=()=>send({type:'button',button:'left',down:$('#drag').checked});
document.addEventListener('visibilitychange',()=>{if(document.hidden){send({type:'release'});resetTouch()}});
for(const id of ['speed','lefty','profile']){const el=$('#'+id),saved=localStorage.getItem(id);if(saved!==null){if(el.type==='checkbox')el.checked=saved==='true';else el.value=saved}el.addEventListener('change',()=>localStorage.setItem(id,el.type==='checkbox'?el.checked:el.value))}
function renderShortcuts(){
  $('#favorites').replaceChildren();$('#shortcut-list').replaceChildren();$('#macro-json').value=JSON.stringify(shortcuts,null,2);
  shortcuts.forEach((item,index)=>{const b=document.createElement('button');b.textContent=item.name;b.onclick=async()=>{b.disabled=true;try{await send({type:'macro',index},true)}catch(e){toast(e.message)}finally{b.disabled=false}};$('#favorites').append(b);
    const row=document.createElement('div');row.className='row';const label=document.createElement('span');label.textContent=item.name;const del=document.createElement('button');del.textContent='Sil';del.onclick=async()=>{if(!confirm(item.name+' silinsin mi?'))return;try{await save(shortcuts.filter((_,i)=>i!==index))}catch(e){toast(e.message)}};row.append(label,del);$('#shortcut-list').append(row)});
}
async function save(items){shortcuts=await api('shortcuts',{method:'PUT',headers:{'Content-Type':'application/json'},body:JSON.stringify(items)});renderShortcuts();toast('Kısayollar kaydedildi')}
$('#add-url').onclick=async()=>{try{const name=$('#shortcut-name').value.trim(),url=$('#shortcut-url').value.trim();if(!name)throw new Error('Düğmeye bir ad ver');await save([...shortcuts,{name,actions:[{type:'url',url}]}]);$('#shortcut-name').value=$('#shortcut-url').value=''}catch(e){toast(e.message)}};
$('#save-macros').onclick=async()=>{try{await save(JSON.parse($('#macro-json').value))}catch(e){toast(e.message)}};
$('#export').onclick=()=>{if(navigator.userAgent.includes('; wv)')){$('#macro-json').focus();$('#macro-json').select();toast('Yedek için seçili JSON metnini kopyala');return}const url=URL.createObjectURL(new Blob([JSON.stringify(shortcuts,null,2)],{type:'application/json'}));const a=document.createElement('a');a.href=url;a.download='sofa-shortcuts.json';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000)};
$('#screenshot').onclick=async()=>{try{const r=await send({type:'screen'},true);$('#screen').src='data:image/jpeg;base64,'+r.image;$('#screen').hidden=false}catch(e){toast(e.message)}};
$('#windows').onclick=async()=>{try{const r=await send({type:'windows'},true);$('#window-list').replaceChildren();for(const w of r.windows){const b=document.createElement('button');b.textContent=w.title;b.onclick=()=>send({type:'focus',id:w.id});$('#window-list').append(b)}if(!r.windows.length)toast('Açık pencere bulunamadı')}catch(e){toast(e.message)}};
$('#clip-get').onclick=async()=>{try{$('#clipboard').value=(await send({type:'clipboard_get'},true)).text}catch(e){toast(e.message)}};
$('#clip-set').onclick=async()=>{try{await send({type:'clipboard_set',text:$('#clipboard').value},true);toast('PC panosuna kopyalandı')}catch(e){toast(e.message)}};
$$('[data-power]').forEach(b=>b.onclick=()=>{if(confirm('Bilgisayar: '+b.textContent+'?'))send({type:'power',action:b.dataset.power,confirm:true})});
load();
window.addEventListener('sofa-pause',()=>{send({type:'release'});resetTouch()});
