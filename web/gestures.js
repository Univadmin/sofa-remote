(function(root){
'use strict';
class MouseGesture {
  constructor(options){this.o=options;this.points=new Map();this.lastTap=null;this.frame=null;this.mx=0;this.my=0;this.scrollY=0;this.gesture=null;this.held=false;}
  now(){return this.o.now?this.o.now():performance.now()}
  down(e){
    if(this.points.size===0){
      const tap=this.lastTap,manual=this.o.manual?.();
      this.gesture={start:this.now(),distance:0,fingers:1,x:e.clientX,y:e.clientY,moved:false};
      if(!manual&&tap&&this.now()-tap.time<=350&&Math.hypot(e.clientX-tap.x,e.clientY-tap.y)<35){this.held=true;this.o.button('left',true);this.lastTap=null;}
    }
    this.points.set(e.pointerId,{x:e.clientX,y:e.clientY});
    this.gesture.fingers=Math.max(this.gesture.fingers,this.points.size);
    if(this.points.size>1&&this.held){this.o.button('left',false);this.held=false;this.lastTap=null;}
  }
  move(e){
    const p=this.points.get(e.pointerId);if(!p||!this.gesture)return;
    const dx=e.clientX-p.x,dy=e.clientY-p.y;this.points.set(e.pointerId,{x:e.clientX,y:e.clientY});
    const g=this.gesture;g.distance+=Math.abs(dx)+Math.abs(dy);g.moved=g.distance>10;
    if(this.points.size>1){this.scrollY+=dy;if(Math.abs(this.scrollY)>=18){const n=Math.trunc(this.scrollY/18);this.o.scroll(Math.max(-20,Math.min(20,n)));this.scrollY-=n*18;}}
    else {const speed=this.o.speed?.()??1.6;this.mx+=dx*speed;this.my+=dy*speed;if(this.frame===null)this.frame=this.o.schedule(()=>{this.frame=null;this.flush()});}
  }
  flush(){
    if(this.frame!==null){this.o.cancelFrame(this.frame);this.frame=null;}
    const x=Math.max(-1000,Math.min(1000,Math.round(this.mx))),y=Math.max(-1000,Math.min(1000,Math.round(this.my)));
    if(x||y)this.o.move(x,y);this.mx=this.my=0;
  }
  up(e){
    if(!this.points.has(e.pointerId))return null;this.move(e);this.points.delete(e.pointerId);if(this.points.size)return null;
    this.flush();const g=this.gesture;this.gesture=null;this.scrollY=0;let clicked=false;
    if(this.held){this.o.button('left',false);this.held=false;this.lastTap=null;}
    else if(!this.o.manual?.()){
      const quick=!g.moved&&this.now()-g.start<350;
      if(g.fingers>=2&&quick){this.o.click('right');clicked=true;this.lastTap=null;}
      else if(g.fingers===1&&(quick||this.o.releaseClick?.())){
        this.o.click(this.o.lefty?.()?'right':'left');clicked=true;
        this.lastTap=quick?{time:this.now(),x:e.clientX,y:e.clientY}:null;
      }else this.lastTap=null;
    }
    return {moved:g.moved,clicked};
  }
  reset(){
    if(this.held)this.o.button('left',false);this.held=false;this.points.clear();this.gesture=null;this.lastTap=null;
    if(this.frame!==null)this.o.cancelFrame(this.frame);this.frame=null;this.mx=this.my=this.scrollY=0;
  }
}
root.MouseGesture=MouseGesture;if(typeof module!=='undefined')module.exports={MouseGesture};
})(typeof window==='undefined'?globalThis:window);
