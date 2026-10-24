"""Sofa Remote: same-origin mobile UI and authenticated local WebSocket."""
import argparse
import asyncio
from collections import deque
import io
import json
import math
import os
from pathlib import Path
import secrets
import socket
import sys
import time
from urllib.parse import urlsplit
from aiohttp import web, WSMsgType
from .input import Windows, DryRun, KEYS
from .network import local_address
from .version import VERSION, REPOSITORY
from .updater import Updater
from .discovery import start_discovery

ROOT = Path(getattr(sys, '_MEIPASS', Path(__file__).resolve().parent.parent))
STATE = Path(os.environ.get('LOCALAPPDATA', str(Path.home()))) / 'SofaRemote'
PROFILES = {
    'generic': {'play':['SPACE'], 'back':['LEFT'], 'forward':['RIGHT'], 'fullscreen':['F'], 'captions':['C']},
    'youtube': {'play':['K'], 'back':['J'], 'forward':['L'], 'fullscreen':['F'], 'captions':['C'], 'next':['SHIFT','N']},
    'netflix': {'play':['SPACE'], 'back':['LEFT'], 'forward':['RIGHT'], 'fullscreen':['F'], 'captions':['C']},
}

def validate_url(value):
    if not isinstance(value,str) or len(value)>2048: raise ValueError('Invalid URL')
    parsed=urlsplit(value)
    if parsed.scheme not in ('http','https') or not parsed.hostname or parsed.username or parsed.password:
        raise ValueError('Only http/https URLs without credentials are allowed')
    return value

def validate_action(data):
    if not isinstance(data,dict): raise ValueError('Object required')
    kind=data.get('type')
    if kind=='move':
        for k in ('x','y'):
            if type(data.get(k)) not in (int,float) or not math.isfinite(data[k]) or abs(data[k])>1000: raise ValueError('Invalid movement')
        return {'type':kind,'x':round(data['x']),'y':round(data['y'])}
    if kind=='scroll':
        if type(data.get('amount')) is not int or abs(data['amount'])>20: raise ValueError('Invalid scroll')
    elif kind=='button':
        if data.get('button') not in ('left','right','middle') or type(data.get('down')) is not bool: raise ValueError('Invalid button')
    elif kind=='keys':
        keys=data.get('keys')
        if not isinstance(keys,list) or not 1<=len(keys)<=6 or any(not isinstance(k,str) or k not in KEYS for k in keys): raise ValueError('Unsupported key combination')
    elif kind in ('text','clipboard_set'):
        if not isinstance(data.get('text'),str) or len(data['text'])>10000: raise ValueError('Text exceeds 10000 characters')
    elif kind=='edit':
        if type(data.get('delete')) is not int or not 0<=data['delete']<=10000 or not isinstance(data.get('text'),str) or len(data['text'])>10000: raise ValueError('Invalid live input')
    elif kind=='launch':
        if data.get('app') not in ('chrome','edge','firefox','explorer','calculator'): raise ValueError('Unsupported application')
    elif kind=='window':
        if data.get('action') not in ('minimize','maximize','restore','close') or type(data.get('handle')) is not int or data['handle']<1: raise ValueError('Invalid window action')
    elif kind=='tab':
        if data.get('action') not in ('activate','close','new','reload','duplicate','next','previous'): raise ValueError('Invalid tab action')
        if data['action'] in ('activate','close','reload','duplicate') and (type(data.get('tabId')) is not int or data['tabId']<1): raise ValueError('Invalid tab id')
        if data.get('url'): validate_url(data['url'])
    elif kind=='url': validate_url(data.get('url'))
    elif kind=='profile':
        if data.get('profile') not in PROFILES or data.get('action') not in PROFILES[data['profile']]: raise ValueError('Unsupported profile action')
    elif kind=='focus':
        if type(data.get('id')) is not int or data['id']<1: raise ValueError('Invalid window')
    elif kind=='power':
        if data.get('action') not in ('lock','shutdown','restart','cancel'): raise ValueError('Invalid power action')
        if data.get('confirm') is not True: raise ValueError('Confirmation required')
    elif kind=='delay':
        if type(data.get('ms')) is not int or not 0<=data['ms']<=1000: raise ValueError('Delay 0–1000 ms')
    elif kind not in ('clipboard_get','windows','screen','ping','release','tabs'): raise ValueError('Unknown action')
    return data

