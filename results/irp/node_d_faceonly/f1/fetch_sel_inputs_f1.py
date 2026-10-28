import json, re, os, urllib.request, concurrent.futures as cf
B="https://vesuvius-challenge-open-data.s3.amazonaws.com/"
I=json.load(open('segments_info.json')); P=json.load(open('pick_draft.json'))
LOW=('7.91um','8.64um','9.362um','9.366um')
plan=[]
for s,g in P:
    r=I[f'{s}/segments/{g}/']
    ink=sorted(r['ink'], key=lambda t:(re.findall(r'-(\d{14})-',t[0].split('/')[-1])[-1], t[0]))[-1][0]  # newest model run
    sv=[x for x in r['sv'] if any(x.split('/')[1].startswith(u) for u in LOW)][0]
    volid=re.search(r'volume-(\d{14})',sv).group(1)
    mesh=[m for m in r['mesh'] if f'-on-{volid}-' in m][0]
    plan.append(dict(scroll=s,segment=g,ink_map=ink,sv=f'{s}/segments/{g}/{sv}',mesh=f'{s}/segments/{g}/{mesh}'))
json.dump(plan,open('plan.json','w'),indent=1)
def get(u,p):
    if os.path.exists(p): return p
    os.makedirs(os.path.dirname(p),exist_ok=True); urllib.request.urlretrieve(u,p+'.part'); os.replace(p+'.part',p); return p
jobs=[]
for x in plan:
    k=x['scroll']+'__'+x['segment'][:14]
    jobs.append((B+x['ink_map'],f'inputs/{k}/map.tif'))
    for f in ('x.tif','meta.json'): jobs.append((B+x['mesh']+f,f'inputs/{k}/mesh_{f}'))
    jobs.append((B+x['sv']+'0/.zarray',f'inputs/{k}/sv_zarray.json'))
with cf.ThreadPoolExecutor(8) as ex: print(list(ex.map(lambda j:get(*j),jobs)))
