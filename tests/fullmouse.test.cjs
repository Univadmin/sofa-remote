const {test}=require('node:test');
const assert=require('node:assert/strict');
const vm=require('node:vm');
const fs=require('node:fs');
const {HoldMouse}=require('../web/gestures.js');
for(const name of ['Düzen','Kısayollar','Güncelleme'])test(`${name}: opening a dialog suppresses the retargeted touch click`,()=>{
 const listeners={},sheet={open:false};let opened=0;
 const button={isConnected:true,matches:()=>false,click(){opened++;sheet.open=true;},closest(selector){return selector.includes('button')?this:null;}};
 const backdrop={closest:()=>null};
 const context={fullMouse:true,expandedPair:()=>false,globalMouse:null,HoldMouse,Map,performance:{now:()=>100},setTimeout:()=>1,clearTimeout(){},gestureOptions:options=>({...options,click(){}}),window:{},$:()=>sheet,document:{addEventListener:(name,fn)=>listeners[name]=fn,body:{classList:{toggle(){}}}}};
 const source=fs.readFileSync('web/app.js','utf8');
 vm.runInNewContext(source.slice(source.indexOf('function setupFullMouse(){'),source.indexOf('\nfunction iconFor('))+'\nsetupFullMouse();',context);
 const event=target=>({target,pointerId:1,clientX:10,clientY:10,cancelable:true,preventDefault(){this.prevented=true;},stopImmediatePropagation(){this.stopped=true;}});
 listeners.pointerdown(event(button));listeners.pointerup(event(button));
 assert.equal(opened,1);assert.equal(sheet.open,true);
 // Android can retarget the compatibility click to the newly opened backdrop.
 const ghost=event(backdrop);listeners.click(ghost);
 assert.equal(ghost.stopped,true);
 // A fresh physical touch inside the sheet must work immediately.
 listeners.pointerdown(event(backdrop));const fresh=event(backdrop);listeners.click(fresh);
 assert.equal(fresh.stopped,undefined);
});
