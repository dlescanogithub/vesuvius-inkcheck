import json,numpy as np,tifffile,os
from scipy import ndimage as ndi
m=json.load(open("meta.json")); M=m["M"]; P="/workspace/vesuvius/prize_oct/node_d_f1_gpu/pod_results/"
ref={"172":"PHerc0172__20250926145427__pos0","841":"PHerc0841__20260220214732__pos0"}
def load(f,T):
    a=tifffile.imread(f).astype(np.float32); N=T+2*M
    if a.shape!=(N,N): a=ndi.zoom(a,(N/a.shape[0],N/a.shape[1]),order=1)[:N,:N]
    return a[M:M+T,M:M+T]
def top(a,v,q=0.03): return (a>=np.quantile(a[v],1-q))&v
def iou(a,b,v): x,y=top(a,v),top(b,v); return float((x&y).sum()/max(1,(x|y).sum()))
def S1(i1,i2): return max(i1,i2)/max(min(i1,i2),1e-3)
res={}
for v in ["172raw","841raw","172to009","172to841","841to172"]:
    seg=v[:3]; T=m["T"][seg]; d=np.load(P+f"preds_{ref[seg]}.npz"); val=d["valid"].astype(bool); r={}
    try:
        for fa,suf in (("fwd",""),("rev","_reverse")):
            A=load(f"out_{v}_rv3{suf}.tif",T); B=load(f"out_{v}_dn{suf}.tif",T)
            r[fa]=dict(iou=round(iou(A,B,val),3),pear=round(float(np.corrcoef(A[val],B[val])[0,1]),3),
                A_med=float(np.median(A[val])),A_gt128=round(float((A[val]>128).mean()),3),B_med=float(np.median(B[val])),
                A_vs_gpu=round(float(np.corrcoef(A[val],d["rv3_"+fa][val].astype(float))[0,1]),3) if v.endswith("raw") else None,
                B_vs_gpu=round(float(np.corrcoef(B[val],d["dn_"+fa][val].astype(float))[0,1]),3) if v.endswith("raw") else None)
        r["S1"]=round(S1(r["fwd"]["iou"],r["rev"]["iou"]),2); r["best_iou"]=max(r["fwd"]["iou"],r["rev"]["iou"])
    except FileNotFoundError as e: r["missing"]=str(e)
    res[v]=r; print(v,json.dumps(r))
json.dump(res,open("causal.json","w"),indent=1)
