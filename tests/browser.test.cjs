const {test}=require('node:test');const assert=require('node:assert/strict');const vm=require('node:vm');const fs=require('node:fs');
test('closing a tab acknowledges success before a failing metadata refresh',async()=>{
 const messages=[],closed=[],event={addListener(){}};
 class Socket{constructor(){this.readyState=1;this.send=data=>messages.push(JSON.parse(data));Socket.instance=this;}}
 const chrome={tabs:{query:async()=>{throw new Error('metadata temporarily unavailable')},remove:async id=>closed.push(id),onActivated:event,onUpdated:event,onRemoved:event,onCreated:event},windows:{onFocusChanged:event},runtime:{onMessage:event},alarms:{create(){},onAlarm:event}};
 vm.runInNewContext(fs.readFileSync('browser/background.js','utf8'),{chrome,WebSocket:Socket,setTimeout(){},setInterval(){}});
 await Socket.instance.onmessage({data:JSON.stringify({type:'tab',action:'close',tabId:101,requestId:'close-1'})});
 assert.deepEqual(closed,[101]);assert.deepEqual(messages,[{requestId:'close-1',ok:true}]);
});
