import tempfile
import unittest
from aiohttp import CookieJar, WSServerHandshakeError
from aiohttp.test_utils import TestClient, TestServer
from server.app import create_app, validate_action, validate_url, Remote
from server.input import DryRun

class ValidationTests(unittest.TestCase):
    def test_url_restrictions(self):
        for url in ['file:///secret','javascript:alert(1)','https://user:pass@example.com','cmd.exe',None]:
            with self.assertRaises(ValueError): validate_url(url)
        self.assertEqual(validate_url('https://www.netflix.com'),'https://www.netflix.com')
    def test_bad_input(self):
        for action in [None,[],{'type':'shell'}, {'type':'move','x':float('nan'),'y':0}, {'type':'keys','keys':['FN']}, {'type':'power','action':'shutdown'}, {'type':'delay','ms':5000},{'type':'scroll','amount':True}, {'type':'text','text':'a'*10001}, {'type':'focus','id':True}]:
            with self.assertRaises(ValueError): validate_action(action)
    def test_advanced_keys(self):
        for keys in [['WIN','D'],['CTRL','SHIFT','T'],['F12'],['PLAYPAUSE']]:
            self.assertEqual(validate_action({'type':'keys','keys':keys})['keys'],keys)
    def test_shortcuts_persist(self):
        with tempfile.TemporaryDirectory() as tmp:
            r=Remote(DryRun(),tmp);items=[{'name':'Test','actions':[{'type':'keys','keys':['WIN','D']}]}]
            r.save_shortcuts(items);self.assertEqual(Remote(DryRun(),tmp).load_shortcuts(),items)
            with self.assertRaises(ValueError): r.save_shortcuts([{'name':'bad','actions':[{'type':'power','action':'lock','confirm':True}]}])
            self.assertEqual(r.load_shortcuts(),items)

class IntegrationTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.adapter=DryRun();self.app=create_app(self.adapter,self.tmp.name,'123456')
        self.client=TestClient(TestServer(self.app),cookie_jar=CookieJar(unsafe=True));await self.client.start_server()
    async def asyncTearDown(self):
        await self.client.close();self.tmp.cleanup()
    async def pair(self):
        self.assertEqual((await self.client.post('/api/pair',json={'pin':'123456'})).status,200)
    async def test_ui_and_auth(self):
        response=await self.client.get('/');self.assertEqual(response.status,200);self.assertIn('Koltuk senin',await response.text())
        self.assertIn("frame-ancestors 'none'",response.headers['Content-Security-Policy'])
        self.assertEqual((await self.client.get('/api/shortcuts')).status,401)
        with self.assertRaises(WSServerHandshakeError): await self.client.ws_connect('/api/ws')
    async def test_origin_blocked(self):
        self.assertEqual((await self.client.post('/api/pair',json={'pin':'123456'},headers={'Origin':'https://attacker.example'})).status,403)
    async def test_rate_limit(self):
        for _ in range(5): self.assertEqual((await self.client.post('/api/pair',json={'pin':'000000'})).status,401)
        self.assertEqual((await self.client.post('/api/pair',json={'pin':'123456'})).status,429)
    async def test_cookie(self):
        response=await self.client.post('/api/pair',json={'pin':'123456'})
        self.assertIn('HttpOnly',response.headers['Set-Cookie']);self.assertIn('SameSite=Strict',response.headers['Set-Cookie'])
    async def test_commands_and_recovery(self):
        await self.pair();ws=await self.client.ws_connect('/api/ws');await ws.receive_json()
        for i,action in enumerate([{'type':'keys','keys':['WIN','D']},{'type':'text','text':'Türkçe 😀'},{'type':'profile','profile':'youtube','action':'play'}]):
            await ws.send_json({**action,'id':i});self.assertEqual((await ws.receive_json())['id'],i)
        await ws.send_json({'type':'keys','keys':['BAD']});self.assertEqual((await ws.receive_json())['type'],'error')
        await ws.send_json({'type':'ping'});self.assertEqual((await ws.receive_json())['type'],'result')
        self.assertEqual(self.adapter.events,[('keys',['WIN','D']),('text','Türkçe 😀'),('keys',['K'])]);await ws.close()
    async def test_single_controller(self):
        await self.pair();ws=await self.client.ws_connect('/api/ws');await ws.receive_json()
        with self.assertRaises(WSServerHandshakeError) as cm: await self.client.ws_connect('/api/ws')
        self.assertEqual(cm.exception.status,409);await ws.close()
    async def test_macro_clipboard(self):
        await self.pair();items=[{'name':'Film','actions':[{'type':'url','url':'https://example.com'},{'type':'delay','ms':0},{'type':'keys','keys':['F11']}]}]
        self.assertEqual((await self.client.put('/api/shortcuts',json=items)).status,200)
        ws=await self.client.ws_connect('/api/ws');await ws.receive_json()
        await ws.send_json({'type':'macro','index':0});await ws.receive_json()
        self.assertEqual(self.adapter.events,[('url','https://example.com'),('keys',['F11'])])
        await ws.send_json({'type':'clipboard_set','text':'Örnek'});await ws.receive_json()
        await ws.send_json({'type':'clipboard_get'});self.assertEqual((await ws.receive_json())['text'],'Örnek');await ws.close()
    async def test_expired_session(self):
        await self.pair();self.app['remote'].tokens.clear();self.assertEqual((await self.client.get('/api/shortcuts')).status,401)
    async def test_invalid_macro(self):
        await self.pair();before=await (await self.client.get('/api/shortcuts')).json()
        self.assertEqual((await self.client.put('/api/shortcuts',json=[{'name':'bad','actions':[{'type':'url','url':'file:///etc/passwd'}]}])).status,400)
        self.assertEqual(await (await self.client.get('/api/shortcuts')).json(),before)
if __name__=='__main__': unittest.main()
