"""Sofa Remote: same-origin mobile UI and authenticated local WebSocket."""
import argparse
import asyncio
from collections import defaultdict, deque
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
    elif kind not in ('clipboard_get','windows','screen','ping','release'): raise ValueError('Unknown action')
    return data

class Remote:
    def __init__(self, adapter, state_dir, pin=None):
        self.adapter=adapter; self.state=Path(state_dir); self.state.mkdir(parents=True,exist_ok=True)
        self.pin=pin or f'{secrets.randbelow(1000000):06d}'
        self.tokens={}; self.attempts=defaultdict(deque); self.sockets=set(); self.lock=asyncio.Lock()
        self.controller=None
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
            actions=item.get('actions')
            if not isinstance(actions,list) or not 1<=len(actions)<=20: raise ValueError('1–20 actions per macro')
            for action in actions:
                validate_action(action)
                if action['type'] not in ('url','keys','text','delay','profile'): raise ValueError('Unsupported macro action')
        path=self.state/'shortcuts.json'; temp=path.with_suffix('.tmp')
        temp.write_text(json.dumps(items,ensure_ascii=False),encoding='utf-8'); temp.replace(path)
    async def execute(self, action):
        d=validate_action(action); a=self.adapter; kind=d['type']
        if kind=='move': a.move(d['x'],d['y'])
        elif kind=='scroll': a.scroll(d['amount'])
        elif kind=='button': a.button(d['button'],d['down'])
        elif kind=='keys': a.keys(d['keys'])
        elif kind=='text': a.text(d['text'])
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
    # Reject browser cross-origin writes and WebSocket handshakes. Native clients use no Origin.
    origin=request.headers.get('Origin')
    if origin and origin != f'{request.scheme}://{request.host}': raise web.HTTPForbidden(text='Origin rejected')
    if request.path.startswith('/api/') and request.path!='/api/pair':
        token=request.cookies.get('sofa_session','')
        if not request.app['remote'].authorized(token): raise web.HTTPUnauthorized(text='Pair this device first')
    response=await handler(request)
    response.headers['X-Content-Type-Options']='nosniff'
    response.headers['Referrer-Policy']='no-referrer'
    response.headers['Cache-Control']='no-store'
    response.headers['Content-Security-Policy']="default-src 'self'; img-src 'self' data:; style-src 'self'; script-src 'self'; connect-src 'self'; object-src 'none'; frame-ancestors 'none'"
    return response

async def pair(request):
    r=request.app['remote']; peer=request.remote; now=time.monotonic(); attempts=r.attempts[peer]
    while attempts and attempts[0]<now-60: attempts.popleft()
    if len(attempts)>=5: raise web.HTTPTooManyRequests(text='60 saniye bekleyin')
    attempts.append(now)
    try: data=await request.json()
    except (ValueError,TypeError): raise web.HTTPBadRequest()
    if not isinstance(data,dict) or not secrets.compare_digest(str(data.get('pin','')),r.pin): raise web.HTTPUnauthorized(text='Kod yanlış')
    attempts.clear(); response=web.json_response({'ok':True})
    response.set_cookie('sofa_session',r.token(),httponly=True,samesite='Strict',secure=request.secure,max_age=86400)
    return response

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

def create_app(adapter=None,state_dir=None,pin=None):
    app=web.Application(middlewares=[security],client_max_size=65536)
    app['remote']=Remote(adapter if adapter is not None else Windows(),state_dir or STATE,pin)
    app.router.add_post('/api/pair',pair)
    app.router.add_route('*','/api/shortcuts',shortcuts)
    app.router.add_get('/api/ws',ws_handler)
    async def index(_): return web.FileResponse(ROOT/'web/index.html')
    app.router.add_get('/',index)
    app.router.add_static('/assets/',ROOT/'web')
    return app

def main():
    p=argparse.ArgumentParser(); p.add_argument('--host',default='0.0.0.0'); p.add_argument('--port',type=int,default=8765)
    p.add_argument('--dry-run',action='store_true'); p.add_argument('--tls-cert'); p.add_argument('--tls-key')
    args=p.parse_args(); app=create_app(DryRun() if args.dry_run else None)
    import ssl
    context=None
    if args.tls_cert:
        context=ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER); context.load_cert_chain(args.tls_cert,args.tls_key)
    try:
        with socket.socket(socket.AF_INET,socket.SOCK_DGRAM) as sock:
            sock.connect(('192.0.2.1',80)); ip=sock.getsockname()[0]
    except OSError: ip='BILGISAYAR-IP'
    url=f'{"https" if context else "http"}://{ip}:{args.port}'
    print(f'\nSofa Remote\nTelefon adresi: {url}\nEşleştirme kodu: {app["remote"].pin}\nKod ve oturumlar sunucu yeniden başlatılınca yenilenir.\n')
    try:
        import qrcode
        qr=qrcode.QRCode(); qr.add_data(url); qr.print_ascii(invert=True)
    except ImportError: pass
    web.run_app(app,host=args.host,port=args.port,ssl_context=context,access_log=None)

if __name__=='__main__': main()
