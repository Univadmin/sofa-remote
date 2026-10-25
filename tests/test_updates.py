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

class InstallHandshakeTests(unittest.IsolatedAsyncioTestCase):
    async def test_failed_helper_keeps_application_running(self):
        import sys
        tmp=tempfile.TemporaryDirectory();self.addCleanup(tmp.cleanup)
        updater=Updater(tmp.name);updater.status.update(ready=True,latest='0.4.0')
        (updater.state/'SofaRemote-0.4.0.exe').write_bytes(b'fixture')
        process=SimpleNamespace(poll=lambda:1,terminate=lambda:None)
        with patch('server.updater.os',SimpleNamespace(name='nt',getpid=lambda:123)),patch('server.updater.sys',SimpleNamespace(frozen=True,executable=sys.executable,argv=['SofaRemote.exe'])),patch('server.windows_runtime.powershell',return_value=process):
            with self.assertRaisesRegex(ValueError,'yardımcısı'):
                await updater.install()
        self.assertEqual(updater.status['state'],'ready')
        self.assertFalse((updater.state/'installing').exists())

@unittest.skipUnless(__import__('os').name=='nt','Windows PowerShell required')
class PowerShellSyntaxTests(unittest.TestCase):
    def test_runtime_scripts_parse_in_windows_powershell(self):
        import os
        import subprocess
        from server.windows_runtime import UPDATE_SCRIPT,WATCH_SCRIPT
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'script.ps1'
            command="$tokens=$null; $errors=$null; [System.Management.Automation.Language.Parser]::ParseFile($env:SOFA_PARSE_SCRIPT,[ref]$tokens,[ref]$errors) | Out-Null; if($errors){$errors | Out-String | Write-Output; exit 1}"
            for source in (UPDATE_SCRIPT,WATCH_SCRIPT):
                path.write_text(source,encoding='utf-8-sig')
                result=subprocess.run(['powershell.exe','-NoProfile','-Command',command],env=dict(os.environ,SOFA_PARSE_SCRIPT=str(path)),capture_output=True,text=True)
                self.assertEqual(result.returncode,0,result.stdout+result.stderr)
