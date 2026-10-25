import asyncio
import tempfile
import unittest
from aiohttp import CookieJar, WSServerHandshakeError
from aiohttp.test_utils import TestClient, TestServer
from server.app import create_app, validate_action, validate_url, Remote
from server.input import DryRun
from server.network import local_address
from server.updater import version_tuple, trusted_download

class ValidationTests(unittest.TestCase):
    def test_url_restrictions(self):
        for url in ['file:///secret','javascript:alert(1)','https://user:pass@example.com','cmd.exe',None]:
            with self.assertRaises(ValueError): validate_url(url)
    def test_bad_input(self):
        for action in [None,[],{'type':'shell'}, {'type':'move','x':float('nan'),'y':0}, {'type':'keys','keys':['FN']}, {'type':'power','action':'shutdown'}, {'type':'delay','ms':5000},{'type':'scroll','amount':True}, {'type':'edit','delete':-1,'text':'x'}, {'type':'edit','delete':True,'text':'x'}, {'type':'launch','app':'cmd'}, {'type':'tab','action':'activate','tabId':'1'}, {'type':'window','handle':1,'action':'destroy'}]:
            with self.assertRaises(ValueError): validate_action(action)
    def test_advanced_keys(self):
        for keys in [['WIN','D'],['CTRL','SHIFT','T'],['F12'],['PLAYPAUSE']]:
            self.assertEqual(validate_action({'type':'keys','keys':keys})['keys'],keys)
    def test_shortcuts_persist(self):
        with tempfile.TemporaryDirectory() as tmp:
            r=Remote(DryRun(),tmp);items=[{'name':'Türkçe','icon':'🎬','actions':[{'type':'launch','app':'chrome'}]}]
            r.save_shortcuts(items);self.assertEqual(Remote(DryRun(),tmp).load_shortcuts(),items)
            with self.assertRaises(ValueError): r.save_shortcuts([{'name':'bad','actions':[{'type':'power','action':'lock','confirm':True}]}])
            self.assertEqual(r.load_shortcuts(),items)
    def test_local_networks_only(self):
        for ip in ['127.0.0.1','192.168.1.9','10.3.0.1','172.31.1.1','::1','::ffff:192.168.1.4']:self.assertTrue(local_address(ip))
        for ip in ['8.8.8.8','172.32.1.1','example.com',None]:self.assertFalse(local_address(ip))
    def test_update_sources_and_versions(self):
        self.assertGreater(version_tuple('v0.10.0'),version_tuple('0.2.0'))
        with self.assertRaises(ValueError):version_tuple('0.2.0-beta')
        self.assertTrue(trusted_download('https://github.com/Univadmin/sofa-remote/releases/download/v0.2.0/SofaRemote.exe'))
        for url in ['https://evil.com/SofaRemote.exe','http://github.com/Univadmin/sofa-remote/releases/download/v1/x','https://github.com/other/repo/releases/download/v1/x']:
            self.assertFalse(trusted_download(url))

class IntegrationTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.adapter=DryRun();self.app=create_app(self.adapter,self.tmp.name)
        self.client=TestClient(TestServer(self.app),cookie_jar=CookieJar(unsafe=True));await self.client.start_server()
    async def asyncTearDown(self):
        await self.client.close();self.tmp.cleanup()
    async def connect(self):self.assertEqual((await self.client.post('/api/connect')).status,200)
    async def test_ui_info_and_passwordless_connection(self):
        self.assertEqual((await self.client.get('/')).status,200)
        response=await self.client.get('/api/info');info=await response.json()
        self.assertEqual(info['service'],'sofa-remote');self.assertFalse(info['passwordRequired'])
        self.assertEqual((await self.client.get('/api/shortcuts')).status,401)
        await self.connect();self.assertEqual((await self.client.get('/api/shortcuts')).status,200)
    async def test_origin_and_host_blocked(self):
        self.assertEqual((await self.client.post('/api/connect',headers={'Origin':'https://attacker.example'})).status,403)
        self.assertEqual((await self.client.get('/api/info',headers={'Host':'attacker.example'})).status,403)
        with self.assertRaises(WSServerHandshakeError):await self.client.ws_connect('/api/ws')
    async def test_cookie(self):
        response=await self.client.post('/api/connect');self.assertIn('HttpOnly',response.headers['Set-Cookie']);self.assertIn('SameSite=Strict',response.headers['Set-Cookie'])
    async def test_live_keyboard_and_commands(self):
        await self.connect();ws=await self.client.ws_connect('/api/ws');await ws.receive_json()
        actions=[{'type':'edit','delete':0,'text':'Türkçe 😀'},{'type':'edit','delete':1,'text':'🎬'}, {'type':'keys','keys':['ENTER']},{'type':'launch','app':'chrome'},{'type':'window','handle':1,'action':'minimize'}]
        for i,action in enumerate(actions):
            await ws.send_json({**action,'id':i});self.assertEqual((await ws.receive_json())['id'],i)
        self.assertEqual(self.adapter.events,[('text','Türkçe 😀'),('keys',['BACKSPACE']),('text','🎬'),('keys',['ENTER']),('launch','chrome'),('window',1,'minimize')]);await ws.close()
    async def test_error_recovery(self):
        await self.connect();ws=await self.client.ws_connect('/api/ws');await ws.receive_json()
        await ws.send_json({'type':'keys','keys':['BAD']});self.assertEqual((await ws.receive_json())['type'],'error')
        await ws.send_json({'type':'ping'});self.assertEqual((await ws.receive_json())['type'],'result');await ws.close()
    async def two_phones(self):
        await self.connect();a=await self.client.ws_connect('/api/ws');await a.receive_json()
        b=await self.client.ws_connect('/api/ws');await b.receive_json();return a,b
    async def command(self,ws,action):
        await ws.send_json(action);return await ws.receive_json()
    async def test_two_phones_can_control_at_the_same_time(self):
        a,b=await self.two_phones()
        self.assertEqual((await self.command(a,{'type':'keys','keys':['VOLUMEUP']}))['type'],'result')
        self.assertEqual((await self.command(b,{'type':'keys','keys':['MUTE']}))['type'],'result')
        self.assertEqual(self.adapter.events,[('keys',['VOLUMEUP']),('keys',['MUTE'])]);await a.close();await b.close()
    async def test_disconnect_does_not_release_another_phones_drag(self):
        a,b=await self.two_phones();await self.command(a,{'type':'button','button':'left','down':True})
        await b.close();await asyncio.sleep(0.01);self.assertEqual(self.adapter.events,[('button','left',True)])
        await a.close();await asyncio.sleep(0.01);self.assertEqual(self.adapter.events,[('button','left',True),('button','left',False)])
    async def test_release_only_applies_to_the_requesting_phone(self):
        a,b=await self.two_phones()
        await self.command(a,{'type':'button','button':'left','down':True});await self.command(b,{'type':'release'})
        self.assertEqual(self.adapter.events,[('button','left',True)])
        await self.command(a,{'type':'release'});self.assertEqual(self.adapter.events,[('button','left',True),('button','left',False)])
        await a.close();await b.close()
    async def test_shared_button_is_released_after_last_owner(self):
        a,b=await self.two_phones()
        for ws in (a,b):await self.command(ws,{'type':'button','button':'left','down':True})
        await self.command(a,{'type':'button','button':'left','down':False});self.assertEqual(self.adapter.events,[('button','left',True)])
        await self.command(b,{'type':'button','button':'left','down':False});self.assertEqual(self.adapter.events,[('button','left',True),('button','left',False)])
        await a.close();await b.close()
    async def test_both_phones_receive_tab_changes(self):
        a,b=await self.two_phones();extension=await self.client.ws_connect('/api/browser',headers={'Origin':'chrome-extension://abcdefghijklmnop'})
        await extension.send_json({'type':'tabs','tabs':[{'id':1,'windowId':1,'title':'Site','url':'https://example.com'}]})
        for ws in (a,b):self.assertEqual((await ws.receive_json())['type'],'tabs')
        await extension.close();await a.close();await b.close()
    async def test_macro_clipboard(self):
        await self.connect();items=[{'name':'Film','actions':[{'type':'url','url':'https://example.com'},{'type':'delay','ms':0},{'type':'keys','keys':['F11']}]}]
        self.assertEqual((await self.client.put('/api/shortcuts',json=items)).status,200)
        ws=await self.client.ws_connect('/api/ws');await ws.receive_json()
        await ws.send_json({'type':'macro','index':0});await ws.receive_json();self.assertEqual(self.adapter.events,[('url','https://example.com'),('keys',['F11'])])
        await ws.send_json({'type':'clipboard_set','text':'Örnek'});await ws.receive_json()
        await ws.send_json({'type':'clipboard_get'});self.assertEqual((await ws.receive_json())['text'],'Örnek');await ws.close()
    async def test_browser_extension_tab_roundtrip(self):
        extension=await self.client.ws_connect('/api/browser',headers={'Origin':'chrome-extension://abcdefghijklmnop'})
        await extension.send_json({'type':'tabs','tabs':[{'id':7,'windowId':1,'title':'YouTube','url':'https://youtube.com','active':True}]});await asyncio.sleep(0.01)
        await self.connect();ws=await self.client.ws_connect('/api/ws');await ws.receive_json()
        await ws.send_json({'type':'tabs'});data=await ws.receive_json();self.assertTrue(data['connected']);self.assertEqual(data['tabs'][0]['id'],7)
        await ws.send_json({'type':'tab','action':'activate','tabId':7,'id':22});command=await extension.receive_json();self.assertEqual(command['tabId'],7)
        await extension.send_json({'requestId':command['requestId'],'ok':True});self.assertEqual((await ws.receive_json())['id'],22)
        await extension.close();await ws.close()
    async def test_tab_icons_are_pushed_to_controller(self):
        await self.connect();ws=await self.client.ws_connect('/api/ws');await ws.receive_json()
        extension=await self.client.ws_connect('/api/browser',headers={'Origin':'chrome-extension://abcdefghijklmnop'})
        await extension.send_json({'type':'tabs','tabs':[{'id':9,'windowId':1,'title':'Site','url':'https://example.com','favicon':'https://example.com/custom.png'}]})
        result=await ws.receive_json();self.assertEqual(result['type'],'tabs');self.assertEqual(result['tabs'][0]['favicon'],'https://example.com/custom.png')
        response=await self.client.get('/api/icon',params={'url':'http://127.0.0.1/private'});self.assertEqual(response.status,404)
        await extension.close();await ws.close()
    async def test_downloads_status_no_network(self):
        await self.connect();d=await (await self.client.get('/api/updates')).json();self.assertEqual(d['current'],'0.3.3');self.assertFalse(d['ready'])
        self.assertEqual((await self.client.post('/api/updates/install')).status,400)
    async def test_browser_focus_broadcast_does_not_send_field_contents(self):
        await self.connect();phone=await self.client.ws_connect('/api/ws');await phone.receive_json()
        browser=await self.client.ws_connect('/api/browser',headers={'Origin':'chrome-extension://test'})
        await browser.send_json({'type':'keyboard-focus','active':True,'text':'never-forward-this'})
        event=await phone.receive_json(timeout=2)
        self.assertEqual(event,{'type':'keyboard-focus','active':True})
        await phone.close();await browser.close()
    async def test_expired_session(self):
        await self.connect();self.app['remote'].tokens.clear();self.assertEqual((await self.client.get('/api/shortcuts')).status,401)
    async def test_invalid_macro(self):
        await self.connect();before=await (await self.client.get('/api/shortcuts')).json()
        self.assertEqual((await self.client.put('/api/shortcuts',json=[{'name':'bad','actions':[{'type':'url','url':'file:///etc/passwd'}]}])).status,400)
        self.assertEqual(await (await self.client.get('/api/shortcuts')).json(),before)
if __name__=='__main__':unittest.main()
