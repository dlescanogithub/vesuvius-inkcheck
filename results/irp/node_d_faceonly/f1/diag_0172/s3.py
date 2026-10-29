import json, glob, numpy as np, tifffile
from scipy import ndimage as ndi
S=json.load(open("/workspace/vesuvius/prize_oct/node_d_f1_gpu/noded/regions_f1.json"))
P="/workspace/vesuvius/prize_oct/node_d_f1_gpu/pod_results/"
def readregion(f,r0,r1,c0,c1):
    t=tifffile.TiffFile(f); p=t.pages[0]; th,tw=p.tilelength,p.tilewidth; H,W=p.shape[:2]; nx=-(-W//tw)
    out=np.zeros((r1-r0,c1-c0),np.uint8); fh=t.filehandle
    for ty in range(r0//th,(r1-1)//th+1):
        for tx in range(c0//tw,(c1-1)//tw+1):
            k=ty*nx+tx; fh.seek(p.dataoffsets[k]); data=fh.read(p.databytecounts[k])
            tile=p.decode(data,k)[0].reshape(th,tw)
            ya,yb=max(r0,ty*th),min(r1,(ty+1)*th); xa,xb=max(c0,tx*tw),min(c1,(tx+1)*tw)
            out[ya-r0:yb-r0,xa-c0:xb-c0]=tile[ya-ty*th:yb-ty*th,xa-tx*tw:xb-tx*tw]
    t.close(); return out,(H,W)
def maptile(seg,y0,x0,T):
    H,W=S[seg]["canvas"]; f=f"maps/{seg}.tif"; mh,mw=tifffile.TiffFile(f).pages[0].shape[:2]; fy,fx=mh/H,mw/W
    a,_=readregion(f,int(round(y0*fy)),int(round((y0+T)*fy)),int(round(x0*fx)),int(round((x0+T)*fx)))
    a=a.astype(np.float32)
    return ndi.zoom(a,(T/a.shape[0],T/a.shape[1]),order=1)[:T,:T], (fy,fx)
def pear(a,b,v): return round(float(np.corrcoef(a[v].astype(float),b[v].astype(float))[0,1]),3)
def top(a,v,q=0.03): t=np.quantile(a[v],1-q); return (a>=t)&v
def iou(a,b,v): x,y=top(a,v),top(b,v); return round(float((x&y).sum()/max(1,(x|y).sum())),3)
out={}
for seg,s in S.items():
    lo,hi=s["window"]
    for kind in ("positive","blank"):
        for i,t in enumerate(s[kind]):
            rid=f"{seg}__{kind[:3]}{i}"; ct=np.load(f"ct/{rid}.npy").astype(np.float32); d=np.load(P+f"preds_{rid}.npz"); v=d["valid"].astype(bool)
            prof=[float(ct[k][v].mean()) for k in range(ct.shape[0])]
            w=ct[lo:hi]; wm=w.mean(0)
            m,(fy,fx)=maptile(seg,t["y0"],t["x0"],t["size"])
            r=dict(D=ct.shape[0],window=[lo,hi],argmax_layer=int(np.argmax(prof)),prof=[round(x,1) for x in prof],
                ct_mean=round(float(w[:,v].mean()),1),ct_std=round(float(w[:,v].std()),1),ct_p3=float(np.percentile(w[:,v],3)),ct_p97=float(np.percentile(w[:,v],97)),
                ct_hp_std=round(float((wm-ndi.gaussian_filter(wm,8))[v].std()),2),
                map_scale=[round(fy,3),round(fx,3)],map_mean=round(float(m[v].mean()),1),map_frac_gt127=round(float((m[v]>127).mean()),3),map_p50=float(np.median(m[v])))
            for fa in ("fwd","rev"):
                A,B=d["rv3_"+fa],d["dn_"+fa]
                r[fa]=dict(A_ct=pear(A,wm,v),B_ct=pear(B,wm,v),A_map=pear(A,m,v),B_map=pear(B,m,v),A_map_iou=iou(A,m,v),B_map_iou=iou(B,m,v))
            out[rid]=r
json.dump(out,open("s3.json","w"),indent=1)
for rid,r in out.items():
    print(rid[:11],rid[-4:],"D%d win%s argmax%d ct %.0f±%.0f [%g,%g] hp %.1f | map mean %.0f gt127 %.2f | fwd A~ct %.2f B~ct %.2f A~map %.2f B~map %.2f iouAm %.2f iouBm %.2f | rev A~ct %.2f B~ct %.2f A~map %.2f B~map %.2f"%(
      r["D"],r["window"],r["argmax_layer"],r["ct_mean"],r["ct_std"],r["ct_p3"],r["ct_p97"],r["ct_hp_std"],r["map_mean"],r["map_frac_gt127"],
      r["fwd"]["A_ct"],r["fwd"]["B_ct"],r["fwd"]["A_map"],r["fwd"]["B_map"],r["fwd"]["A_map_iou"],r["fwd"]["B_map_iou"],r["rev"]["A_ct"],r["rev"]["B_ct"],r["rev"]["A_map"],r["rev"]["B_map"]))
