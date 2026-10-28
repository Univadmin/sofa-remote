"""Bounded, bilingual candidate discovery. Search snippets are never playback proof."""
import asyncio
import base64
import re
import xml.etree.ElementTree as ET
from urllib.parse import urlsplit,parse_qs,unquote,quote_plus
from .movies import normalized,public_url,SearchLinks

SEARCH_HOSTS=('google.com','google.com.tr','bing.com','duckduckgo.com','youtube.com')

def names(movie):
    result=[]
    for value in (movie.get('title'),movie.get('english_title'),movie.get('original_title')):
        if value and normalized(value) not in [normalized(n) for n in result]:result.append(value)
    return result

def queries(movie):
    suffix='full film izle' if movie.get('turkish_original') else 'Türkçe altyazılı full movie izle'
    return [f'"{name}" {movie.get("year") or ""} {suffix}'.strip() for name in names(movie)][:3]

def unwrap(url):
    try:
        p=urlsplit(url);q=parse_qs(p.query);host=p.hostname or ''
        if host in ('www.google.com','www.google.com.tr','google.com') and p.path=='/url':url=(q.get('q') or q.get('url') or [url])[0]
        elif host.endswith('bing.com') and p.path.startswith('/ck/'):
            encoded=q.get('u',[''])[0]
            if encoded.startswith('a1'):url=base64.urlsafe_b64decode(encoded[2:]+'='*((-len(encoded[2:]))%4)).decode()
        elif host.endswith('duckduckgo.com'):url=q.get('uddg',[url])[0]
        return public_url(url)
    except (ValueError,UnicodeError):return None

def candidate(movie,item):
    from .playback import video_candidate
    if not isinstance(item,dict):return None
    url=unwrap(item.get('url',''))
    if not url:return None
    host=urlsplit(url).hostname.lower()
    if any(host==h or host.endswith('.'+h) for h in SEARCH_HOSTS if h!='youtube.com'):return None
    if not video_candidate(url):return None
    # Title must appear as complete words, not merely in a site's unrelated navigation.
    text=unquote(str(item.get('title',''))+' '+url)
    flat=normalized(text)
    matched=any(normalized(n) in flat for n in names(movie))
    if not matched:return None
    year=str(movie.get('year') or '')
    # Do not accept a different sequel/year merely because its name contains this title.
    years=re.findall(r'(?<!\d)(?:19|20)\d{2}(?!\d)',text)
    if year and years and year not in years:return None
    title=str(item.get('title',''))[:300]
    if re.search(r'\b(trailer|fragman|review|inceleme)\b',title,re.I) and not re.search(r'full|tam film',title,re.I):return None
    return {'url':url,'provider':host,'kind':'UNKNOWN','cost':'Site koşulları bilinmiyor','unverified':True,
            'turkish_subtitles':False,'languages_known':False,'search_title':title,
            'score':(5 if year and year in text else 0)+(3 if re.search(r'izle|watch|full|film',text,re.I) else 0)}

def merge(movie,items,limit=18):
    found={}
    for item in items:
        row=candidate(movie,item)
        if row:
            key=row['url'].split('#')[0]
            if key not in found or row['score']>found[key]['score']:found[key]=row
    return sorted(found.values(),key=lambda r:-r['score'])[:limit]

async def web_candidates(movies,movie,client):
    errors=[];items=[]
    async def run(query,engine):
        url=('https://html.duckduckgo.com/html/?q=' if engine=='DuckDuckGo' else 'https://www.bing.com/search?format=rss&q=')+quote_plus(query)
        try:
            if engine=='DuckDuckGo':
                html,_=await movies.public_html(client,url);p=SearchLinks();p.feed(html)
                rows=[{'url':u,'title':''} for u in p.urls]
            else:
                async with client.get(url,allow_redirects=False) as response:
                    response.raise_for_status();raw=bytearray()
                    async for chunk in response.content.iter_chunked(32768):
                        raw.extend(chunk)
                        if len(raw)>500000:raise ValueError('Yanıt çok büyük')
                    tree=ET.fromstring(raw)
                    rows=[{'url':n.findtext('link',''),'title':n.findtext('title','')} for n in tree.findall('./channel/item')]
            accepted=merge(movie,rows)
            if not accepted:errors.append(f'{engine}: ilgili film sonucu alınamadı (arama engeli veya sonuç yok)')
            items.extend(rows)
        except Exception as e:errors.append(f'{engine}: {type(e).__name__} — arama kaynağı yanıt vermedi')
    await asyncio.gather(*(run(q,engine) for q in queries(movie) for engine in ('DuckDuckGo','Bing')))
    return {'offers':merge(movie,items),'diagnostics':list(dict.fromkeys(errors)),'queries':queries(movie)}