class Remote:
    def __init__(self, adapter, state_dir):
        self.adapter=adapter; self.state=Path(state_dir); self.state.mkdir(parents=True,exist_ok=True)
        self.tokens={}; self.sockets=set(); self.lock=asyncio.Lock()
        self.controller=None
        self.browser=None; self.browser_tabs=[]; self.browser_pending={}
        self.updater=Updater(self.state)
    def token(self):
        token=secrets.token_urlsafe(32); self.tokens[token]=time.monotonic()+24*3600; return token
    def authorized(self, token): return self.tokens.get(token,0)>time.monotonic()
    def load_shortcuts(self):
        path=self.state/'shortcuts.json'
        if path.exists(): return json.loads(path.read_text(encoding='utf-8'))
        return [{'name':'YouTube','actions':[{'type':'url','url':'https://www.youtube.com'}]}, {'name':'Netflix','actions':[{'type':'url','url':'https://www.netflix.com'}]}]
    def save_shortcuts(self, items):
        if not isinstance(items,list) or len(items)>60: raise ValueError('At most 60 shortcuts')
        for item in items:
            if not isinstance(item,dict) or not isinstance(item.get('name'),str) or not 1<=len(item['name'])<=60: raise ValueError('Invalid shortcut name')
            if 'icon' in item and (not isinstance(item['icon'],str) or len(item['icon'])>12): raise ValueError('Invalid icon')
            actions=item.get('actions')
            if not isinstance(actions,list) or not 1<=len(actions)<=20: raise ValueError('1–20 actions per macro')
            for action in actions:
                validate_action(action)
                if action['type'] not in ('url','keys','text','delay','profile','launch'): raise ValueError('Unsupported macro action')
        path=self.state/'shortcuts.json'; temp=path.with_suffix('.tmp')
        temp.write_text(json.dumps(items,ensure_ascii=False),encoding='utf-8'); temp.replace(path)
    async def execute(self, action):
        d=validate_action(action); a=self.adapter; kind=d['type']
        if kind=='move': a.move(d['x'],d['y'])
        elif kind=='scroll': a.scroll(d['amount'])
        elif kind=='button': a.button(d['button'],d['down'])
        elif kind=='keys': a.keys(d['keys'])
        elif kind=='text': a.text(d['text'])
        elif kind=='edit':
            for _ in range(d['delete']): a.keys(['BACKSPACE'])
            if d['text']: a.text(d['text'])
        elif kind=='launch': a.launch(d['app'])
        elif kind=='window': a.window(d['handle'],d['action'])
        elif kind=='tabs': return {'tabs':self.browser_tabs,'connected':self.browser is not None}
        elif kind=='tab':
            if self.browser is None: raise ValueError('Sekme listesi için tarayıcı eklentisini bağlayın')
            ident=secrets.token_hex(8);future=asyncio.get_running_loop().create_future();self.browser_pending[ident]=future
            try:
                await self.browser.send_json({**d,'requestId':ident})
                result=await asyncio.wait_for(future,5)
                if result.get('error'): raise ValueError(result['error'])
            finally: self.browser_pending.pop(ident,None)
        elif kind=='url': a.open_url(d['url'])
        elif kind=='profile': a.keys(PROFILES[d['profile']][d['action']])
        elif kind=='clipboard_get': return {'text':a.clipboard()[:10000]}
        elif kind=='clipboard_set': a.clipboard(d['text'])
        elif kind=='windows': return {'windows':a.windows()}
        elif kind=='focus': a.focus(d['id'])
        elif kind=='power': a.power(d['action'])
        elif kind=='release': a.release()
        elif kind=='delay': await asyncio.sleep(d['ms']/1000)
        elif kind=='screen':
            if isinstance(a,DryRun): raise ValueError('Screen preview requires Windows')
            from PIL import ImageGrab
            import base64
            def capture():
                im=ImageGrab.grab(); im.thumbnail((960,540)); out=io.BytesIO(); im.save(out,format='JPEG',quality=60)
                return base64.b64encode(out.getvalue()).decode()
            return {'image':await asyncio.to_thread(capture)}
        return {}

