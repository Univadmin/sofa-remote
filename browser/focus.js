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
