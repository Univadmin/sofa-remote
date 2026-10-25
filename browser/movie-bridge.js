/* Runs beside page players: no stream URLs, credentials or network interception. */
'use strict';
(()=>{
 const tr=t=>/^(tr|tur)(-|$)/i.test(t.language||t.srclang||'')||/^(türkçe|turkce|turkish)(\b|\s|$)/i.test(t.label||'');
 window.addEventListener('message',event=>{
  const m=event.data;if(event.source!==window||m?.type!=='sofa-player-command'||typeof m.requestId!=='string'||!['inspect','start','gesture'].includes(m.action))return;
  let turkish=false;
  const act=player=>{try{if(m.action!=='inspect'){player.muted?.(m.mode==='probe');Promise.resolve(player.play?.()).catch(()=>{})}}catch{}};
  try{
   const players=window.videojs?.getPlayers?.()||{};
   for(const p of Object.values(players)){if(!p)continue;const tracks=Array.from(p.textTracks?.()||[]);for(const t of tracks)if(tr(t)){t.mode='showing';turkish=true}act(p)}
  }catch{}
  try{
   if(typeof window.jwplayer==='function')for(const el of document.querySelectorAll('.jwplayer')){
    const p=window.jwplayer(el.id),tracks=p.getCaptionsList?.()||[];const index=tracks.findIndex(tr);
    if(index>=0){p.setCurrentCaptions(index);turkish=true}
    if(m.action!=='inspect'){p.setMute?.(m.mode==='probe');p.play?.(true)}
   }
  }catch{}
  window.postMessage({type:'sofa-player-result',requestId:m.requestId,turkish_subtitles:turkish},'*');
 });
})();
