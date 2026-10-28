/* Coordinates isolated checks in the user's authenticated browser, never purchases. */
'use strict';
const movieJobs=new Map(),movieWindows=new Map();let movieActivation=Promise.resolve();
function movieName(s){return String(s||'').toLocaleLowerCase('tr').replace(/ı/g,'i').normalize('NFKD').replace(/[^\p{L}\p{N}]/gu,'')}
async function movieKick(job){
 try{const tab=await chrome.tabs.get(job.tabId);const title=movieName(tab.title);
  const titleConfirmed=[job.movie.title,job.movie.english_title,job.movie.original_title].some(n=>{n=movieName(n);return n&&(n.length>=4?title.includes(n):title===n)});
  await chrome.tabs.sendMessage(job.tabId,{type:'movie-control',requestId:job.requestId,mode:job.mode,movie:job.movie,turkish_subtitles:job.turkish_subtitles,passive:job.passive===true,titleConfirmed});
 }catch{}
}
async function movieFinish(job,result){
 if(!movieJobs.has(job.requestId))return;
 movieJobs.delete(job.requestId);clearTimeout(job.timer);clearInterval(job.retry);
 const active=await chrome.tabs.get(job.tabId).catch(()=>null);
 if(job.mode==='probe'||!result.ok){await chrome.tabs.remove(job.tabId).catch(()=>{});if(job.mode==='play'&&job.previousState)await chrome.windows.update(job.windowId,{state:job.previousState}).catch(()=>{});}
 else{await chrome.tabs.update(job.tabId,{muted:false});movieWindows.set(job.tabId,{windowId:job.windowId,state:job.previousState});filmTabs.add(job.tabId);chrome.tabs.sendMessage(job.tabId,{type:'movie-track'}).catch(()=>{})}
 if(job.mode==='probe'&&active?.active&&job.previousTab){await chrome.tabs.update(job.previousTab.id,{active:true}).catch(()=>{});}
 job.releaseActivation?.();
 if(socket?.readyState===1)socket.send(JSON.stringify({requestId:job.requestId,...result}));
}
async function movieCommand(d){
 if(d.type==='movie-cancel'){
  const batch=movieSearchBatches.get(d.requestId);if(batch){batch.cancelled=true;for(const id of batch.tabs)movieSearches.get(id)?.resolve({error:'Arama iptal edildi'});}
  const job=movieJobs.get(d.requestId);if(job)await movieFinish(job,{error:'Kontrol iptal edildi'});return;
 }
 if(!['movie-probe','movie-play'].includes(d.type))return;
 try{
  const url=new URL(d.url);if(!['https:','http:'].includes(url.protocol))throw new Error('Geçersiz video adresi');
  const mode=d.type==='movie-play'?'play':'probe';const tab=await chrome.tabs.create({url:url.href,active:mode==='play'});
  const job={...d,mode,tabId:tab.id,frameId:null};movieJobs.set(d.requestId,job);
  job.timer=setTimeout(()=>movieFinish(job,job.passive?{ok:true,status:job.waitingCode||'unconfirmed',reason:job.waiting||'Sayfa/oynatıcı yanıt vermedi; erişim veya kullanıcı etkileşimi gerekebilir',video_found:!!job.videoFound}:{error:job.waiting||'Sayfadan oynatıcı yanıtı alınamadı; eklentiyi yeniden yükleyin'}),Math.min(22000,Math.max(3000,d.timeout||18000)));
  await chrome.tabs.update(tab.id,{muted:true});
  if(!movieJobs.has(d.requestId))return;
  job.windowId=tab.windowId;
  if(mode==='play'){job.previousState=(await chrome.windows.get(tab.windowId)).state;await chrome.windows.update(tab.windowId,{focused:true,state:'fullscreen'});}

  job.retry=setInterval(()=>movieKick(job),1200);movieKick(job);
 }catch(e){const job=movieJobs.get(d.requestId);if(job)await movieFinish(job,{error:e.message});else if(socket?.readyState===1)socket.send(JSON.stringify({requestId:d.requestId,error:e.message}));}
}
chrome.tabs.onUpdated.addListener((id,change)=>{if(change.status==='complete')for(const job of movieJobs.values())if(job.tabId===id)movieKick(job)});
chrome.runtime.onMessage.addListener(async(message,sender)=>{
 if(message.type==='movie-exit'&&sender.tab&&movieWindows.has(sender.tab.id)){const w=movieWindows.get(sender.tab.id);movieWindows.delete(sender.tab.id);await chrome.windows.update(w.windowId,{state:w.state==='fullscreen'?'normal':w.state});return;}
 if(message.type!=='movie-state'||!sender.tab)return;
 const job=movieJobs.get(message.requestId);if(!job||job.tabId!==sender.tab.id)return;
 if(message.state==='waiting'){recordDiagnosis(job,message);return;}
 if(message.state==='ready'&&job.passive){await movieFinish(job,{ok:true,status:'ready',duration:message.duration,turkish_subtitles:message.turkish_subtitles===true,evidence:message.evidence,reason:message.reason});return;}
 if(message.state==='gesture-needed'){
  if(job.passive||job.gestureSent)return;job.gestureSent=true;job.frameId=sender.frameId;
  movieActivation=movieActivation.catch(()=>{}).then(async()=>{
   if(!movieJobs.has(job.requestId))return;
   const previous=(await chrome.tabs.query({active:true,lastFocusedWindow:true}))[0];
   if(previous&&previous.id!==job.tabId)job.previousTab=previous;
   const tab=await chrome.tabs.update(job.tabId,{active:true});await chrome.windows.update(tab.windowId,{focused:true});
   await chrome.tabs.sendMessage(job.tabId,{type:'movie-activate',requestId:job.requestId},{frameId:sender.frameId});
   if(!movieJobs.has(job.requestId))return;
   const done=new Promise(resolve=>job.releaseActivation=resolve);
   if(socket?.readyState===1)socket.send(JSON.stringify({type:'movie-gesture',requestId:job.requestId}));
   await done;
  }).catch(()=>movieFinish(job,{error:'Oynatıcı sekmesi etkinleştirilemedi'}));
 }else if(message.state==='playable'&&job.mode==='probe'||message.state==='playing'&&job.mode==='play'){
  const tab=await chrome.tabs.get(job.tabId);
  await movieFinish(job,{ok:true,status:'verified',tabId:job.tabId,url:tab.url,duration:message.duration,turkish_subtitles:message.turkish_subtitles===true,turkish_audio:message.turkish_audio===true,fullscreen:job.mode==='play'});
 }else if(message.state==='unavailable'){
  if(sender.frameId===0||job.frameId===sender.frameId)await movieFinish(job,job.passive?{ok:true,status:message.code||'unavailable',reason:message.reason||'Bu video kullanılamıyor'}:{error:message.reason||'Bu video kullanılamıyor'});
  else recordDiagnosis(job,{...message,code:message.code||'media_error'});
 }
});

