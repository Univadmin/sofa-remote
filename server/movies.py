"""Keyless Turkish movie discovery, country-specific offers and local watch history."""
import asyncio
import json
import math
from pathlib import Path
import re
import sqlite3
import time
import unicodedata
from contextlib import contextmanager
from urllib.parse import quote_plus, urlsplit, parse_qs, urljoin
from html.parser import HTMLParser
from aiohttp import ClientSession, ClientTimeout, TCPConnector
from .icons import PublicResolver

FIELDS='id content(country:TR,language:tr){title originalTitle originalReleaseYear fullPath runtime scoring{imdbScore imdbVotes} externalIds{imdbId}}'
SEARCH='query($q:String!,$after:String){popularTitles(country:TR,first:24,after:$after,sortBy:POPULAR,filter:{searchQuery:$q,objectTypes:[MOVIE]}){pageInfo{endCursor hasNextPage} edges{node{'+FIELDS+'}}}}'
DETAIL='query($id:ID!){node(id:$id){... on Movie{'+FIELDS+' offers(country:TR,platform:WEB){standardWebURL monetizationType subtitleLanguages package{clearName technicalName}}}}}'
KINDS={'FREE':'Ücretsiz','ADS':'Reklamlı','FLATRATE':'Abonelik','RENT':'Kirala','BUY':'Satın al'}

class SearchLinks(HTMLParser):
    def __init__(self):super().__init__();self.urls=[]
    def handle_starttag(self,tag,attrs):
        a=dict(attrs)
        if tag=='a' and 'result__a' in a.get('class','').split():
            url=urljoin('https://html.duckduckgo.com',a.get('href',''))
            self.urls.append(parse_qs(urlsplit(url).query).get('uddg',[url])[0])

class FilmPage(HTMLParser):
    def __init__(self):super().__init__();self.text=[];self.turkish=False;self.player=False
    def handle_data(self,data):self.text.append(data)
    def handle_starttag(self,tag,attrs):
        a=dict(attrs)
        if tag in ('video','iframe'):self.player=True
        if tag=='track' and a.get('srclang','').lower().split('-')[0] in ('tr','tur') and a.get('kind','subtitles') in ('subtitles','captions') and a.get('src'):self.turkish=True
        if tag=='meta' and a.get('property')=='og:title':self.text.append(a.get('content',''))

def public_url(url):
    p=urlsplit(url)
    if p.scheme!='https' or not p.hostname or p.username or p.password or p.port not in (None,443):raise ValueError('HTTPS adresi gerekli')
    # Also resolves through PublicResolver whenever the server fetches a URL.
    import ipaddress
    try:
        if not ipaddress.ip_address(p.hostname).is_global:raise ValueError('Yerel adres açılamaz')
    except ValueError:
        if ':' in p.hostname or all(c in '0123456789.' for c in p.hostname):raise
    if p.hostname=='localhost' or p.hostname.endswith(('.local','.localhost')):raise ValueError('Yerel adres açılamaz')
    return url

def normalized(value):
    return ''.join(c for c in unicodedata.normalize('NFKD',value.casefold().replace('ı','i')) if c.isalnum())

def movie_row(node):
    c=node['content'];score=(c.get('scoring') or {}).get('imdbScore')
    return {'id':node['id'],'title':c['title'],'original_title':c.get('originalTitle') or c['title'],
        'year':c.get('originalReleaseYear'),'imdb':score,'imdb_votes':(c.get('scoring') or {}).get('imdbVotes'),
        'runtime':c.get('runtime'),'source':'https://www.justwatch.com'+c['fullPath']}

