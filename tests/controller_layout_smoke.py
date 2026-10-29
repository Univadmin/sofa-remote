"""Touch, compact controller, manual keyboard and shortcut checks in real Chromium."""
import asyncio
import sys
import tempfile
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from aiohttp import web
from playwright.async_api import async_playwright
from server.app import create_app
from server.input import DryRun,KEYS

async def main():
    with tempfile.TemporaryDirectory() as state:
        adapter=DryRun();app=create_app(adapter,state);remote=app['remote']
        runner=web.AppRunner(app,shutdown_timeout=1);await runner.setup();await web.TCPSite(runner,'127.0.0.1',18768).start()
        try:
            async with async_playwright() as p:
                browser=await p.chromium.launch()
                context=await browser.new_context(viewport={'width':390,'height':844},has_touch=True,is_mobile=True)
                page=await context.new_page();errors=[];page.on('pageerror',lambda error:errors.append(str(error)))
                await page.goto('http://127.0.0.1:18768');await page.wait_for_function("ws?.readyState===1")
                await page.click('#layout');await page.check('#expanded-mouse-setting');await page.click('#close-sheet')
                assert await page.locator('.compact-transport button').count()==4
                await page.click('.compact-transport button:nth-child(2)');await asyncio.sleep(.1)
                assert ('keys',['PLAYPAUSE']) in adapter.events
                for size in ({'width':390,'height':844},{'width':360,'height':640},{'width':844,'height':390}):
                    await page.set_viewport_size(size)
                    bounds=await page.evaluate("""(()=>{const m=document.querySelector('.touchpad').getBoundingClientRect(),w=document.querySelector('#workspace').getBoundingClientRect(),c=document.querySelector('.compact-controller').getBoundingClientRect();return {height:m.height,total:w.height,top:m.top,compactBottom:c.bottom,overflow:document.documentElement.scrollWidth>innerWidth}})()""")
                    assert bounds['height']>bounds['total']*.65,bounds
                    assert bounds['top']>=bounds['compactBottom'] and not bounds['overflow'],bounds
                await page.set_viewport_size({'width':390,'height':844})
                await page.screenshot(path='.state/expanded-media.png')
                # Immediate swipe moves without clicking; tap clicks; second held tap drags.
                cdp=await context.new_cdp_session(page);box=await page.locator('.touchpad').bounding_box();x,y=box['x']+100,box['y']+100
                async def touch(kind,x=x,y=y):
                    await cdp.send('Input.dispatchTouchEvent',{'type':kind,'touchPoints':[] if kind=='touchEnd' else [{'x':x,'y':y}]})
                adapter.events.clear();await touch('touchStart');await touch('touchMove',x+70,y+20);await asyncio.sleep(.1);await touch('touchEnd');await asyncio.sleep(.1)
                assert any(event[0]=='move' for event in adapter.events),adapter.events
                assert not any(event[0]=='button' for event in adapter.events),adapter.events
                await asyncio.sleep(.4);adapter.events.clear();await touch('touchStart');await touch('touchEnd');await asyncio.sleep(.1);await touch('touchStart');await touch('touchMove',x+40,y+30);await touch('touchEnd');await asyncio.sleep(.1)
                buttons=[event for event in adapter.events if event[0]=='button'];assert buttons==[('button','left',True),('button','left',False)]*2,adapter.events
                await page.click('#layout');await page.select_option('#layout-first','keyboard');await page.select_option('#layout-second','mouse');await page.click('#close-sheet')
                assert await page.locator('.compact-editor').count()==1
                for ws in remote.sockets:await ws.send_json({'type':'keyboard-focus','active':True})
                await asyncio.sleep(.2);assert not await page.locator('.compact-editor').evaluate('(el)=>el===document.activeElement')
                await page.click('.compact-editor');await page.keyboard.type('abc');await asyncio.sleep(.1)
                assert ''.join(event[1] for event in adapter.events if event[0]=='text')=='abc',adapter.events
                await page.keyboard.press('Enter');await page.locator('.compact-editor').blur()
                await page.screenshot(path='.state/expanded-keyboard.png')
                await page.click('[data-windows-shortcuts]');await page.select_option('[data-windows-group]','all')
                assert await page.locator('.windows-shortcut').count()>180
                assert await page.evaluate('windowsShortcuts.filter(x=>!x.manual).every(x=>x.keys.length>0)')
                rows=await page.evaluate('windowsShortcuts.filter(x=>!x.manual).map(x=>x.keys)')
                assert all(key in KEYS for row in rows for key in row)
                await page.fill('[data-windows-filter]','Görev Yöneticisi');await page.locator('.windows-shortcut button').click();await asyncio.sleep(.1)
                assert ('keys',['CTRL','SHIFT','ESC']) in adapter.events
                await page.fill('[data-windows-filter]','Güvenlik ekranı');assert await page.locator('.windows-shortcut button').is_disabled()
                await page.click('#close-sheet');await page.reload();await page.wait_for_selector('.compact-editor')
                assert await page.locator('.expanded-touchpad').get_attribute('id')=='pane-1'
                await page.click('#layout');await page.uncheck('#expanded-mouse-setting');await page.click('#side')
                assert await page.locator('#workspace').evaluate("el=>el.classList.contains('side')&&!el.classList.contains('mouse-expanded')")
                assert await page.locator('.pane-heading:visible').count()==2
                assert not errors,errors
                await browser.close();print('PASS expanded layouts, touch drag, manual keyboard, shortcuts, resize, persistence and normal layout')
        finally:await runner.cleanup()

if __name__=='__main__':
    Path('.state').mkdir(exist_ok=True)
    asyncio.run(main())
