/* Playback checks run only on tabs explicitly opened by a film command. */
'use strict';
(()=>{
 let control=null,timer=null,selected=null,firstPosition=null,advances=0,reported=false,armed=false,clickedPlay=false;const prepared=new WeakSet();const styles=new Map();
 const norm=s=>String(s||'').toLocaleLowerCase('tr').normalize('NFKD').replace(/[^\p{L}\p{N}]/gu,'');
 const unavailable=/bu (?:video|içerik|yapım) (?:şu anda )?(?:kullanılamıyor|izlenemiyor|mevcut değil)|ülkenizde (?:mevcut|kullanılabilir) değil|bulunduğunuz (?:bölgede|konumda).*?(?:mevcut değil|izlenemiyor)|not available in your (?:country|region|location)|this (?:video|title|content) is (?:currently )?(?:unavailable|not available)|video unavailable/i;
 function signal(state,extra={}){chrome.runtime.sendMessage({type:'movie-state',requestId:control.requestId,state,...extra}).catch(()=>{})}
 function restore(){for(const [el,value] of styles){if(value===null)el.removeAttribute('style');else el.setAttribute('style',value)}styles.clear();}
 function stop(){restore();clearInterval(timer);timer=null;armed=false;control=null;selected=null;}
 function finish(state,extra={}){if(reported||!control)return;reported=true;signal(state,extra);if(control.mode==='probe')selected?.pause();clearInterval(timer);timer=null;armed=false;}
 function videos(root=document){let found=[...root.querySelectorAll('video')];for(const el of root.querySelectorAll('*'))if(el.shadowRoot)found.push(...videos(el.shadowRoot));return found;}
 function matches(video){
  if(!Number.isFinite(video.duration)||video.duration<1200)return false;
  const seconds=Number(control.movie.runtime)*60;
  if(seconds>0&&(video.duration<seconds*.75||video.duration>seconds*1.3))return false;
  const title=norm(navigator.mediaSession?.metadata?.title||document.title);
  return control.titleConfirmed||[control.movie.title,control.movie.original_title].some(n=>{const name=norm(n);return name&&(name.length>=4?title.includes(name):title===name)});
 }
 function expand(element){
  if(!styles.has(element))styles.set(element,element.getAttribute('style'));
  element.style.setProperty('position','fixed','important');element.style.setProperty('inset','0','important');
  for(const key of ['width','height'])element.style.setProperty(key,key==='width'?'100vw':'100vh','important');
  element.style.setProperty('z-index','2147483647','important');element.style.setProperty('object-fit','contain','important');element.style.setProperty('background','black','important');
  for(let p=element.parentElement;p;p=p.parentElement){if(!styles.has(p))styles.set(p,p.getAttribute('style'));for(const key of ['transform','filter','contain','perspective','will-change','clip-path'])p.style.setProperty(key,'none','important');}
  if(window!==window.top)window.parent.postMessage({sofaCinema:control?.requestId},'*');
 }
 window.addEventListener('message',e=>{
  if(!control||![e.data?.sofaCinema,e.data?.sofaCinemaExit].includes(control.requestId))return;
  const frame=[...document.querySelectorAll('iframe')].find(f=>f.contentWindow===e.source);
  if(frame){if(e.data.sofaCinemaExit){restore();if(window!==window.top)window.parent.postMessage({sofaCinemaExit:control.requestId},'*');}else{frame.allowFullscreen=true;expand(frame)}}
 });
 function startVisible(video,gesture=false){
  video.muted=false;video.volume=video.volume||1;expand(video);
  if(gesture&&!document.fullscreenElement)video.requestFullscreen?.().catch(()=>{});
  video.play().catch(()=>{if(!armed){armed=true;signal('gesture-needed')}});
 }
 document.addEventListener('keydown',e=>{
  if(control&&e.isTrusted&&e.code==='Escape'){restore();if(window!==window.top)window.parent.postMessage({sofaCinemaExit:control.requestId},'*');chrome.runtime.sendMessage({type:'movie-exit'}).catch(()=>{});return;}
  if(!control||control.mode!=='play'||!selected||!armed||!e.isTrusted||e.code!=='Space')return;
  e.preventDefault();e.stopImmediatePropagation();armed=false;startVisible(selected,true);
 },true);
 function tick(){
  if(!control||reported)return;
  const alerts=[...document.querySelectorAll('[role="alert"],.error-message,.player-error,[data-uia*="error"]')].map(e=>e.innerText||'').join(' ');
  const bodyText=document.body?.innerText||'';
  if(unavailable.test(alerts)||window===window.top&&bodyText.length<2500&&unavailable.test(bodyText))return finish('unavailable',{reason:'Bu video mevcut oturumda veya bölgede kullanılamıyor'});
  const all=videos();
  if(control.titleConfirmed)for(const v of all)if(!prepared.has(v)){prepared.add(v);v.muted=true;v.preload='auto';if(v.readyState===0&&(v.currentSrc||v.getAttribute('src')||v.querySelector('source')))v.load();v.play().catch(()=>{});}
  const candidates=all.filter(matches);const video=candidates.find(v=>!v.paused)||candidates[0];
  if(!video){
   if(!clickedPlay&&control.titleConfirmed){const button=document.querySelector('[data-uia="play-button"],[data-testid="play-button"],button[aria-label="Play"],button[aria-label="Oynat"],.vjs-big-play-button,.jw-icon-display,.plyr__control--overlaid,[data-plyr="play"]');
    const label=(button?.getAttribute('aria-label')||button?.textContent||'').trim();
    if(button&&(button.matches('.vjs-big-play-button,.jw-icon-display,.plyr__control--overlaid,[data-plyr="play"]')||/^(play|oynat|filmi oynat|play movie|watch now|şimdi izle|resume|devam et)$/i.test(label))){clickedPlay=true;button.click()}
   }
   return;
  }
  if(selected&&selected!==video){firstPosition=null;advances=0;}selected=video;
  if(video.error)return finish('unavailable',{reason:'Video kaynağı oynatılamıyor'});
  const tracks=[...video.textTracks],tr=tracks.find(t=>/^tr(?:-|$)|^tur$/i.test(t.language));
  const turkishAudio=[...(video.audioTracks||[])].some(t=>t.enabled&&/^tr(?:-|$)|^tur$/i.test(t.language));
  if(!tr&&!control.turkish_subtitles&&!control.movie.turkish_original)return;
  if(tr){for(const t of tracks)if(t!==tr)t.mode='disabled';tr.mode='showing'}
  if(video.readyState<2)return;
  if(firstPosition===null){firstPosition=video.currentTime;
   if(control.mode==='probe'){video.muted=true;video.play().catch(()=>{})}
   else{video.tabIndex=0;video.focus();armed=true;signal('gesture-needed');startVisible(video)}
   return;
  }
  if(!video.paused&&!video.ended&&!video.seeking&&video.currentTime>firstPosition+.25)advances++;else advances=0;
  if(advances>=2&&(control.mode==='probe'||!video.muted))finish(control.mode==='probe'?'playable':'playing',{duration:video.duration,turkish_subtitles:!!tr||!!control.turkish_subtitles,turkish_audio:turkishAudio,fullscreen:!!document.fullscreenElement,position:video.currentTime});
 }
 chrome.runtime.onMessage.addListener(message=>{
  if(message.type==='movie-stop'){stop();return;}
  if(message.type!=='movie-control')return;
  if(control?.requestId===message.requestId){control.titleConfirmed=control.titleConfirmed||message.titleConfirmed;return;}
  stop();control=message;reported=false;firstPosition=null;advances=0;clickedPlay=false;
  timer=setInterval(tick,500);tick();
 });
})();