class Movies:
    def __init__(self,state):
        self.path=Path(state)/'movies.sqlite3'
        with self.db() as db:
            db.executescript('CREATE TABLE IF NOT EXISTS movies(id TEXT PRIMARY KEY,data TEXT NOT NULL); CREATE TABLE IF NOT EXISTS history(id TEXT PRIMARY KEY,status TEXT NOT NULL,updated REAL NOT NULL);')
        self.cache={};self.sessions={};self.lock=asyncio.Lock()
    @contextmanager
    def db(self):
        connection=sqlite3.connect(self.path)
        try:
            with connection:yield connection
        finally:connection.close()
    async def query(self,query,variables):
        async with ClientSession(connector=TCPConnector(resolver=PublicResolver()),timeout=ClientTimeout(total=9,connect=3),headers={'User-Agent':'SofaRemote movie discovery','Content-Type':'application/json'}) as client:
            async with client.post('https://apis.justwatch.com/graphql',json={'query':query,'variables':variables},allow_redirects=False) as response:
                if response.status!=200:raise ValueError('Film kaynağına şu an ulaşılamıyor')
                raw=bytearray()
                async for chunk in response.content.iter_chunked(32768):
                    raw.extend(chunk)
                    if len(raw)>2_000_000:raise ValueError('Film yanıtı çok büyük')
                result=json.loads(raw)
                if result.get('errors') or not result.get('data'):raise ValueError('Film kaynağı yanıtı değişti; daha sonra tekrar deneyin')
                return result['data']
    def store(self,movie):
        with self.db() as db:db.execute('INSERT OR REPLACE INTO movies VALUES(?,?)',(movie['id'],json.dumps(movie,ensure_ascii=False)))
    def get(self,ident):
        if not isinstance(ident,str) or not re.fullmatch(r'tm\d{1,12}',ident):raise ValueError('Geçersiz film')
        with self.db() as db:row=db.execute('SELECT data FROM movies WHERE id=?',(ident,)).fetchone()
        if not row:raise ValueError('Film listeden seçilmeli')
        return json.loads(row[0])
    def history(self):
        with self.db() as db:
            return [{**json.loads(data),'status':status,'updated':updated} for data,status,updated in db.execute('SELECT m.data,h.status,h.updated FROM history h JOIN movies m ON m.id=h.id ORDER BY h.updated DESC LIMIT 500')]
    def annotate(self,movies):
        statuses={m['id']:m['status'] for m in self.history()}
        return [{**m,'status':statuses.get(m['id'],'unwatched')} for m in movies]
    def mark(self,ident,status):
        self.get(ident)
        if status not in ('unwatched','watching','watched'):raise ValueError('Geçersiz izleme durumu')
        with self.db() as db:
            if status=='unwatched':db.execute('DELETE FROM history WHERE id=?',(ident,))
            else:db.execute('INSERT OR REPLACE INTO history VALUES(?,?,?)',(ident,status,time.time()))
    async def search(self,query='',cursor=None):
        if not isinstance(query,str) or len(query)>150 or cursor is not None and (not isinstance(cursor,str) or len(cursor)>200):raise ValueError('Geçersiz arama')
        key=('list',query,cursor);cached=self.cache.get(key)
        if cached and cached[0]>time.time():return {**cached[1],'movies':self.annotate(cached[1]['movies'])}
        try:
            data=(await self.query(SEARCH,{'q':query.strip(),'after':cursor}))['popularTitles']
            rows=[movie_row(edge['node']) for edge in data['edges']]
            for movie in rows:self.store(movie)
            result={'movies':rows,'cursor':data['pageInfo']['endCursor'],'has_more':data['pageInfo']['hasNextPage'],'offline':False}
            if len(self.cache)>128:self.cache.pop(next(iter(self.cache)))
            self.cache[key]=(time.time()+1800,result)
            return {**result,'movies':self.annotate(rows)}
        except Exception:
            with self.db() as db:rows=[json.loads(r[0]) for r in db.execute('SELECT data FROM movies LIMIT 2000')]
            rows=[m for m in rows if normalized(query) in normalized(m['title']+' '+m['original_title'])][:24]
            if not rows:raise ValueError('Film kaynağına ulaşılamadı. İnternet bağlantısını kontrol edin.')
            return {'movies':self.annotate(rows),'cursor':None,'has_more':False,'offline':True}
    async def details(self,ident):
        self.get(ident);key=('detail',ident);cached=self.cache.get(key)
        if cached and cached[0]>time.time():return cached[1]
        node=(await self.query(DETAIL,{'id':ident})).get('node')
        if not node:raise ValueError('Film bulunamadı')
        movie=movie_row(node);self.store(movie);offers=[];seen=set()
        for offer in node.get('offers') or []:
            url=offer.get('standardWebURL','');languages=offer.get('subtitleLanguages') or []
            try:public_url(url)
            except (ValueError,TypeError):continue
            tr=any(str(lang).lower().split('-')[0] in ('tr','tur') for lang in languages)
            kind=offer.get('monetizationType','');package=offer.get('package') or {};signature=(url,kind)
            if signature in seen:continue
            seen.add(signature)
            offers.append({'url':url,'provider':package.get('clearName','Yayın platformu'),'technical':package.get('technicalName',''),
                'kind':kind,'cost':KINDS.get(kind,kind),'turkish_subtitles':tr,'languages_known':bool(languages)})
        priority=lambda o:({'FREE':0,'ADS':1,'FLATRATE':2,'RENT':3,'BUY':4}.get(o['kind'],5),0 if any(p in o['technical'] for p in ('netflix','amazon','youtube','hbo','max')) else 1)
        offers.sort(key=priority)
        result={'movie':movie,'offers':offers,'checked':time.time(),'country':'TR'}
        self.cache[key]=(time.time()+900,result)
        return result
    def begin(self,ident,tab_id,url):
        movie=self.get(ident);public_url(url)
        if not any(m['id']==ident and m['status']=='watched' for m in self.history()):self.mark(ident,'watching')
        if type(tab_id) is int:
            self.sessions[tab_id]={'movie':movie,'host':urlsplit(url).hostname,'last':time.monotonic(),'seconds':0,'duration':0}
    def progress(self,message):
        tab_id=message.get('tabId');session=self.sessions.get(tab_id) if type(tab_id) is int else None
        if not session:return
        duration=message.get('duration');position=message.get('position');title=message.get('title','');url=message.get('url','')
        if not isinstance(title,str) or not isinstance(url,str):return
        if any(type(v) not in (int,float) or not math.isfinite(v) for v in (duration,position)):return
        if duration<1200 or not 0<=position<=duration:return # trailers never count
        host=urlsplit(url).hostname or '';allowed=session['host']
        if host!=allowed and not host.endswith('.'+allowed):return
        movie=session['movie'];names=(normalized(movie['title']),normalized(movie['original_title']))
        runtime=movie.get('runtime')
        if type(runtime) in (int,float) and runtime>0 and not runtime*60*.75<=duration<=runtime*60*1.3:return
        if not any(len(name)>=4 and name in normalized(title) for name in names):return
        now=time.monotonic();elapsed=min(20,max(0,now-session['last']));session['last']=now
        old=session.get('position')
        if old is not None and message.get('playing') is True and 0<position-old<=elapsed*2.2:
            session['seconds']+=min(position-old,elapsed*2)
        session['position']=position
        if session['seconds']>=duration*.9:
            self.mark(movie['id'],'watched');self.sessions.pop(tab_id,None)
    async def choose(self,ident,index=None):
        detail=await self.details(ident)
        if index is None:
            offer=next((o for o in detail['offers'] if o['turkish_subtitles']),None)
        else:
            if type(index) is not int or not 0<=index<len(detail['offers']):raise ValueError('Geçersiz yayın seçimi')
            offer=detail['offers'][index]
        if offer is None and index is None:
            fallback=await self.fallback(ident)
            offer=next((o for o in fallback['offers'] if o['turkish_subtitles']),None)
        if not offer or not offer['turkish_subtitles']:raise ValueError('Türkçe altyazısı doğrulanan kaynak bulunamadı; diğer siteleri inceleyebilirsiniz')
        return offer
    async def public_html(self,session,url):
        for _ in range(4):
            public_url(url)
            async with session.get(url,allow_redirects=False) as response:
                if response.status in (301,302,303,307,308):url=urljoin(url,response.headers.get('Location',''));continue
                response.raise_for_status()
                if 'text/html' not in response.headers.get('Content-Type','').lower():raise ValueError('HTML sayfası gerekli')
                raw=bytearray()
                async for chunk in response.content.iter_chunked(32768):
                    raw.extend(chunk)
                    if len(raw)>500000:raise ValueError('Sayfa çok büyük')
                return raw.decode(response.charset or 'utf-8',errors='replace'),url
        raise ValueError('Çok fazla yönlendirme')
    async def fallback(self,ident):
        movie=self.get(ident);key=('fallback',ident);cached=self.cache.get(key)
        if cached and cached[0]>time.time():return cached[1]
        query=f'{movie["title"]} {movie["year"] or ""} Türkçe altyazılı izle'
        async with ClientSession(connector=TCPConnector(resolver=PublicResolver()),timeout=ClientTimeout(total=5,connect=2),headers={'User-Agent':'Mozilla/5.0 SofaRemote movie discovery'}) as client:
            try:
                html,_=await self.public_html(client,'https://html.duckduckgo.com/html/?q='+quote_plus(query))
                parser=SearchLinks();parser.feed(html);urls=list(dict.fromkeys(parser.urls))[:5]
            except Exception:urls=[]
            async def inspect(url):
                try:
                    html,final=await self.public_html(client,url);page=FilmPage();page.feed(html)
                    title=normalized(' '.join(page.text));matched=any(len(n)>=4 and n in title for n in (normalized(movie['title']),normalized(movie['original_title'])))
                    if not matched:return None
                    return {'url':final,'provider':urlsplit(final).hostname,'cost':'Site koşulları bilinmiyor','kind':'UNKNOWN',
                        'turkish_subtitles':page.turkish and page.player,'unverified':True,'languages_known':page.turkish}
                except Exception:return None
            offers=[o for o in await asyncio.gather(*(inspect(url) for url in urls)) if o]
        result={'offers':offers,'search_url':self.web_search(ident)};self.cache[key]=(time.time()+600,result)
        return result
    def web_search(self,ident):
        movie=self.get(ident)
        return 'https://www.google.com/search?q='+quote_plus(f'{movie["title"]} {movie["year"] or ""} Türkçe altyazılı izle')
