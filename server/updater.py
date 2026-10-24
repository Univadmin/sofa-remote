"""GitHub release downloads with SHA-256 validation and staged Windows replacement."""
import asyncio
import hashlib
import os
from pathlib import Path
import re
import subprocess
import sys
from urllib.parse import urlsplit
from aiohttp import ClientSession, ClientTimeout
from .version import VERSION, REPOSITORY

def version_tuple(version):
    if not re.fullmatch(r'v?\d+\.\d+\.\d+', version): raise ValueError('Unsupported release version')
    return tuple(map(int,version.lstrip('v').split('.')))

def trusted_download(url):
    p=urlsplit(url)
    return p.scheme=='https' and p.hostname=='github.com' and p.path.startswith('/'+REPOSITORY+'/releases/download/') and not p.username

class Updater:
    def __init__(self, state):
        self.state=Path(state)/'updates'; self.state.mkdir(parents=True,exist_ok=True)
        self.status={'current':VERSION,'latest':VERSION,'available':False,'ready':False,'assets':[], 'state':'idle'}
        self.busy=asyncio.Lock()
    async def check(self, download=True):
        if self.busy.locked(): return self.status
        async with self.busy:
            self.status['state']='checking'
            try:
                async with ClientSession(timeout=ClientTimeout(total=180),headers={'User-Agent':'SofaRemote/'+VERSION,'Accept':'application/vnd.github+json'}) as client:
                    async with client.get(f'https://api.github.com/repos/{REPOSITORY}/releases/latest') as response:
                        if response.status==404:
                            self.status['state']='current';return self.status
                        response.raise_for_status(); release=await response.json()
                    latest=release['tag_name'].lstrip('v'); newer=version_tuple(latest)>version_tuple(VERSION)
                    assets=[]
                    for a in release.get('assets',[]):
                        if a['name'] not in ('SofaRemote.exe','SofaRemote-Android.apk','SofaRemote-Browser.zip'):continue
                        url=a['browser_download_url']
                        if trusted_download(url): assets.append({'name':a['name'],'url':url,'size':a['size'],'digest':a.get('digest','')})
                    self.status.update(latest=latest,available=newer,ready=False,assets=assets,state='available' if newer else 'current')
                    if newer and download and getattr(sys,'frozen',False) and os.name=='nt':
                        asset=next((a for a in assets if a['name']=='SofaRemote.exe'),None)
                        if not asset: raise ValueError('Windows asset missing')
                        digest=asset.get('digest') or ''
                        if not re.fullmatch('sha256:[a-fA-F0-9]{64}',digest): raise ValueError('Release SHA-256 missing')
                        staged=self.state/f'SofaRemote-{latest}.exe'
                        if staged.exists() and hashlib.sha256(staged.read_bytes()).hexdigest()==digest[7:]:
                            self.status.update(ready=True,state='ready');return self.status
                        self.status['state']='downloading';tmp=staged.with_suffix('.part');h=hashlib.sha256();size=0
                        try:
                            async with client.get(asset['url']) as response:
                                response.raise_for_status()
                                with tmp.open('wb') as file:
                                    async for chunk in response.content.iter_chunked(131072):
                                        size+=len(chunk)
                                        if size>150_000_000: raise ValueError('Update too large')
                                        h.update(chunk);file.write(chunk)
                            if size!=asset['size'] or h.hexdigest()!=digest[7:]: raise ValueError('Update checksum mismatch')
                            tmp.replace(staged);self.status.update(ready=True,state='ready')
                        finally: tmp.unlink(missing_ok=True)
            except Exception as exc:
                self.status.update(state='error',error=str(exc)[:160])
            return self.status
    def install(self):
        if os.name!='nt' or not getattr(sys,'frozen',False) or not self.status['ready']: raise ValueError('No staged Windows update')
        target=Path(sys.executable); staged=self.state/f'SofaRemote-{self.status["latest"]}.exe'
        # PowerShell receives paths as parameters, not interpolated executable code.
        script=self.state/'apply-update.ps1'
        script.write_text('''param([int]$ProcessId,[string]$Target,[string]$Staged)
Wait-Process -Id $ProcessId -ErrorAction SilentlyContinue
$Backup = $Target + '.previous'
try {
  Copy-Item -LiteralPath $Target -Destination $Backup -Force
  Copy-Item -LiteralPath $Staged -Destination $Target -Force
  Start-Process -FilePath $Target
} catch {
  if (Test-Path -LiteralPath $Backup) { Copy-Item -LiteralPath $Backup -Destination $Target -Force }
  Start-Process -FilePath $Target
}
''',encoding='utf-8')
        subprocess.Popen(['powershell.exe','-NoProfile','-ExecutionPolicy','Bypass','-File',str(script),str(os.getpid()),str(target),str(staged)],creationflags=0x08000000|0x00000008,close_fds=True)
    async def background(self):
        while True:
            await self.check();await asyncio.sleep(6*3600)
