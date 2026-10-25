import unittest
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
            if 'netflix' in data['url']:raise ValueError('Bu video ülkenizde kullanılamıyor')
            return {'ok':True,'duration':7200,'turkish_subtitles':True}
        self.playback.command=AsyncMock(side_effect=command)
        self.assertEqual(self.playback.sources('tm1')['offers'],[])
        await self.playback.workers['tm1']
        result=self.playback.sources('tm1');self.assertEqual(len(result['offers']),1)
        self.assertIn('primevideo',result['offers'][0]['url']);self.assertEqual(self.playback.command.await_count,2)
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
