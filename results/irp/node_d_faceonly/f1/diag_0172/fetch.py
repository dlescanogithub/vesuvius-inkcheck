import json, os, urllib.request, urllib.error, numpy as np, concurrent.futures as cf
B="https://vesuvius-challenge-open-data.s3.amazonaws.com/"
S=json.load(open("/workspace/vesuvius/prize_oct/node_d_f1_gpu/noded/regions_f1.json"))
def get(u,p):
    if os.path.exists(p): return
    urllib.request.urlretrieve(u,p+".part"); os.replace(p+".part",p)
def chunk(key,D,yi,xi):
    for t in range(4):
        try: return np.frombuffer(urllib.request.urlopen(f"{B}{key}0/0/{yi}/{xi}",timeout=120).read(),np.uint8).reshape(D,128,128)
        except urllib.error.HTTPError as e:
            if e.code in (403,404): return None
        except Exception: pass
    raise RuntimeError("chunk")
os.makedirs("ct",exist_ok=True); os.makedirs("maps",exist_ok=True)
for seg,s in S.items():
    get(B+s["ink_map"],f"maps/{seg}.tif"); print("map",seg,flush=True)
    D=s["depth"]
    for kind in ("positive","blank"):
        for i,t in enumerate(s[kind]):
            rid=f"{seg}__{kind[:3]}{i}"; p=f"ct/{rid}.npy"
            if os.path.exists(p): continue
            y0,x0,T=t["y0"],t["x0"],t["size"]; out=np.zeros((D,T,T),np.uint8); c=128
            jobs=[(yi,xi) for yi in range(y0//c,(y0+T-1)//c+1) for xi in range(x0//c,(x0+T-1)//c+1)]
            with cf.ThreadPoolExecutor(16) as ex:
                for (yi,xi),b in zip(jobs,ex.map(lambda j:chunk(s["sv"],D,*j),jobs)):
                    if b is None: continue
                    gy0,gy1=max(y0,yi*c),min(y0+T,(yi+1)*c); gx0,gx1=max(x0,xi*c),min(x0+T,(xi+1)*c)
                    out[:,gy0-y0:gy1-y0,gx0-x0:gx1-x0]=b[:,gy0-yi*c:gy1-yi*c,gx0-xi*c:gx1-xi*c]
            np.save(p,out); print("ct",rid,out.shape,flush=True)
