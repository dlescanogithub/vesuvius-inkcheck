import numpy as np, glob, json
from scipy import ndimage as ndi
P="/workspace/vesuvius/prize_oct/node_d_f1_gpu/pod_results/"
def top(a,v,q=0.03):
    t=np.quantile(a[v],1-q); return (a>=t)&v
def iou(a,b,v): x,y=top(a,v),top(b,v); return (x&y).sum()/max(1,(x|y).sum())
def pear(a,b,v): return float(np.corrcoef(a[v].astype(float),b[v].astype(float))[0,1])
def xcorr_shift(a,b,R=64):
    a=a.astype(float);b=b.astype(float);a=(a-a.mean())/a.std();b=(b-b.mean())/b.std()
    F=np.fft.irfft2(np.fft.rfft2(a)*np.conj(np.fft.rfft2(b)),s=a.shape)/a.size
    F=np.fft.fftshift(F); c=np.array(F.shape)//2; W=F[c[0]-R:c[0]+R+1,c[1]-R:c[1]+R+1]
    i=np.unravel_index(W.argmax(),W.shape); return float(W[R,R]),float(W.max()),(int(i[0]-R),int(i[1]-R))
out={}
for f in sorted(glob.glob(P+"preds_*.npz")):
    rid=f.split("preds_")[1][:-4]; d=np.load(f); v=d["valid"].astype(bool)
    r={}
    for k in ("rv3_fwd","rv3_rev","dn_fwd","dn_rev"):
        a=d[k][v].astype(float); r[k]=dict(p50=float(np.median(a)),p3=float(np.percentile(a,3)),p97=float(np.percentile(a,97)),frac_gt128=float((a>128).mean()),
            smooth_std=float(ndi.gaussian_filter(d[k].astype(float),8)[v].std()))
    for fa in ("fwd","rev"):
        A,B=d["rv3_"+fa],d["dn_"+fa]; r["pear_"+fa]=pear(A,B,v); r["iou_"+fa]=float(iou(A,B,v))
        c0,cm,sh=xcorr_shift(A,B); r["xc_"+fa]=dict(zero=c0,best=cm,shift=sh)
        # flips/transposes of B vs A
        r["orient_"+fa]={n:pear(A,t(B),v) if t(B).shape==A.shape else None for n,t in
            dict(id=lambda x:x,fliplr=np.fliplr,flipud=np.flipud,rot180=lambda x:np.rot90(x,2),T=lambda x:x.T).items()}
        # cross-face: A fwd vs B rev
    r["pear_Afwd_Brev"]=pear(d["rv3_fwd"],d["dn_rev"],v); r["pear_Arev_Bfwd"]=pear(d["rv3_rev"],d["dn_fwd"],v)
    r["iou_Afwd_Brev"]=float(iou(d["rv3_fwd"],d["dn_rev"],v)); r["iou_Arev_Bfwd"]=float(iou(d["rv3_rev"],d["dn_fwd"],v))
    r["pear_A_fwd_rev"]=pear(d["rv3_fwd"],d["rv3_rev"],v); r["pear_B_fwd_rev"]=pear(d["dn_fwd"],d["dn_rev"],v)
    out[rid]=r
json.dump(out,open("/tmp/diag0172/s1.json","w"),indent=1)
for rid,r in out.items():
    print(rid[:22],rid[-4:],"A p50 %.0f/%.0f gt128 %.2f/%.2f sstd %.1f | B p50 %.0f/%.0f sstd %.1f | pear f %.2f r %.2f | xc f %.2f->%.2f %s r %.2f->%.2f %s | orient f %s | xface %.2f %.2f | AfA r %.2f BfB r %.2f"%(
     r["rv3_fwd"]["p50"],r["rv3_rev"]["p50"],r["rv3_fwd"]["frac_gt128"],r["rv3_rev"]["frac_gt128"],r["rv3_fwd"]["smooth_std"],r["dn_fwd"]["p50"],r["dn_rev"]["p50"],r["dn_fwd"]["smooth_std"],
     r["pear_fwd"],r["pear_rev"],r["xc_fwd"]["zero"],r["xc_fwd"]["best"],r["xc_fwd"]["shift"],r["xc_rev"]["zero"],r["xc_rev"]["best"],r["xc_rev"]["shift"],
     {k:round(x,2) for k,x in r["orient_fwd"].items()},r["pear_Afwd_Brev"],r["pear_Arev_Bfwd"],r["pear_A_fwd_rev"],r["pear_B_fwd_rev"]))
