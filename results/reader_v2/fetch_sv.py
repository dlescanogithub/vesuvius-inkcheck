# fetch level-0 of the native 8.64um surface volume for the two Reader v2 held-out PHerc0343P segments
import os, sys, urllib.request, concurrent.futures as cf, json
B="https://vesuvius-challenge-open-data.s3.amazonaws.com/PHerc0343P/segments/%s/surface-volumes/8.64um-1.2m-116keV-volume-20250521134555.zarr/"
DST="/workspace/vesuvius/data_raw/PHerc0343P/segments/%s/surface-volumes/8.64um-1.2m-116keV-volume-20250521134555.zarr/"
def get(u,p):
    if os.path.exists(p): return 0
    os.makedirs(os.path.dirname(p),exist_ok=True)
    for i in range(4):
        try:
            d=urllib.request.urlopen(u,timeout=60).read(); open(p+'.part','wb').write(d); os.replace(p+'.part',p); return len(d)
        except urllib.error.HTTPError as e:
            if e.code==404: return 0
        except Exception: pass
    raise RuntimeError(u)
for seg in sys.argv[1:]:
    b,d=B%seg,DST%seg
    for m in ['.zgroup','.zattrs','0/.zarray']: get(b+m,d+m)
    za=json.load(open(d+'0/.zarray')); Z,Y,X=za['shape']; cy,cx=za['chunks'][1:]
    keys=[f'0/0/{i}/{j}' for i in range((Y+cy-1)//cy) for j in range((X+cx-1)//cx)]
    with cf.ThreadPoolExecutor(4) as ex: n=sum(ex.map(lambda k:get(b+k,d+k),keys))
    print(seg,len(keys),'chunks',n/1e6,'MB new',flush=True)