chrome.tabs.onRemoved.addListener(tabId=>movieWindows.delete(tabId));

// Discard unsolicited windows opened by a source during an automated playback check.
chrome.tabs.onCreated.addListener(tab=>{if(tab.openerTabId&&[...movieJobs.values()].some(job=>job.tabId===tab.openerTabId))chrome.tabs.remove(tab.id).catch(()=>{})});

// Search uses the user's browser network/session. No result is treated as video proof.
const movieSearches=new Map(),movieSearchBatches=new Map();
function recordDiagnosis(job,message){
 const ranks={subtitles_unknown:9,media_error:8,region_unavailable:8,media_pending:7,player_not_loaded:4,resource_error:3,account_required:2,trailer:2,interaction_required:1};
 const rank=ranks[message.code]||0;job.videoFound=job.videoFound||message.videoFound;
 if(rank>=(job.waitingRank||0)){job.waitingRank=rank;job.waiting=message.reason;job.waitingCode=message.code;}
}
async function movieSearch(d){
 const batch={cancelled:false,tabs:new Set()};movieSearchBatches.set(d.requestId,batch);
 const urls=[];const diagnostics=[];const requests=(d.names||[]).slice(0,2).map(query=>({query,engine:'site'}));
 for(const query of (d.queries||[]).slice(0,3))for(const engine of ['google','bing'])requests.push({query:String(query).slice(0,250),engine});
 async function one(item){
  const url=item.engine==='site'?'https://www.hdfilmcehennemi.nl/film-robotu-1/':item.engine==='google'?'https://www.google.com/search?hl=tr&num=10&q=':'https://www.bing.com/search?q=';
  let tab;
  try{
   tab=await chrome.tabs.create({url:item.engine==='site'?url:url+encodeURIComponent(item.query),active:false});batch.tabs.add(tab.id);
   const result=await new Promise(resolve=>{
    const timer=setTimeout(()=>resolve({error:item.engine+': arama yanıt vermedi veya doğrulama istiyor'}),7500);
    const retry=setInterval(()=>chrome.tabs.sendMessage(tab.id,{type:'movie-search-control',requestId:d.requestId,query:item.query}).catch(()=>{}),700);
    movieSearches.set(tab.id,{resolve:value=>{clearTimeout(timer);clearInterval(retry);resolve(value)}});
   });
   urls.push(...(result.links||[]));if(result.links?.length&&socket?.readyState===1)socket.send(JSON.stringify({type:'movie-search-results',requestId:d.requestId,links:result.links}));if(result.error)diagnostics.push(result.error);
  }catch{diagnostics.push(item.engine+': arama sekmesi açılamadı')}
  finally{if(tab){movieSearches.get(tab.id)?.resolve({});movieSearches.delete(tab.id);batch.tabs.delete(tab.id);await chrome.tabs.remove(tab.id).catch(()=>{})}}
 }
 // At most two search tabs; every tab has its own cleanup deadline.
 const queue=[...requests];await Promise.all([0,1].map(async()=>{while(queue.length&&!batch.cancelled)await one(queue.shift())}));
 movieSearchBatches.delete(d.requestId);
 if(!batch.cancelled&&socket?.readyState===1)socket.send(JSON.stringify({requestId:d.requestId,ok:true,links:urls.slice(0,120),diagnostics}));
}
chrome.runtime.onMessage.addListener((message,sender)=>{
 if(message.type==='movie-search-result'&&sender.tab&&movieSearches.has(sender.tab.id))movieSearches.get(sender.tab.id).resolve({links:message.links,error:message.error});
});