@web.middleware
async def security(request, handler):
    if not local_address(request.remote): raise web.HTTPForbidden(text='Local network only')
    host=request.host.rsplit(':',1)[0] if ':' in request.host and not request.host.startswith('[') else request.host.strip('[]')
    if not local_address(host) and host not in ('localhost',socket.gethostname(),socket.gethostname()+'.local'):
        raise web.HTTPForbidden(text='Local host address required')
    origin=request.headers.get('Origin')
    extension=request.path=='/api/browser' and origin and urlsplit(origin).scheme in ('chrome-extension','moz-extension')
    if origin and origin != f'{request.scheme}://{request.host}' and not extension:
        raise web.HTTPForbidden(text='Origin rejected')
    if request.path.startswith('/api/') and request.path not in ('/api/info','/api/connect','/api/browser'):
        if not request.app['remote'].authorized(request.cookies.get('sofa_session','')): raise web.HTTPUnauthorized(text='Connect first')
    response=await handler(request)
    response.headers['X-Content-Type-Options']='nosniff'
    response.headers['Referrer-Policy']='no-referrer'
    response.headers['Cache-Control']='no-store'
    response.headers['Content-Security-Policy']="default-src 'self'; img-src 'self' data: https:; style-src 'self'; script-src 'self'; connect-src 'self'; object-src 'none'; frame-ancestors 'none'"
    return response

async def info(request):
    return web.json_response({'service':'sofa-remote','protocol':1,'name':socket.gethostname(),'version':VERSION,'passwordRequired':False})

async def connect_device(request):
    response=web.json_response({'ok':True})
    response.set_cookie('sofa_session',request.app['remote'].token(),httponly=True,samesite='Strict',secure=request.secure,max_age=86400)
    return response

async def browser_handler(request):
    r=request.app['remote'];ws=web.WebSocketResponse(heartbeat=20,max_msg_size=262144)
    await ws.prepare(request)
    if r.browser is not None: await r.browser.close()
    r.browser=ws
    try:
        async for msg in ws:
            if msg.type!=WSMsgType.TEXT:continue
            try:
                data=json.loads(msg.data)
                if data.get('type')=='tabs' and isinstance(data.get('tabs'),list):
                    tabs=[]
                    for tab in data['tabs'][:200]:
                        if type(tab.get('id')) is int and type(tab.get('windowId')) is int:
                            tabs.append({'id':tab['id'],'windowId':tab['windowId'],'title':str(tab.get('title',''))[:200], 'url':str(tab.get('url',''))[:2048],'active':bool(tab.get('active'))})
                    r.browser_tabs=tabs
                elif data.get('requestId') in r.browser_pending:
                    future=r.browser_pending[data['requestId']]
                    if not future.done(): future.set_result(data)
            except (ValueError,TypeError,AttributeError): continue
    finally:
        if r.browser is ws:
            r.browser=None;r.browser_tabs=[]
            for future in r.browser_pending.values():
                if not future.done(): future.set_result({'error':'Tarayıcı bağlantısı kesildi'})
    return ws

async def updates(request):
    return web.json_response(request.app['remote'].updater.status)

async def check_updates(request):
    r=request.app['remote']
    if not r.updater.busy.locked():
        task=asyncio.create_task(r.updater.check()); request.app['tasks'].add(task);task.add_done_callback(request.app['tasks'].discard)
    return web.json_response({'ok':True})

async def install_update(request):
    r=request.app['remote']
    try: r.updater.install()
    except ValueError as exc: raise web.HTTPBadRequest(text=str(exc))
    asyncio.get_running_loop().call_later(1,lambda:os._exit(0))
    return web.json_response({'ok':True})

async def shortcuts(request):
    r=request.app['remote']
    if request.method=='PUT':
        try: r.save_shortcuts(await request.json())
        except (ValueError,TypeError,KeyError): raise web.HTTPBadRequest(text='Invalid shortcut configuration')
    return web.json_response(r.load_shortcuts())

