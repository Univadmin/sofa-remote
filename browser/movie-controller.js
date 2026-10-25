/* Coordinates isolated checks in the user's authenticated browser, never purchases. */
'use strict';
const movieJobs=new Map(),movieWindows=new Map();
function movieName(s){return String(s||'').toLocaleLowerCase('tr').normalize('NFKD').replace(/[^\p{L}\p{N}]/gu,'')}
async function movieKick(job){
 try{const tab=await chrome.tabs.get(job.tabId);const title=movieName(tab.title);
  const titleConfirmed=[job.movie.title,job.movie.original_title].some(n=>{n=movieName(n);return n&&(n.length>=4?title.includes(n):title===n)});
  await chrome.tabs.sendMessage(job.tabId,{type:'movie-control',requestId:job.requestId,mode:job.mode,movie:job.movie,turkish_subtitles:job.turkish_subtitles,titleConfirmed});
 }catch{}
}
async function movieFinish(job,result){
 if(!movieJobs.has(job.requestId))return;
 movieJobs.delete(job.requestId);clearTimeout(job.timer);clearInterval(job.retry);
 if(job.mode==='probe'||!result.ok){await chrome.tabs.remove(job.tabId).catch(()=>{});if(job.mode==='play'&&job.previousState)await chrome.windows.update(job.windowId,{state:job.previousState}).catch(()=>{});}
 else{await chrome.tabs.update(job.tabId,{muted:false});movieWindows.set(job.tabId,{windowId:job.windowId,state:job.previousState});filmTabs.add(job.tabId);chrome.tabs.sendMessage(job.tabId,{type:'movie-track'}).catch(()=>{})}
 if(socket?.readyState===1)socket.send(JSON.stringify({requestId:job.requestId,...result}));
}
async function movieCommand(d){
 if(d.type==='movie-cancel'){
  const job=movieJobs.get(d.requestId);if(job)await movieFinish(job,{error:'Kontrol iptal edildi'});return;
 }
 if(!['movie-probe','movie-play'].includes(d.type))return;
 try{
  const url=new URL(d.url);if(!['https:','http:'].includes(url.protocol))throw new Error('Geçersiz video adresi');
  const mode=d.type==='movie-play'?'play':'probe';const tab=await chrome.tabs.create({url:'about:blank',active:mode==='play'});
  const job={...d,mode,tabId:tab.id,frameId:null};movieJobs.set(d.requestId,job);
  job.timer=setTimeout(()=>movieFinish(job,{error:'Film süresine uygun, oynatım doğrulanamadı'}),Math.min(22000,Math.max(3000,d.timeout||18000)));
  await chrome.tabs.update(tab.id,{muted:true,url:url.href});
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
 if(message.state==='gesture-needed'&&job.mode==='play'){
  if(job.gestureSent)return;
  const tab=await chrome.tabs.get(job.tabId),win=await chrome.windows.get(tab.windowId);
  if(!tab.active||!win.focused)return;
  job.gestureSent=true;job.frameId=sender.frameId;
  if(socket?.readyState===1)socket.send(JSON.stringify({type:'movie-gesture',requestId:job.requestId}));
 }else if(message.state==='playable'&&job.mode==='probe'||message.state==='playing'&&job.mode==='play'){
  const tab=await chrome.tabs.get(job.tabId);
  await movieFinish(job,{ok:true,tabId:job.tabId,url:tab.url,duration:message.duration,turkish_subtitles:message.turkish_subtitles===true,turkish_audio:message.turkish_audio===true,fullscreen:job.mode==='play'});
 }else if(message.state==='unavailable'&&(sender.frameId===0||job.frameId===sender.frameId))await movieFinish(job,{error:message.reason||'Bu video kullanılamıyor'});
});

chrome.tabs.onRemoved.addListener(tabId=>movieWindows.delete(tabId));
