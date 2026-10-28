import json,re,os
# F1 listing + mechanical pick (prereg section 5). Run in a dir with segments_all.json / segments_info.json from crawl_f1.py / crawl2_f1.py.
# Scrolls named in F1_PRIVATE_SCROLLS (comma list; private scouting targets / private training data) are dropped from the listing entirely.
PRIVATE=set(filter(None,os.environ.get('F1_PRIVATE_SCROLLS','').split(',')))
I=json.load(open('segments_info.json')); T=json.load(open(os.environ.get('READER_V3_TRAIN','triage/reader_v3_train_segments.json')))
B=json.load(open(os.environ.get('DENSE_NATIVE_TRAIN','train_dense_native.json')))
seen={('PHerc0172','w082'),('PHerc0172','w083'),('PHerc0500P2','00371'),('PHerc0500P2','00377'),('PHerc0841','w00'),('PHerc0009B','20250919125754'),('PHerc0814','46527')}
train_ts=set(); train_w={}
for k,L in T.items():
    for s in L:
        m=re.match(r'(\d{14})',s); 
        if m: train_ts.add(m.group(1))
        for w in re.findall(r'w\d{3}',s): train_w.setdefault({'labels':'0139','0139':'0139'}.get(k,k),set()).add(w)
for ds in B['datasets']:
    for s in ds['segments']:
        sc=ds['sampling_scroll'].replace('nat','')
        for w in re.findall(r'w\d{3}',s): train_w.setdefault(sc,set()).add(w)
        for n in re.findall(r'(\d{5})$',s): train_w.setdefault(sc,set()).add(n)
rows=[]
for p,r in sorted(I.items()):
    scroll,_,seg=p.rstrip('/').split('/'); sid=seg
    why=[]
    if not (r.get('ink') and r.get('sv') and r.get('mesh')): why.append('no ink/sv/mesh')
    if scroll in ('PHerc0343','PHerc0343P'): why.append('343')
    if scroll in PRIVATE: continue
    if any(scroll==a and b in seg for a,b in seen): why.append('seen')
    ts=seg[:14]
    if ts in train_ts: why.append('A training (timestamp)')
    sc=scroll.replace('PHerc','')
    tags=set(re.findall(r'w\d{3}',seg))|set(re.findall(r'(?<!\d)(\d{5})(?!\d)',seg))
    if tags & train_w.get(sc,set()): why.append('training tag %s'%sorted(tags & train_w.get(sc,set())))
    rows.append(dict(scroll=scroll,segment=seg,eligible=not why,why=why))
json.dump(rows,open('eligibility.json','w'),indent=0)
from collections import defaultdict
E=defaultdict(list)
for x in rows:
    if x['eligible']: E[x['scroll']].append(x['segment'])
for s in sorted(E): print(s,len(E[s]),E[s][:3])
pick=[]
for rnd in (0,1):
    for s in sorted(E):
        if len(pick)<6 and len(E[s])>rnd: pick.append((s,E[s][rnd]))
print(pick)
json.dump(pick,open('pick_draft.json','w'))
