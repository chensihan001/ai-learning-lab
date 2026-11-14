# -*- coding: utf-8 -*-
import hashlib, json, re, time, urllib.parse, urllib.request, http.cookiejar, ssl

UA = ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
      '(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36')
TAB = [46,47,18,2,53,8,23,32,15,50,10,31,58,3,45,35,27,43,5,49,33,9,42,19,29,28,
       14,39,12,38,41,13,37,48,7,16,24,55,40,61,26,17,0,1,60,51,30,4,22,25,54,21,
       56,59,6,63,57,62,11,36,20,34,44,52]

cj = http.cookiejar.CookieJar()
opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
opener.addheaders = [
    ('User-Agent', UA),
    ('Referer', 'https://www.bilibili.com/'),
    ('Accept', 'application/json, text/plain, */*'),
    ('Accept-Language', 'zh-CN,zh;q=0.9'),
]

def get(url, tries=3):
    last = None
    for i in range(tries):
        try:
            with opener.open(url, timeout=20) as r:
                return json.loads(r.read().decode('utf-8'))
        except Exception as e:
            last = e
            time.sleep(1.5 + i)
    raise last

# prime cookies
try:
    opener.open('https://www.bilibili.com/', timeout=20).read()
except Exception as e:
    print('# warmup fail:', e)

nav = get('https://api.bilibili.com/x/web-interface/nav')
wbi = nav['data']['wbi_img']
img = wbi['img_url'].rsplit('/', 1)[1].split('.')[0]
sub = wbi['sub_url'].rsplit('/', 1)[1].split('.')[0]
raw = img + sub
mixin = ''.join(raw[i] for i in TAB)[:32]

def search(kw):
    wts = int(time.time())
    p = {'keyword': kw, 'page': '1', 'search_type': 'video', 'wts': str(wts)}
    q = '&'.join('%s=%s' % (k, urllib.parse.quote(str(p[k]), safe='')) for k in sorted(p))
    rid = hashlib.md5((q + mixin).encode()).hexdigest()
    url = 'https://api.bilibili.com/x/web-interface/wbi/search/type?' + q + '&w_rid=' + rid
    return get(url)

KWS = ['大模型 应用开发 实战', 'RAG 从零 实现', '手写 Agent 框架',
       'LLaMA-Factory 微调', 'LLM 面试 八股', 'Transformer 李沐 详解',
       '大模型 实习 面经']

def clean(t):
    t = re.sub(r'<[^>]+>', '', t)
    return t.replace('&quot;', '"').replace('\n', ' ').strip()

out = []
for kw in KWS:
    try:
        d = search(kw)['data']
    except Exception as e:
        out.append('## %s  -> ERROR %s' % (kw, e))
        continue
    vids = [x for x in (d.get('result') or []) if x.get('type') == 'video' and x.get('bvid')]
    vids.sort(key=lambda x: (x.get('play') or 0), reverse=True)
    out.append('## %s  (n=%d)' % (kw, len(vids)))
    for v in vids[:20]:
        out.append('%8d | %8s | %s | %-16s | %s' % (
            v.get('play') or 0, v.get('duration') or '', v['bvid'],
            clean(v.get('author') or '')[:16], clean(v.get('title') or '')[:70]))
    time.sleep(1.0)

print('\n'.join(out))
