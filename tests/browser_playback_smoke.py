"""Real MV3 extension tests against local videos; no platform account or external film."""
import asyncio
import json
from pathlib import Path
import subprocess
import tempfile
from aiohttp import web,WSMsgType
from playwright.async_api import async_playwright

async def main():
    output=Path('.state/playback-smoke');output.mkdir(parents=True,exist_ok=True)
    for name,duration in (('movie',1200),('trailer',10)):
        path=output/(name+'.webm')
        if not path.exists():subprocess.run(['ffmpeg','-v','error','-f','lavfi','-i',f'color=c=black:s=32x32:r=1:d={duration}','-c:v','libvpx','-deadline','realtime','-cpu-used','8','-b:v','8k','-an','-y',str(path)],check=True)
    connected=asyncio.Event();pending={};socket=None;context=None
    async def browser(request):
        nonlocal socket
        socket=web.WebSocketResponse();await socket.prepare(request);connected.set()
        async for msg in socket:
            if msg.type!=WSMsgType.TEXT:continue
            data=json.loads(msg.data);ident=data.get('requestId')
            if data.get('type')=='movie-gesture':
                page=next(p for p in context.pages if p.url.endswith(('/movie','/nested')))
                await page.keyboard.press('Space') # trusted input, as sent by the Windows adapter
            elif ident in pending and not pending[ident].done():pending[ident].set_result(data)
        return socket
    async def page(request):
        path=request.path
        if path.endswith('.webm'):return web.FileResponse(output/path[1:])
        if path=='/sub.vtt':return web.Response(text='WEBVTT\n\n00:00.000 --> 19:59.000\nTürkçe altyazı testi\n',content_type='text/vtt')
        if path=='/blocked':body='<div role="alert">Bu video ülkenizde mevcut değil. This video is unavailable.</div>'
        elif path=='/nested':body='<iframe src="http://localhost:8765/inner" allow="autoplay; fullscreen" allowfullscreen></iframe>'
        else:
            source='trailer' if path=='/info' else 'movie'
            body=f'<h1>Fixture Movie</h1><video controls muted preload="auto" style="width:320px" src="/{source}.webm"><track default kind="subtitles" srclang="tr" src="/sub.vtt"></video>'
        if path=='/lazy':body=body.replace('preload="auto"','preload="none"')
        if path=='/turkish':body=body.replace('<track default kind="subtitles" srclang="tr" src="/sub.vtt">','')
        title='Player' if path=='/inner' else 'Fixture Movie'
        return web.Response(text=f'<!doctype html><title>{title}</title>{body}',content_type='text/html')
    app=web.Application();app.router.add_get('/api/browser',browser);app.router.add_get('/{path:.*}',page)
    runner=web.AppRunner(app);await runner.setup();await web.TCPSite(runner,'0.0.0.0',8765).start()
    async def command(kind,path,timeout=12000,turkish=False):
        ident=str(len(pending)+1);future=asyncio.get_running_loop().create_future();pending[ident]=future
        await socket.send_json({'type':kind,'requestId':ident,'url':'http://127.0.0.1:8765'+path,'movie':{'title':'Fixture Movie','original_title':'Fixture Movie','runtime':20,'turkish_original':turkish},'turkish_subtitles':False,'timeout':timeout})
        return await asyncio.wait_for(future,timeout/1000+10)
    try:
        async with async_playwright() as playwright:
            with tempfile.TemporaryDirectory(prefix='sofa-chromium-') as temp:
                extension=str(Path('browser').resolve())
                context=await playwright.chromium.launch_persistent_context(temp,channel='chromium',headless=True,args=[f'--disable-extensions-except={extension}',f'--load-extension={extension}'])
                await asyncio.wait_for(connected.wait(),15)
                initial=len(context.pages)
                result=await command('movie-probe','/movie');assert result.get('ok'),result
                assert result['duration']>=1200 and result['turkish_subtitles'];assert len(context.pages)==initial
                print('Real Chromium: advancing full-length video verified; silent probe tab closed',flush=True)
                result=await command('movie-probe','/lazy');assert result.get('ok'),result
                result=await command('movie-probe','/turkish',turkish=True);assert result.get('ok') and not result['turkish_subtitles'],result
                result=await command('movie-probe','/turkish',3000);assert result.get('error'),result
                print('Real Chromium: lazy metadata loads; Turkish original plays without subtitles; foreign movie rejected without subtitles',flush=True)
                for path in ('/info','/blocked'):
                    result=await command('movie-probe',path,3000);assert result.get('error'),result
                print('Real Chromium: trailer/info page and unavailable-region page excluded',flush=True)
                result=await command('movie-probe','/nested');assert result.get('ok'),result
                print('Real Chromium: cross-origin iframe player verified',flush=True)
                result=await command('movie-play','/movie');assert result.get('ok') and result.get('fullscreen'),result
                played=next(p for p in context.pages if p.url.endswith('/movie'))
                await played.wait_for_function("!document.querySelector('video').paused && !document.querySelector('video').muted && document.querySelector('video').currentTime>0")
                rect=await played.locator('video').bounding_box();size=await played.evaluate('({w:innerWidth,h:innerHeight})');assert rect['width']>=size['w']*.9 and rect['height']>=size['h']*.9,(rect,size)
                await played.screenshot(path=str(output/'fullscreen.png'))
                await played.keyboard.press('Escape');await played.wait_for_function("document.querySelector('video').getAttribute('style')==='width:320px'")
                print('Real Chromium: trusted input starts unmuted movie, enters fullscreen, Escape restores layout',flush=True)
                await played.close()
                result=await command('movie-play','/nested');assert result.get('ok') and result.get('fullscreen'),result
                played=next(p for p in context.pages if p.url.endswith('/nested'))
                frame=next(f for f in played.frames if f.url.endswith('/inner'))
                await frame.wait_for_function("!document.querySelector('video').paused&&!document.querySelector('video').muted")
                rect=await played.locator('iframe').bounding_box();size=await played.evaluate('({w:innerWidth,h:innerHeight})');assert rect['width']>=size['w']*.9 and rect['height']>=size['h']*.9,(rect,size)
                await played.keyboard.press('Escape');await played.wait_for_function("!document.querySelector('iframe').getAttribute('style')")
                print('Real Chromium: nested iframe starts full-screen and Escape restores parent frame',flush=True)
                await context.close()
    finally:await runner.cleanup()
if __name__=='__main__':asyncio.run(main())
