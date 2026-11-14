# -*- coding: utf-8 -*-
import hashlib, time, urllib.parse

IMG = '7cd084941338484aae1ad9425b84077c'
SUB = '4932caff0ff746eab6f01bf08b70ac45'
TAB = [46,47,18,2,53,8,23,32,15,50,10,31,58,3,45,35,27,43,5,49,33,9,42,19,29,28,
       14,39,12,38,41,13,37,48,7,16,24,55,40,61,26,17,0,1,60,51,30,4,22,25,54,21,
       56,59,6,63,57,62,11,36,20,34,44,52]
raw = IMG + SUB
mixin = ''.join(raw[i] for i in TAB)[:32]

KWS = ['大模型 应用开发 实战', 'RAG 从零 实现', '手写 Agent 框架',
       'LLaMA-Factory 微调', 'LLM 面试 八股', 'Transformer 李沐 详解',
       '大模型 实习 面经']

for kw in KWS:
    wts = int(time.time())
    params = {'keyword': kw, 'page': '1', 'search_type': 'video', 'wts': str(wts)}
    query = '&'.join('%s=%s' % (k, urllib.parse.quote(str(params[k]), safe=''))
                     for k in sorted(params))
    w_rid = hashlib.md5((query + mixin).encode('utf-8')).hexdigest()
    print('### ' + kw)
    print('https://api.bilibili.com/x/web-interface/wbi/search/type?' + query + '&w_rid=' + w_rid)
