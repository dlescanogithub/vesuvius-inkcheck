import sys, json, concurrent.futures as cf
sys.path.insert(0,'/workspace/vesuvius'); from s3ls import ls
scrolls=[d.rstrip('/') for d in ls('')[0]]
def segs(s):
    d,_=ls(s+'/segments/'); return s,[x for x in d]
out={}
with cf.ThreadPoolExecutor(16) as ex:
    for s,L in ex.map(segs,scrolls): out[s]=L; print(s,len(L),flush=True)
json.dump(out,open('segments_all.json','w'),indent=0)
