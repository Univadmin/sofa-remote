'use strict';
let socket, connecting=false;
async function publish(){if(socket?.readyState!==1)return;const tabs=await chrome.tabs.query({});socket.send(JSON.stringify({type:'tabs',tabs:tabs.map(t=>({id:t.id,windowId:t.windowId,title:t.title||'',url:t.url||'',active:t.active}))}))}
async function command(d){
  if(d.type!=='tab')return;
  if(d.action==='activate'){const tab=await chrome.tabs.update(d.tabId,{active:true});await chrome.windows.update(tab.windowId,{focused:true})}
  else if(d.action==='close')await chrome.tabs.remove(d.tabId);
  else if(d.action==='reload')await chrome.tabs.reload(d.tabId);
  else if(d.action==='duplicate')await chrome.tabs.duplicate(d.tabId);
  else if(d.action==='new'){const url=d.url||'https://www.google.com';if(!/^https?:\/\//.test(url))throw new Error('Geçersiz adres');await chrome.tabs.create({url})}
  else if(['next','previous'].includes(d.action)){const tabs=await chrome.tabs.query({lastFocusedWindow:true});const at=tabs.findIndex(t=>t.active);if(tabs.length)await chrome.tabs.update(tabs[(at+(d.action==='next'?1:-1)+tabs.length)%tabs.length].id,{active:true})}
  await publish();
}
function connect(){
  if(connecting||socket?.readyState===0||socket?.readyState===1)return;connecting=true;
  socket=new WebSocket('ws://127.0.0.1:8765/api/browser');
  socket.onopen=()=>{connecting=false;publish()};
  socket.onmessage=async event=>{const d=JSON.parse(event.data);if(d.type!=='tab')return;try{await command(d);socket.send(JSON.stringify({requestId:d.requestId,ok:true}))}catch(e){if(socket.readyState===1)socket.send(JSON.stringify({requestId:d.requestId,error:e.message}))}};
  socket.onclose=()=>{connecting=false;setTimeout(connect,3000)};socket.onerror=()=>{connecting=false};
}
chrome.tabs.onActivated.addListener(publish);chrome.tabs.onUpdated.addListener(publish);chrome.tabs.onRemoved.addListener(publish);chrome.tabs.onCreated.addListener(publish);
chrome.alarms.create('sofa-reconnect',{periodInMinutes:0.5});chrome.alarms.onAlarm.addListener(connect);
setInterval(()=>{if(socket?.readyState===1){socket.send(JSON.stringify({type:'heartbeat'}));publish()}else connect()},20000);
connect();
