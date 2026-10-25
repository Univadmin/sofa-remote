// Only focus state is shared; field contents never leave the page.
'use strict';
let previous='';
function report(){
 const e=document.activeElement;
 const active=!!e&&(e.matches('textarea:not([readonly]):not([disabled]),input:not([readonly]):not([disabled])')&&!['button','submit','reset','checkbox','radio','range','color','file','hidden','image'].includes(e.type)||e.isContentEditable);
 const key=active?'active':'inactive';if(previous===key)return;previous=key;
 chrome.runtime.sendMessage({type:'keyboard-focus',active}).catch(()=>{});
}
document.addEventListener('focusin',report,true);document.addEventListener('focusout',()=>setTimeout(report,0),true);
window.addEventListener('focus',()=>{previous='';report()});report();
chrome.runtime.onMessage.addListener(message=>{if(message.type==='focus-probe'){previous='';report();}});

// Only playback metadata is reported; a server-side selected-film session is required.
let filmTracking=false;
chrome.runtime.onMessage.addListener(message=>{if(message.type==='movie-track')filmTracking=true});
setInterval(()=>{
 if(!filmTracking)return;
 const videos=[...document.querySelectorAll('video')].filter(v=>Number.isFinite(v.duration)&&v.duration>=1200);
 const video=videos.find(v=>!v.paused)||videos[0];if(!video)return;
 const tracks=[...video.textTracks],tr=tracks.find(t=>/^tr(?:-|$)|^tur$/i.test(t.language));
 if(tr&&tracks.every(t=>t.mode!=='showing'))tr.mode='showing';
 chrome.runtime.sendMessage({type:'movie-progress',title:navigator.mediaSession?.metadata?.title||document.title,duration:video.duration,position:video.currentTime,playing:!video.paused&&!video.ended&&!video.seeking,turkish_subtitles:!!tr}).catch(()=>{});
},10000);
