import unittest
from server.movie_search import queries,merge

MOVIE={'title':'Demir Adam','original_title':'Iron Man','year':2008}
class DiscoveryTests(unittest.TestCase):
 def test_both_names_and_turkish_original_rule(self):
  q=queries(MOVIE);self.assertEqual(len(q),2);self.assertIn('Demir Adam',q[0]);self.assertIn('Iron Man',q[1]);self.assertTrue(all('2008' in s for s in q))
  self.assertNotIn('altyazılı',queries({**MOVIE,'turkish_original':True})[0])
 def test_distinct_english_title_is_searched(self):
  result=queries({'title':'Hayat Güzeldir','english_title':'Life Is Beautiful','original_title':'La vita è bella','year':1997})
  self.assertEqual(len(result),3);self.assertIn('Life Is Beautiful',result[1])
 def test_does_not_require_static_video_tag_and_filters_wrong_movie(self):
  rows=merge(MOVIE,[{'url':'https://example.com/iron-man-2008','title':'Iron Man izle'}, {'url':'https://example.com/iron-man-2-2010','title':'Iron Man 2'}, {'url':'https://imdb.com/title/tt1','title':'Iron Man 2008'}, {'url':'https://example.com/iron-man-trailer','title':'Iron Man trailer 2008'}, {'url':'https://example.com/bottoms','title':'Bottoms 2023'}, {'url':'https://127.0.0.1/iron-man','title':'Iron Man'}])
  self.assertEqual(len(rows),1);self.assertFalse(rows[0]['turkish_subtitles']);self.assertTrue(rows[0]['unverified'])
 def test_google_redirect_and_duplicate_are_normalized(self):
  rows=merge(MOVIE,[{'url':'https://www.google.com/url?q=https%3A%2F%2Fexample.com%2Firon-man-2008','title':'Iron Man 2008'}, {'url':'https://example.com/iron-man-2008','title':'Iron Man 2008'}])
  self.assertEqual(len(rows),1)
 def test_unrelated_rss_results_are_not_film_sources(self):
  self.assertEqual(merge(MOVIE,[{'url':'https://example.com/demir-fiyatlari','title':'Demir Fiyatları'}]),[])
