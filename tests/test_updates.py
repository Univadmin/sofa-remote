import hashlib
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from server.updater import Updater

class Response:
    def __init__(self,data=None,body=b''):
        self.data=data;self.body=body;self.status=200;self.content=self
    async def __aenter__(self):return self
    async def __aexit__(self,*args):pass
    def raise_for_status(self):pass
    async def json(self):return self.data
    async def iter_chunked(self,size):yield self.body
class Session:
    def __init__(self,release,body):self.responses=iter([Response(release),Response(body=body)])
    async def __aenter__(self):return self
    async def __aexit__(self,*args):pass
    def get(self,url):return next(self.responses)

class UpdateIntegrityTests(unittest.IsolatedAsyncioTestCase):
    async def check(self,body,expected):
        tmp=tempfile.TemporaryDirectory();self.addCleanup(tmp.cleanup)
        updater=Updater(tmp.name)
        release={'tag_name':'v0.4.0','assets':[{'name':'SofaRemote.exe','browser_download_url':'https://github.com/Univadmin/sofa-remote/releases/download/v0.4.0/SofaRemote.exe','size':len(expected),'digest':'sha256:'+hashlib.sha256(expected).hexdigest()}]}
        with patch('server.updater.ClientSession',return_value=Session(release,body)),patch('server.updater.os',SimpleNamespace(name='nt')),patch('server.updater.sys',SimpleNamespace(frozen=True)):
            await updater.check()
        return updater
    async def test_verified_download_staged(self):
        updater=await self.check(b'complete-package',b'complete-package')
        self.assertTrue(updater.status['ready']);self.assertEqual((updater.state/'SofaRemote-0.4.0.exe').read_bytes(),b'complete-package')
    async def test_corrupt_download_never_ready(self):
        updater=await self.check(b'changed-package!',b'complete-package')
        self.assertFalse(updater.status['ready']);self.assertEqual(updater.status['state'],'error')
        self.assertFalse(list(updater.state.glob('*.exe')));self.assertFalse(list(updater.state.glob('*.part')))
