import json,sys,numpy as np
sys.argv=["x"]; src=open("/workspace/vesuvius/prize_oct/node_d_f1_gpu/noded/job_f1.py").read()
import urllib.request,urllib.error,time,os,concurrent.futures as cf
BUCKET="https://vesuvius-challenge-open-data.s3.amazonaws.com/"
ns={"np":np,"urllib":urllib,"time":time,"cf":cf,"BUCKET":BUCKET,"os":os,"json":json}
start=src.index("def chunk"); end=src.index("SEL = json.load")
exec(src[start:end],ns)
S=json.load(open("/workspace/vesuvius/prize_oct/node_d_f1_gpu/noded/regions_f1.json"))
M=128
def crop(seg,kind,i):
    s=S[seg]; t=s[kind][i]; T=t["size"]
    return ns["fetch"](s["sv"],s["depth"],*s["canvas"],t["y0"]-M,t["x0"]-M,T+2*M,T+2*M,s["window"][0]),T
def hmatch(src,ref):
    sv=src[src>0]; rv=ref[ref>0]
    q=np.linspace(0,1,1001); sq=np.quantile(sv,q); rq=np.quantile(rv,q)
    out=np.interp(src.astype(np.float32),sq,rq); out=np.clip(np.round(out),1,255).astype(np.uint8); out[src==0]=0; return out
c172,T172=crop("PHerc0172__20250926145427","positive",0)
c841,T841=crop("PHerc0841__20260220214732","positive",0)
c009,T009=crop("PHerc0009B__20250510172639","positive",0)
V={"172raw":c172,"172to009":hmatch(c172,c009),"172to841":hmatch(c172,c841),"841raw":c841,"841to172":hmatch(c841,c172)}
for k,a in V.items():
    ns["write_zarr"](f"{k}.zarr",a); print(k,a.shape,round(float(a[a>0].mean()),1),np.percentile(a[a>0],[3,50,97]))
json.dump({"M":M,"T":{"172":T172,"841":T841}},open("meta.json","w"))
