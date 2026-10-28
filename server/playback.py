"""Discover film sources and report readiness separately from proven playback."""
import asyncio
import secrets
import time
from urllib.parse import urlsplit,urlunsplit
import re
from .movies import public_url

SCAN_TIMEOUT=75

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
    def __init__(self,remote):self.remote=remote;self.jobs={};self.workers={};self.gestures=set();self.discoveries={}
    async def command(self,kind,**data):
        r=self.remote
        if r.browser is None or not r.movie_capable:raise ValueError('Oynatıcı kontrolü için PC tarayıcı eklentisini güncelleyin ve bağlayın')
        on_results=data.pop('on_results',None)
        ident=secrets.token_hex(12)
        if on_results:self.discoveries[ident]=on_results
        future=asyncio.get_running_loop().create_future();r.browser_pending[ident]=future
        if kind=='movie-play' or kind=='movie-probe' and not data.get('passive'):self.gestures.add(ident)
        try:
            await r.browser.send_json({'type':kind,'requestId':ident,**data})
            result=await asyncio.wait_for(future,38 if kind=='movie-search' else 26)
            if result.get('error'):raise ValueError(str(result['error'])[:180])
            if not result.get('ok'):raise ValueError('Oynatım doğrulanamadı')
            return result
        finally:
            self.gestures.discard(ident);self.discoveries.pop(ident,None);r.browser_pending.pop(ident,None)
            if not future.done() or future.cancelled():
                if r.browser is not None:
                    try:await r.browser.send_json({'type':'movie-cancel','requestId':ident})
                    except Exception:pass
    def sources(self,ident,force=False):
        movie=self.remote.movies.get(ident)
        if not self.remote.movie_capable or self.remote.browser is None:return {'movie':movie,'state':'extension_required','offers':[],'message':'İzlenebilirliği kontrol etmek için PC tarayıcı eklentisini güncelleyin. Platform hesabına PC tarayıcısında giriş yapılmış olmalı.'}
        job=self.jobs.get(ident)
        if force and hasattr(self.remote.movies,'cache'):
            for key in (('detail',ident),('fallback',ident)):self.remote.movies.cache.pop(key,None)
        if job and (job['state']=='checking' or not force and time.time()-job['checked']<600):return {**job,'offers':list(job['offers'])}
        job={'movie':movie,'state':'checking','offers':[],'candidates':[],'diagnostics':[],'queries':[],'checked':time.time(),'attempted':0,'discovered':0,'failures':[],'message':'Türkçe ve özgün/İngilizce adlarla kaynaklar aranıyor; TV’de otomatik tam ekran açılmaz.'};self.jobs[ident]=job
        task=asyncio.create_task(self.check(ident,job));self.workers[ident]=task
        return {**job,'offers':[]}
    async def check(self,ident,job):
        from .movie_search import queries,merge,names
        r=self.remote;seen=set();queue=asyncio.Queue();tasks=[]
        job['queries']=queries(job['movie'])
        def enqueue(offers):
            for offer in offers:
                try:
                    url=player_url(offer['url'])
                    if not video_candidate(url) or url in seen or len(seen)>=24:continue
                    seen.add(url);queue.put_nowait({**offer,'url':url});job['discovered']=len(seen)
                except (ValueError,TypeError):continue
        async def platforms():
            try:
                detail=await r.movies.details(ident);job['movie']=detail.get('movie',job['movie']);enqueue(detail['offers'][:8])
            except Exception:job['diagnostics'].append('Türkiye platform kataloğuna ulaşılamadı; diğer aramalar sürdürüldü.')
        async def web_search():
            try:
                result=await r.movies.fallback(ident);enqueue(result['offers']);job['diagnostics'].extend(result.get('diagnostics',[]))
            except Exception:job['diagnostics'].append('Web arama kaynağına ulaşılamadı.')
        async def browser_search():
            try:
                result=await self.command('movie-search',queries=job['queries'],names=names(job['movie']),on_results=lambda links:enqueue(merge(job['movie'],links)))
                enqueue(merge(job['movie'],result.get('links',[])));job['diagnostics'].extend(result.get('diagnostics',[]))
            except Exception:job['diagnostics'].append('Brave araması tamamlanamadı; arama motoru erişimi veya eklenti kontrol edilmeli.')
        async def inspect(offer):
            row={**offer,'source_id':secrets.token_urlsafe(12),'checked':time.time()}
            try:
                proof=await self.command('movie-probe',url=offer['url'],movie=job['movie'],passive=True,timeout=11000,turkish_subtitles=False)
                status=proof.get('status','verified');duration=proof.get('duration');runtime=job['movie'].get('runtime')
                row.update(status=status,reason=proof.get('reason',''),video_found=proof.get('video_found',False))
                if status in ('ready','verified'):
                    valid=type(duration) in (int,float) and duration>=1200 and (not runtime or runtime*45<=duration<=runtime*78)
                    subtitles=proof.get('turkish_subtitles') is True
                    if not valid:row.update(status='wrong_duration',reason='Tam film süresi seçilen filmle uyuşmuyor.')
                    elif not job['movie'].get('turkish_original') and not subtitles:row.update(status='subtitles_unknown',reason='Türkçe altyazı doğrulanamadı.')
                    else:
                        row.update(verified=status=='verified',turkish_subtitles=subtitles,duration=duration,evidence=proof.get('evidence','playback'))
                        job['offers'].append(row);return
                job['candidates'].append(row)
            except asyncio.CancelledError:
                row.update(status='unconfirmed',reason='Kontrol süresi doldu veya iptal edildi; izlenemez olduğu doğrulanmadı.')
                job['candidates'].append(row);raise
            except Exception as error:
                row.update(status='unconfirmed',reason=str(error) or 'Sayfa/oynatıcı kontrolü zaman aşımına uğradı.')
                job['candidates'].append(row)
            finally:
                job['attempted']+=1;job['message']=f"{job['discovered']} aday bulundu, {job['attempted']} kaynak incelendi."
        async def worker():
            while True:
                offer=await queue.get()
                try:await inspect(offer)
                finally:queue.task_done()
        try:
            async with asyncio.timeout(SCAN_TIMEOUT):
                tasks=[asyncio.create_task(worker()) for _ in range(3)]
                await asyncio.gather(platforms(),web_search(),browser_search())
                await queue.join()
            job['state']='ready'
        except TimeoutError:
            job['state']='ready';job['diagnostics'].append('75 saniyelik sınır doldu. İncelenemeyen adaylar izlenemez sayılmadı; yeniden kontrol edebilirsiniz.')
        except asyncio.CancelledError:raise
        except Exception as error:
            job['state']='error';job['diagnostics'].append('Arama tamamlanamadı: '+str(error)[:120])
        finally:
            for task in tasks:task.cancel()
            await asyncio.gather(*tasks,return_exceptions=True)
            while not queue.empty():
                offer=queue.get_nowait();queue.task_done()
                job['candidates'].append({**offer,'source_id':secrets.token_urlsafe(12),'status':'unconfirmed','reason':'Süre sınırı nedeniyle henüz incelenmedi.'})
            job['checked']=time.time()
            job['diagnostics']=list(dict.fromkeys(job['diagnostics']))
            if job['offers']:job['message']=f"{len(job['offers'])} kaynakta tam film videosu hazır. Sessiz arka plan kontrolü tamamlandı; yükleme kanıtı oynatım garantisi değildir."
            elif job['candidates']:job['message']='Film sayfaları bulundu; mevcut oturumda oynatılabilirlik/altyazı kesinleşmedi. Aşağıda her kaynağın nedeni var.'
            else:job['message']='Aramalarda doğrulanabilir film kaynağı elde edilemedi. Bu, filmin internette bulunmadığı anlamına gelmez; arama tanısını kontrol edin.'

    async def open_source(self,ident,source_id):
        job=self.jobs.get(ident)
        if not job or time.time()-job['checked']>600:raise ValueError('Önce kaynakları yeniden kontrol edin')
        row=next((o for o in job['offers']+job.get('candidates',[]) if o['source_id']==source_id),None)
        if not row:raise ValueError('Geçersiz film kaynağı')
        await self.remote.execute({'type':'tab','action':'new','url':row['url']})
        return {'ok':True,'playing':False}
    async def play(self,ident,source_id=None):
        job=self.jobs.get(ident)
        if not job or not job['offers'] or time.time()-job['checked']>600:raise ValueError('Önce izlenebilir kaynakları yeniden kontrol edin')
        offer=next((o for o in job['offers'] if source_id is None or o['source_id']==source_id),None)
        if not offer:raise ValueError('Kaynak artık izlenebilir listesinde değil; yeniden kontrol edin')
        try:
            proof=await self.command('movie-play',url=offer['url'],movie=job['movie'],turkish_subtitles=offer.get('turkish_subtitles',False))
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
        self.workers.clear();self.jobs.clear();self.gestures.clear();self.discoveries.clear()
