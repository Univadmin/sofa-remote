"""Resolve site icons over the public internet; never request LAN or loopback hosts."""
import asyncio
import io
import ipaddress
import time
from html.parser import HTMLParser
from urllib.parse import urljoin, urlsplit
from aiohttp import ClientSession, ClientTimeout, TCPConnector
from aiohttp.resolver import DefaultResolver
from PIL import Image

class PublicResolver(DefaultResolver):
    async def resolve(self,host,port=0,family=0):
        results=await super().resolve(host,port,family)
        if not results or any(not ipaddress.ip_address(r['host']).is_global for r in results):
            raise OSError('Only public icon hosts are allowed')
        return results

class IconLinks(HTMLParser):
    def __init__(self):super().__init__();self.icons=[]
    def handle_starttag(self,tag,attrs):
        if tag.lower()!='link':return
        a=dict(attrs);rel=a.get('rel','').lower().split()
        if ('icon' in rel or 'apple-touch-icon' in rel) and a.get('href'):
            self.icons.append(a['href'])

class Icons:
    def __init__(self):self.cache={};self.semaphore=asyncio.Semaphore(4)
    @staticmethod
    def valid(url):
        p=urlsplit(url)
        if p.scheme not in ('https','http') or not p.hostname or p.username or p.password:raise ValueError('Invalid icon address')
        if p.port not in (None,80,443):raise ValueError('Invalid icon port')
        try:
            if not ipaddress.ip_address(p.hostname).is_global:raise ValueError('Public icons only')
        except ValueError:
            # A DNS hostname must be resolved by PublicResolver; literal private IPs are rejected here.
            if ':' in p.hostname or all(c in '0123456789.' for c in p.hostname):raise
        return url
    async def fetch(self,session,url,limit):
        for _ in range(4):
            self.valid(url)
            async with session.get(url,allow_redirects=False) as response:
                if response.status in (301,302,303,307,308):
                    url=urljoin(url,response.headers.get('Location',''));continue
                response.raise_for_status();data=bytearray()
                async for chunk in response.content.iter_chunked(32768):
                    data.extend(chunk)
                    if len(data)>limit:raise ValueError('Icon response too large')
                return bytes(data),str(response.url)
        raise ValueError('Too many icon redirects')
    async def get(self,page,preferred=''):
        key=(page,preferred);hit=self.cache.get(key)
        if hit and hit[0]>time.monotonic():return hit[1]
        async with self.semaphore:
            hit=self.cache.get(key)
            if hit and hit[0]>time.monotonic():return hit[1]
            self.valid(page);candidates=[]
            async with ClientSession(connector=TCPConnector(resolver=PublicResolver()),timeout=ClientTimeout(total=5,connect=2),headers={'User-Agent':'Mozilla/5.0 SofaRemote/0.3'}) as session:
                if preferred and preferred.startswith(('http://','https://')):candidates.append(preferred)
                try:
                    raw,final=await self.fetch(session,page,450000);parser=IconLinks();parser.feed(raw.decode('utf-8',errors='replace'))
                    candidates.extend(urljoin(final,url) for url in [url for url in parser.icons if not urlsplit(url).path.endswith('.svg')][:3])
                except Exception:pass
                candidates.append(urljoin(page,'/favicon.ico'));image=None
                for candidate in dict.fromkeys(candidates):
                    try:
                        raw,_=await self.fetch(session,candidate,500000)
                        with Image.open(io.BytesIO(raw)) as icon:
                            if icon.width>4096 or icon.height>4096:continue
                            icon.thumbnail((64,64));out=io.BytesIO();icon.convert('RGBA').save(out,format='PNG');image=out.getvalue();break
                    except Exception:continue
            if image is None:raise ValueError('Site icon unavailable')
            if len(self.cache)>=512:self.cache.pop(next(iter(self.cache)))
            self.cache[key]=(time.monotonic()+86400,image)
            return image