async def ws_handler(request):
    r=request.app['remote']; ws=web.WebSocketResponse(heartbeat=15,max_msg_size=65536)
    # One active controller prevents interleaved dragging/macros from different phones.
    if r.controller is not None: raise web.HTTPConflict(text='Başka telefon bağlı; önce bağlantısını kesin')
    r.controller=ws
    try:
        await ws.prepare(request); r.sockets.add(ws)
        await ws.send_json({'type':'hello','dryRun':isinstance(r.adapter,DryRun)})
        history=deque()
        async for msg in ws:
            if msg.type!=WSMsgType.TEXT: continue
            now=time.monotonic()
            while history and history[0]<now-1: history.popleft()
            if len(history)>=180:
                await ws.close(code=1008,message=b'Rate limit'); break
            history.append(now)
            if not r.authorized(request.cookies.get('sofa_session','')):
                await ws.close(code=1008,message=b'Session expired'); break
            request_id=None
            try:
                data=json.loads(msg.data)
                if not isinstance(data,dict): raise ValueError('Object required')
                request_id=data.get('id')
                async with r.lock:
                    if data.get('type')=='macro':
                        index=data.get('index'); items=r.load_shortcuts()
                        if type(index) is not int or not 0<=index<len(items): raise ValueError('Invalid shortcut')
                        for action in items[index]['actions']: await r.execute(action)
                        result={}
                    else: result=await r.execute(data)
                if data.get('type')!='move': await ws.send_json({'type':'result','id':request_id,**result})
            except Exception as exc:
                await ws.send_json({'type':'error','id':request_id,'message':str(exc)[:180]})
    finally:
        r.adapter.release(); r.sockets.discard(ws)
        if r.controller is ws: r.controller=None
    return ws

def create_app(adapter=None,state_dir=None):
    app=web.Application(middlewares=[security],client_max_size=65536)
    app['remote']=Remote(adapter if adapter is not None else Windows(),state_dir or STATE)
    app['tasks']=set()
    app.router.add_get('/api/info',info)
    app.router.add_post('/api/connect',connect_device)
    app.router.add_get('/api/browser',browser_handler)
    app.router.add_get('/api/updates',updates)
    app.router.add_post('/api/updates/check',check_updates)
    app.router.add_post('/api/updates/install',install_update)
    app.router.add_route('*','/api/shortcuts',shortcuts)
    app.router.add_get('/api/ws',ws_handler)
    async def index(_): return web.FileResponse(ROOT/'web/index.html')
    app.router.add_get('/',index)
    app.router.add_static('/assets/',ROOT/'web')
    return app

def main():
    p=argparse.ArgumentParser(); p.add_argument('--host',default='0.0.0.0'); p.add_argument('--port',type=int,default=8765)
    p.add_argument('--state-dir'); p.add_argument('--dry-run',action='store_true'); p.add_argument('--tls-cert'); p.add_argument('--tls-key')
    args=p.parse_args(); app=create_app(DryRun() if args.dry_run else None,state_dir=args.state_dir)
    import ssl
    context=None
    if args.tls_cert:
        context=ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER); context.load_cert_chain(args.tls_cert,args.tls_key)
    try:
        with socket.socket(socket.AF_INET,socket.SOCK_DGRAM) as sock:
            sock.connect(('192.0.2.1',80)); ip=sock.getsockname()[0]
    except OSError: ip='BILGISAYAR-IP'
    url=f'{"https" if context else "http"}://{ip}:{args.port}'
    print(f'\nSofa Remote\nTelefon adresi: {url}\nAynı yerel ağdaki telefonlar şifresiz bağlanabilir.\n')
    try:
        import qrcode
        qr=qrcode.QRCode(); qr.add_data(url); qr.print_ascii(invert=True)
    except ImportError: pass
    async def lifecycle(app):
        discovery=None
        try:
            if not context: discovery=await start_discovery(args.port)
        except OSError: print('Ağ keşfi başlatılamadı; telefon adresle bağlanabilir.')
        task=asyncio.create_task(app['remote'].updater.background()) if not args.dry_run else None
        yield
        if task:
            task.cancel()
            await asyncio.gather(task,return_exceptions=True)
        for pending in list(app['tasks']): pending.cancel()
        await asyncio.gather(*app['tasks'],return_exceptions=True)
        if discovery: discovery.close()
        app['remote'].adapter.release()
    app.cleanup_ctx.append(lifecycle)
    web.run_app(app,host=args.host,port=args.port,ssl_context=context,access_log=None)

if __name__=='__main__': main()
