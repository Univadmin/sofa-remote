'use strict';
function movieMarkup(){return `<div class="film-toolbar"><input data-film-query placeholder="Film adı ara…" aria-label="Film adı"><button data-film-search>Ara</button></div><div class="row"><select data-film-filter aria-label="Film listesi"><option value="all">Film kataloğu</option><option value="watched">İzlenenler</option><option value="watching">İzleniyor</option></select><button data-film-refresh class="small">Yenile</button></div><p class="hint" data-film-status>Filmler yükleniyor…</p><div data-film-list></div><button class="wide" data-film-more hidden>Daha fazla film</button><p class="hint">Katalog: <a href="https://www.justwatch.com/tr" target="_blank" rel="noopener noreferrer">JustWatch</a> · IMDb. Kaynaklar PC tarayıcısındaki gerçek oynatım denenerek filtrelenir.</p>`}
function setupMovies(root){
 let cursor=null,busy=false,queued=false,request=0,selected=null,poll=null;const list=root.querySelector('[data-film-list]'),status=root.querySelector('[data-film-status]'),more=root.querySelector('[data-film-more]');
 const call=(path='',options={})=>api('movies'+path,options,45000);
 const post=data=>call('',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(data)});
 const stateName=s=>({watched:'✓ İzlendi',watching:'▶ İzleniyor'}[s]||'İzlenmedi');
 const current=()=>root.isConnected&&root.querySelector('[data-film-list]')===list&&!(root.id==='sheet-body'&&$('#sheet').hidden);
 function card(movie){const row=document.createElement('article');row.className='film-card';row.innerHTML=`<button class="film-title" data-film-detail="${escaped(movie.id)}">${escaped(movie.title)}</button><p>${escaped(movie.year||'Yıl yok')} · IMDb ${movie.imdb==null?'—':Number(movie.imdb).toFixed(1)} <small>· ${stateName(movie.status)}</small></p>`;list.append(row)}
 async function load(append=false){
  if(busy){if(!append)queued=true;return;}busy=true;selected=null;clearTimeout(poll);const id=++request;more.disabled=true;status.textContent='Filmler yükleniyor…';
  try{const filter=root.querySelector('[data-film-filter]').value,q=root.querySelector('[data-film-query]').value.trim();let d;
   if(filter==='all')d=await call('?q='+encodeURIComponent(q)+(append&&cursor?'&cursor='+encodeURIComponent(cursor):''));
   else{d=await call('?mode=history');d.movies=d.movies.filter(m=>m.status===filter&&(!q||(m.title+' '+m.original_title).toLocaleLowerCase('tr').includes(q.toLocaleLowerCase('tr'))));}
   if(id!==request||!current())return;if(!append)list.replaceChildren();d.movies.forEach(card);cursor=d.cursor;more.hidden=!d.has_more;status.textContent=d.offline?'Çevrimdışı: önbellekteki filmler gösteriliyor.':list.children.length?'Film seçerek izlenebilen kaynakları kontrol et.':'Film bulunamadı.';
  }catch(e){status.textContent=e.message}finally{busy=false;more.disabled=false;if(queued){queued=false;load()}}
 }
 async function detail(ident,force=false){
  selected=ident;clearTimeout(poll);status.textContent='PC tarayıcısında oynatım ve Türkçe altyazı kontrol ediliyor…';
  try{const d=await call('?mode=sources&id='+encodeURIComponent(ident)+(force?'&refresh=1':''));if(!current()||selected!==ident)return;const m=d.movie;list.replaceChildren();more.hidden=true;
   const box=document.createElement('article');box.className='film-card';box.innerHTML=`<h3>${escaped(m.title)}</h3><p>${escaped(m.year||'—')} · IMDb ${m.imdb==null?'—':Number(m.imdb).toFixed(1)}</p><p class="hint">Yalnızca mevcut PC tarayıcı oturumunda film videosu oynatıldığı doğrulanan kaynaklar. Yabancı filmlerde Türkçe altyazı aranır. Türkçe filmler için aşağıdaki seçimi açın.</p>`;
   const language=document.createElement('label');const toggle=document.createElement('input');toggle.type='checkbox';toggle.checked=!!m.turkish_original;language.append(toggle,document.createTextNode(' Filmin özgün dili Türkçe (altyazı gerekmez)'));toggle.onchange=async()=>{try{await post({action:'language',id:ident,turkish_original:toggle.checked});await detail(ident,true)}catch(e){toast(e.message)}};box.append(language);
   d.offers.forEach(offer=>{const b=document.createElement('button');b.className='primary wide';b.dataset.filmPlay=offer.source_id;b.textContent='▶ İzle · '+offer.provider+' · '+offer.cost+(offer.turkish_subtitles?' · Türkçe altyazı':' · Türkçe film/ses');b.onclick=()=>play(ident,offer.source_id,b);box.append(b)});
   const message=document.createElement('p');message.className='hint';message.textContent=(d.message||'')+(d.state!=='checking'&&d.failures?.length?' Son kontrol: '+d.failures.join(' • '):'');box.append(message);
   const check=document.createElement('button');check.className='wide';check.textContent=d.state==='checking'?'Kaynaklar kontrol ediliyor…':'Kaynakları yeniden kontrol et';check.disabled=d.state==='checking';check.onclick=()=>detail(ident,true);box.append(check);
   const row=document.createElement('div');row.className='grid';for(const [value,label] of [['watched','✓ İzlendi olarak işaretle'],['unwatched','İzlendi kaydını kaldır']]){const b=document.createElement('button');b.textContent=label;b.onclick=async()=>{try{await post({action:'mark',id:ident,status:value});toast('İzleme listesi güncellendi')}catch(e){toast(e.message)}};row.append(b)}box.append(row);
   const hint=document.createElement('p');hint.className='hint';hint.textContent='İzle: filmi başlatır ve tam ekrana geçirir. Escape ile tam ekrandan çıkılır. Film bilgi sayfaları, fragmanlar ve oynatılamayan kaynaklar sonuçlara eklenmez. Otomatik İzlendi kaydı için oynatımın %90’ı algılanmalı.';box.append(hint);list.append(box);status.textContent=d.state==='checking'?'İzlenebilir kaynaklar deneniyor…':d.offers.length+' izlenebilir kaynak';
   if(d.state==='checking')poll=setTimeout(()=>{if(current()&&selected===ident)detail(ident)},2000);
  }catch(e){status.textContent=e.message}
 }
 async function play(ident,source_id,button){button.disabled=true;button.textContent='Oynatılıyor…';try{await post({action:'play',id:ident,source_id});toast('Film başlatıldı ve tam ekran açıldı.')}catch(e){toast(e.message);await detail(ident)}finally{button.disabled=false}}
 root.onclick=e=>{const b=e.target.closest('button');if(!b)return;if(b.dataset.filmDetail)detail(b.dataset.filmDetail);else if(b.hasAttribute('data-film-search')||b.hasAttribute('data-film-refresh'))load();else if(b.hasAttribute('data-film-more'))load(true)};
 root.querySelector('[data-film-query]').onkeydown=e=>{if(e.key==='Enter'){e.preventDefault();load()}};root.querySelector('[data-film-filter]').onchange=()=>load();load();
}
