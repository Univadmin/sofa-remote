import asyncio
import unittest
from unittest.mock import patch
from unittest.mock import AsyncMock
from types import SimpleNamespace
from server.playback import Playback,video_candidate,player_url

MOVIE={'id':'tm1','title':'Movie','original_title':'Movie','runtime':120}
class PlaybackTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.catalog=SimpleNamespace(get=lambda ident:MOVIE,details=AsyncMock(),fallback=AsyncMock(return_value={'offers':[]}),begin=lambda *args:None)
        self.remote=SimpleNamespace(movies=self.catalog,browser=object(),movie_capable=True)
        self.playback=Playback(self.remote)
    async def asyncTearDown(self):await self.playback.reset()
    async def test_unavailable_region_and_info_pages_never_become_results(self):
        self.catalog.details.return_value={'offers':[{'url':'https://www.imdb.com/title/tt1/','turkish_subtitles':True},{'url':'https://www.netflix.com/title/123','turkish_subtitles':True},{'url':'https://www.primevideo.com/detail/1','turkish_subtitles':True}]}
        async def command(kind,**data):
            if kind=='movie-search':return {'ok':True,'links':[]}
            if 'netflix' in data['url']:raise ValueError('Bu video ülkenizde kullanılamıyor')
            return {'ok':True,'duration':7200,'turkish_subtitles':True}
        self.playback.command=AsyncMock(side_effect=command)
        self.assertEqual(self.playback.sources('tm1')['offers'],[])
        await self.playback.workers['tm1']
        result=self.playback.sources('tm1');self.assertEqual(len(result['offers']),1)
        self.assertIn('primevideo',result['offers'][0]['url']);self.assertEqual(self.playback.command.await_count,3)
    async def test_trailer_and_unknown_subtitles_never_become_results(self):
        self.catalog.details.return_value={'offers':[{'url':'https://example.com/film','turkish_subtitles':True}]}
        self.playback.command=AsyncMock(return_value={'ok':True,'duration':120,'turkish_subtitles':True})
        self.playback.sources('tm1');await self.playback.workers['tm1'];self.assertEqual(self.playback.sources('tm1')['offers'],[])
    async def test_playback_failure_immediately_removes_previously_verified_source(self):
        self.catalog.details.return_value={'offers':[{'url':'https://example.com/film','turkish_subtitles':True}]}
        self.playback.command=AsyncMock(return_value={'ok':True,'duration':7200,'turkish_subtitles':True})
        self.playback.sources('tm1');await self.playback.workers['tm1'];self.assertEqual(len(self.playback.sources('tm1')['offers']),1)
        self.playback.command=AsyncMock(side_effect=ValueError('Video kullanılamıyor'))
        with self.assertRaises(ValueError):await self.playback.play('tm1')
        self.assertEqual(self.playback.sources('tm1')['offers'],[])
    def test_information_sites_are_rejected_and_netflix_goes_to_player(self):
        for url in ('https://imdb.com/title/a','https://www.filmara.com/film/a','https://www.justwatch.com/tr/film/a'):
            self.assertFalse(video_candidate(url))
        self.assertEqual(player_url('https://www.netflix.com/tr/title/123?source=test'),'https://www.netflix.com/watch/123')

    async def test_hung_source_search_finishes_at_global_deadline(self):
        async def hang(*args):await asyncio.sleep(10)
        self.catalog.details.side_effect=hang
        self.playback.command=AsyncMock(return_value={'ok':True,'links':[]})
        with patch('server.playback.SCAN_TIMEOUT',.03):
            self.playback.sources('tm1');await asyncio.wait_for(self.playback.workers['tm1'],.3)
        self.assertEqual(self.playback.sources('tm1')['state'],'ready')
    async def test_turkish_original_does_not_require_subtitles(self):
        movie={**MOVIE,'turkish_original':True};self.catalog.get=lambda ident:movie
        self.catalog.details.return_value={'movie':movie,'offers':[{'url':'https://example.com/movie'}]}
        self.playback.command=AsyncMock(return_value={'ok':True,'duration':7200,'turkish_subtitles':False})
        self.playback.sources('tm1');await self.playback.workers['tm1']
        self.assertEqual(len(self.playback.sources('tm1')['offers']),1)
    async def test_foreign_movie_still_requires_subtitles_even_with_turkish_dub(self):
        self.catalog.details.return_value={'offers':[{'url':'https://example.com/movie'}]}
        self.playback.command=AsyncMock(return_value={'ok':True,'duration':7200,'turkish_subtitles':False,'turkish_audio':True})
        self.playback.sources('tm1');await self.playback.workers['tm1']
        self.assertEqual(self.playback.sources('tm1')['offers'],[])
    async def test_catalog_failure_does_not_cancel_browser_discovery(self):
        self.catalog.details.side_effect=OSError('offline')
        async def command(kind,**data):
            if kind=='movie-search':return {'ok':True,'links':[{'url':'https://example.com/movie','title':'Movie'}]}
            return {'ok':True,'status':'ready','duration':7200,'turkish_subtitles':True,'evidence':'loaded_video'}
        self.playback.command=AsyncMock(side_effect=command)
        self.playback.sources('tm1');await self.playback.workers['tm1'];result=self.playback.sources('tm1')
        self.assertEqual(len(result['offers']),1);self.assertFalse(result['offers'][0]['verified']);self.assertTrue(result['diagnostics'])
        probes=[c for c in self.playback.command.call_args_list if c.args[0]=='movie-probe'];self.assertTrue(all(c.kwargs['passive'] for c in probes))
    async def test_unknown_is_retained_with_reason_not_labeled_playable(self):
        self.catalog.details.return_value={'offers':[{'url':'https://example.com/movie'}]}
        async def command(kind,**data):
            if kind=='movie-search':return {'ok':True,'links':[]}
            return {'ok':True,'status':'interaction_required','reason':'Oynatıcı etkileşim bekliyor'}
        self.playback.command=AsyncMock(side_effect=command)
        self.playback.sources('tm1');await self.playback.workers['tm1'];result=self.playback.sources('tm1')
        self.assertEqual(result['offers'],[]);self.assertEqual(result['candidates'][0]['status'],'interaction_required')
    async def test_browser_results_are_inspected_before_search_finishes(self):
        self.catalog.details.return_value={'offers':[]}
        release=asyncio.Event();inspected=asyncio.Event()
        async def command(kind,**data):
            if kind=='movie-search':
                data['on_results']([{'url':'https://example.com/movie','title':'Movie'}])
                await release.wait();return {'ok':True,'links':[]}
            inspected.set();return {'ok':True,'status':'ready','duration':7200,'turkish_subtitles':True}
        self.playback.command=AsyncMock(side_effect=command)
        self.playback.sources('tm1');await asyncio.wait_for(inspected.wait(),1)
        self.assertEqual(self.playback.sources('tm1')['state'],'checking')
        release.set();await self.playback.workers['tm1']
        self.assertEqual(len(self.playback.sources('tm1')['offers']),1)
