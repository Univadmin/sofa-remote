"""Isolated dry-run server for Android touch/IME integration tests."""
from aiohttp import web
from server.app import create_app
from server.input import DryRun
import tempfile

state=tempfile.TemporaryDirectory();app=create_app(DryRun(),state.name);remote=app['remote']
remote.browser_tabs=[{'id':101,'windowId':1,'title':'Deneme sekmesi','url':'about:blank','active':True,'favicon':''}]
class Browser:
    closed=False
    async def send_json(self,data):
        if data.get('action')=='close':remote.browser_tabs=[]
        remote.browser_pending[data['requestId']].set_result({'ok':True})
        await remote.publish_tabs()
remote.browser=Browser()
async def focus(request):
    for ws in list(remote.sockets):await ws.send_json({'type':'keyboard-focus','active':True})
    return web.json_response({'ok':True})
app.router.add_post('/__focus',focus)
web.run_app(app,host='0.0.0.0',port=8765,access_log=None)
