import tempfile
import unittest
from unittest.mock import AsyncMock,patch
from server.movies import Movies,FilmPage,SearchLinks,public_url

NODE={'id':'tm119206','content':{'title':'Esaretin Bedeli','originalTitle':'The Shawshank Redemption','originalReleaseYear':1994,'fullPath':'/tr/film/esaretin-bedeli','runtime':142,'scoring':{'imdbScore':9.3,'imdbVotes':3000000}}}
def offer(url,subs,kind='FLATRATE',name='Netflix'):
    return {'standardWebURL':url,'subtitleLanguages':subs,'monetizationType':kind,'package':{'clearName':name,'technicalName':name.lower()}}
class MovieTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.movies=Movies(self.tmp.name)
    async def populate(self,offers=None):
        self.movies.query=AsyncMock(return_value={'popularTitles':{'edges':[{'node':NODE}],'pageInfo':{'endCursor':'one','hasNextPage':True}}})
        result=await self.movies.search('Esaret')
        self.movies.query=AsyncMock(return_value={'node':{**NODE,'offers':offers or []}})
        return result
    async def test_keyless_catalog_uses_actual_imdb_score_and_year(self):
        result=await self.populate();m=result['movies'][0]
        self.assertEqual((m['title'],m['year'],m['imdb']),("Esaretin Bedeli",1994,9.3));self.assertTrue(result['has_more'])
    async def test_turkish_subtitles_are_required_and_duplicate_quality_offers_collapse(self):
        await self.populate([offer('https://www.netflix.com/watch/1',['en']),offer('https://www.primevideo.com/detail/2',['tr']),offer('https://www.primevideo.com/detail/2',['tr'])])
        detail=await self.movies.details('tm119206');self.assertEqual(len(detail['offers']),2)
        self.assertIn('primevideo', (await self.movies.choose('tm119206'))['url'])
        with self.assertRaises(ValueError):await self.movies.choose('tm119206',0)
    async def test_missing_subtitles_never_silently_autoplay(self):
        await self.populate([offer('https://www.netflix.com/watch/1',[])])
        self.movies.fallback=AsyncMock(return_value={'offers':[]})
        with self.assertRaises(ValueError):await self.movies.choose('tm119206')
    async def test_open_is_watching_not_watched_and_history_survives_restart(self):
        await self.populate();self.movies.begin('tm119206',4,'https://www.netflix.com/watch/1')
        self.assertEqual(Movies(self.tmp.name).history()[0]['status'],'watching')
        self.movies.mark('tm119206','watched');self.assertEqual(Movies(self.tmp.name).history()[0]['status'],'watched')
        self.movies.mark('tm119206','unwatched');self.assertEqual(self.movies.history(),[])
    async def test_real_elapsed_playback_marks_watched_but_seeking_or_wrong_title_does_not(self):
        await self.populate();self.movies.begin('tm119206',4,'https://www.netflix.com/watch/1');self.movies.sessions[4]['movie']['runtime']=20
        def sample(position,title='Esaretin Bedeli'):
            self.movies.progress({'tabId':4,'url':'https://www.netflix.com/watch/1','title':title,'duration':1200,'position':position,'playing':True})
        with patch('server.movies.time.monotonic',return_value=self.movies.sessions[4]['last']+10):sample(1199,'Different movie')
        self.assertEqual(self.movies.history()[0]['status'],'watching')
        with patch('server.movies.time.monotonic',return_value=self.movies.sessions[4]['last']+10):sample(1199)
        self.assertEqual(self.movies.history()[0]['status'],'watching')
        self.movies.begin('tm119206',4,'https://www.netflix.com/watch/1');self.movies.sessions[4]['movie']['runtime']=20;start=self.movies.sessions[4]['last']
        for n in range(109):
            with patch('server.movies.time.monotonic',return_value=start+n*10):sample(n*10)
        self.assertEqual(self.movies.history()[0]['status'],'watched')
    async def test_offline_catalog_uses_saved_movies(self):
        await self.populate();self.movies.cache.clear();self.movies.query=AsyncMock(side_effect=OSError('offline'))
        result=await self.movies.search('Esaret');self.assertTrue(result['offline']);self.assertEqual(len(result['movies']),1)
    def test_public_urls_only_and_subtitle_claims_are_not_inferred_from_page_text(self):
        for url in ('http://example.com','https://127.0.0.1/movie','https://192.168.1.1','https://localhost/','https://host.local/','https://user:pass@example.com'):
            with self.assertRaises(ValueError):public_url(url)
        page=FilmPage();page.feed('<h1>Türkçe altyazılı izle</h1><video></video>');self.assertFalse(page.turkish)
        page.feed('<track kind="subtitles" srclang="tr" src="/movie.vtt">');self.assertTrue(page.turkish and page.player)
        parser=SearchLinks();parser.feed('<a class="result__a" href="//duckduckgo.com/l/?uddg=https%3A%2F%2Fexample.com%2Ffilm">Film</a>');self.assertEqual(parser.urls,['https://example.com/film'])

class MovieApiTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        from aiohttp import CookieJar
        from aiohttp.test_utils import TestClient,TestServer
        from server.app import create_app
        from server.input import DryRun
        self.tmp=tempfile.TemporaryDirectory();self.adapter=DryRun();self.app=create_app(self.adapter,self.tmp.name)
        self.client=TestClient(TestServer(self.app),cookie_jar=CookieJar(unsafe=True));await self.client.start_server()
        self.app['remote'].movies.query=AsyncMock(return_value={'popularTitles':{'edges':[{'node':NODE}],'pageInfo':{'endCursor':None,'hasNextPage':False}}})
    async def asyncTearDown(self):await self.client.close();self.tmp.cleanup()
    async def test_catalog_and_history_require_local_session_and_launch_never_marks_watched(self):
        self.assertEqual((await self.client.get('/api/movies')).status,401)
        await self.client.post('/api/connect');r=await self.client.get('/api/movies');self.assertEqual(r.status,200)
        self.app['remote'].movies.query=AsyncMock(return_value={'node':{**NODE,'offers':[offer('https://www.netflix.com/watch/1',['tr'])]}})
        r=await self.client.post('/api/movies',json={'action':'open','id':'tm119206'});self.assertEqual(r.status,200)
        self.assertEqual(self.adapter.events,[('url','https://www.netflix.com/watch/1')])
        history=await (await self.client.get('/api/movies?mode=history')).json();self.assertEqual(history['movies'][0]['status'],'watching')
        self.assertEqual((await self.client.post('/api/movies',json={'action':'mark','id':'tm119206','status':'watched'})).status,200)
        history=await (await self.client.get('/api/movies?mode=history')).json();self.assertEqual(history['movies'][0]['status'],'watched')
