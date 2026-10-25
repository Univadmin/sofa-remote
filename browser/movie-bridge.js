/* Runs beside page players: no stream URLs, credentials or network interception. */
'use strict';
(()=>{
 const tr=t=>/^(tr|tur)(-|$)/i.test(t.language||t.srclang||'')||/^(türkçe|turkce|turkish)(\b|\s|$)/i.test(t.label||'');
 window.addEventListener('message',event=>{
  const m=event.data;if(event.source!==window||m?.type!=='sofa-player-command'||typeof m.requestId!=='string'||!['inspect','start','gesture'].includes(m.action))return;
  let turkish=false,containerId=null;
  const act=player=>{try{if(m.action!=='inspect'){player.muted?.(m.mode==='probe');Promise.resolve(player.play?.()).catch(()=>{})}}catch{}};
  try{
   const players=window.videojs?.getPlayers?.()||{};
   for(const p of Object.values(players)){if(!p)continue;const tracks=Array.from(p.textTracks?.()||[]);for(const t of tracks)if(tr(t)){t.mode='showing';turkish=true;containerId=p.el?.()?.id||null}act(p)}
  }catch{}
  try{
   if(typeof window.jwplayer==='function')for(const el of document.querySelectorAll('.jwplayer')){
    const p=window.jwplayer(el.id),tracks=p.getCaptionsList?.()||[];const index=tracks.findIndex(tr);
    if(index>=0){p.setCurrentCaptions(index);turkish=true;containerId=p.getContainer?.()?.id||el.id}
    if(m.action!=='inspect'){p.setMute?.(m.mode==='probe');p.play?.(true)}
   }
  }catch{}
  try{
   // Playerjs keeps captions and HLS startup outside native video.textTracks.
   const players=new Set([window.player,window.player1,window.player2,window.pjs,typeof player!=='undefined'?player:null]);
   for(const p of players){
    if(typeof p?.api!=='function')continue;
    const available=p.api('subtitles');
    const tracks=Array.isArray(available)?available:typeof available==='string'?[...available.matchAll(/\[([^\]]+)\]/g)].map(m=>m[1]):[];
    const index=tracks.findIndex(t=>tr(typeof t==='string'?{label:t}:t));
    if(index>=0){p.api('subtitle',index);turkish=true;containerId=p.api('id')||null}
    if(m.action!=='inspect'){p.api(m.mode==='probe'?'mute':'unmute');p.api('play')}
   }
  }catch{}
  window.postMessage({type:'sofa-player-result',requestId:m.requestId,turkish_subtitles:turkish,containerId:typeof containerId==='string'?containerId:null},'*');
 });
})();
