import sys, json, concurrent.futures as cf
sys.path.insert(0,'/workspace/vesuvius'); from s3ls import ls
S=json.load(open('segments_all.json'))
def info(p):
    d,_=ls(p); r={'dirs':[x[len(p):] for x in d]}
    if p+'ink-detection/' in d: r['ink']=[(k,s) for k,s in ls(p+'ink-detection/')[1]]
    if p+'surface-volumes/' in d: r['sv']=[x[len(p):] for x in ls(p+'surface-volumes/')[0]]
    if p+'mesh/' in d: r['mesh']=[x[len(p):] for x in ls(p+'mesh/')[0]]
    return p,r
segs=[p for L in S.values() for p in L]
out={}
with cf.ThreadPoolExecutor(24) as ex:
    for p,r in ex.map(info,segs): out[p]=r
json.dump(out,open('segments_info.json','w'),indent=0)
n=sum(1 for r in out.values() if r.get('ink') and r.get('sv'))
print(len(out),'segments;',n,'with ink + sv')
