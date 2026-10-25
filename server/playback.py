"""List only sources proven to play in the PC browser's current account/session."""
import asyncio
import secrets
import time
from urllib.parse import urlsplit,urlunsplit
import re
from .movies import public_url

INFO_HOSTS=('imdb.com','themoviedb.org','justwatch.com','rottentomatoes.com','metacritic.com','wikipedia.org','beyazperde.com','sinemalar.com','letterboxd.com')
def video_candidate(url):
    public_url(url);host=urlsplit(url).hostname.lower()
    if any(host==h or host.endswith('.'+h) for h in INFO_HOSTS) or re.search(r'(^|\.)filmara\.',host):return False
    return True

def player_url(url):
    p=urlsplit(url);host=p.hostname.lower()
    if host=='netflix.com' or host.endswith('.netflix.com'):
        match=re.fullmatch(r'/(?:[a-z]{2}/)?title/(\d+)/?',p.path)
        if match:return urlunsplit((p.scheme,p.netloc,'/watch/'+match[1],'',''))
    return url

class Playback:
    def __init__(self,remote):self.remote=remote;self.jobs={};self.workers={};self.gestures=set()
    async def command(self,kind,**data):
        r=self.remote
        if r.browser is None or not r.movie_capable:raise ValueError('Oynatıcı kontrolü için PC tarayıcı eklentisini güncelleyin ve bağlayın')
        ident=secrets.token_hex(12);future=asyncio.get_running_loop().create_future();r.browser_pending[ident]=future
        if kind=='movie-play':self.gestures.add(ident)
        try:
            await r.browser.send_json({'type':kind,'requestId':ident,**data})
            result=await asyncio.wait_for(future,26)
            if result.get('error'):raise ValueError(str(result['error'])[:180])
            if not result.get('ok'):raise ValueError('Oynatım doğrulanamadı')
            return result
        finally:
            self.gestures.discard(ident);r.browser_pending.pop(ident,None)
            if not future.done() or future.cancelled():
                if r.browser is not None:
                    try:await r.browser.send_json({'type':'movie-cancel','requestId':ident})
                    except Exception:pass
    def sources(self,ident,force=False):
        movie=self.remote.movies.get(ident)
        if not self.remote.movie_capable or self.remote.browser is None:return {'movie':movie,'state':'extension_required','offers':[],'message':'İzlenebilirliği kontrol etmek için PC tarayıcı eklentisini güncelleyin. Platform hesabına PC tarayıcısında giriş yapılmış olmalı.'}
        job=self.jobs.get(ident)
        if job and (job['state']=='checking' or not force and time.time()-job['checked']<600):return {**job,'offers':list(job['offers'])}
        job={'movie':movie,'state':'checking','offers':[],'checked':time.time(),'message':'Kaynaklar PC tarayıcısında sessizce deneniyor…'};self.jobs[ident]=job
        task=asyncio.create_task(self.check(ident,job));self.workers[ident]=task
        return {**job,'offers':[]}
    async def check(self,ident,job):
        r=self.remote;seen=set();semaphore=asyncio.Semaphore(2)
        async def inspect(offer):
            url=player_url(offer['url'])
            try:
                if not video_candidate(url) or url in seen:return
                seen.add(url)
                async with semaphore:
                    proof=await self.command('movie-probe',url=url,movie=job['movie'],turkish_subtitles=offer.get('turkish_subtitles',False))
                duration=proof.get('duration');runtime=job['movie'].get('runtime')
                if type(duration) not in (int,float) or duration<1200 or not proof.get('turkish_subtitles'):return
                if type(runtime) in (int,float) and runtime>0 and not runtime*45<=duration<=runtime*78:return
                job['offers'].append({**offer,'url':url,'source_id':secrets.token_urlsafe(12),'verified':True,'turkish_subtitles':True,'checked':time.time()})
            except (ValueError,TimeoutError,OSError):pass
        try:
            detail=await r.movies.details(ident)
            await asyncio.gather(*(inspect(offer) for offer in detail['offers'][:6]))
            if not job['offers']:
                fallback=await r.movies.fallback(ident)
                await asyncio.gather(*(inspect(offer) for offer in fallback['offers'][:5]))
            job['state']='ready';job['checked']=time.time();job['message']='Yalnızca PC tarayıcısında oynatımı doğrulanan kaynaklar gösteriliyor.' if job['offers'] else 'Mevcut PC oturumunda Türkçe altyazılı tam film oynatımı doğrulanamadı. Platforma giriş yapıp yeniden kontrol edebilirsiniz.'
        except asyncio.CancelledError:raise
        except Exception:
            job['state']='error';job['offers']=[];job['message']='Kaynak kontrolü tamamlanamadı. Yeniden kontrol edin.'
    async def play(self,ident,source_id=None):
        job=self.jobs.get(ident)
        if not job or not job['offers'] or time.time()-job['checked']>600:raise ValueError('Önce izlenebilir kaynakları yeniden kontrol edin')
        offer=next((o for o in job['offers'] if source_id is None or o['source_id']==source_id),None)
        if not offer:raise ValueError('Kaynak artık izlenebilir listesinde değil; yeniden kontrol edin')
        try:
            proof=await self.command('movie-play',url=offer['url'],movie=job['movie'],turkish_subtitles=True)
            if type(proof.get('tabId')) is not int or not proof.get('fullscreen'):raise ValueError('Tam ekran oynatım doğrulanamadı')
        except (ValueError,TimeoutError,OSError):
            job['offers']=[o for o in job['offers'] if o['source_id']!=offer['source_id']]
            raise ValueError('Bu kaynak oynatılamadı ve sonuçlardan kaldırıldı. Başka bir kaynak seçin.')
        self.remote.movies.begin(ident,proof['tabId'],offer['url'])
        return {'ok':True,'tracking':True,'playing':True,'fullscreen':True}
    async def reset(self):
        workers=list(self.workers.values())
        for task in workers:task.cancel()
        await asyncio.gather(*workers,return_exceptions=True)
        self.workers.clear();self.jobs.clear();self.gestures.clear()
