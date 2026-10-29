import numpy as np, glob, json
from scipy import ndimage as ndi
P="/workspace/vesuvius/prize_oct/node_d_f1_gpu/pod_results/"
def top(a,v,q):
    t=np.quantile(a[v],1-q); return (a>=t)&v
def iou(x,y): return (x&y).sum()/max(1,(x|y).sum())
out={}
for f in sorted(glob.glob(P+"preds_*pos*.npz")):
    rid=f.split("preds_")[1][:-4]; d=np.load(f); v=d["valid"].astype(bool); r={}
    for fa in ("fwd","rev"):
        A,B=d["rv3_"+fa].astype(float),d["dn_"+fa].astype(float)
        tA=np.quantile(A[v],0.97); r["selA_"+fa]=float(((A>=tA)&v).sum()/v.sum()); r["tA_"+fa]=float(tA); r["maxA_"+fa]=float(A[v].max())
        r["near_tA_"+fa]=float((np.abs(A[v]-tA)<=3).mean())
        r["iou_q"+fa]={q:round(float(iou(top(A,v,q),top(B,v,q))),3) for q in (0.03,0.1,0.3)}
        r["iou_sm"+fa]={s:round(float(iou(top(ndi.gaussian_filter(A,s),v,0.03),top(ndi.gaussian_filter(B,s),v,0.03))),3) for s in (2,4,8)}
        # rank-based (ties broken randomly) top 3%
        rng=np.random.default_rng(0); Aj=A+rng.uniform(0,1e-3,A.shape); Bj=B+rng.uniform(0,1e-3,B.shape)
        r["iou_jit"+fa]=round(float(iou(top(Aj,v,0.03),top(Bj,v,0.03))),3)
        # Pearson on high-pass (detail) vs low-pass
        hp=lambda x:x-ndi.gaussian_filter(x,8); lp=lambda x:ndi.gaussian_filter(x,8)
        r["pear_hp"+fa]=round(float(np.corrcoef(hp(A)[v],hp(B)[v])[0,1]),3); r["pear_lp"+fa]=round(float(np.corrcoef(lp(A)[v],lp(B)[v])[0,1]),3)
        # where is A's top 3%? mean B percentile there
        sel=top(A,v,0.03); Bv=B[v]; r["Bpct_at_Atop"+fa]=round(float((Bv[None,:]<B[sel][:,None]).mean()) if sel.sum()<5000 else float(np.mean([ (Bv<b).mean() for b in B[sel][::max(1,sel.sum()//2000)]])),3)
    out[rid]=r
json.dump(out,open("/tmp/diag0172/s2.json","w"),indent=1)
for rid,r in out.items():
    print(rid[:12],rid[-4:],"| fwd selA %.3f tA %.0f max %.0f near %.3f iou_q %s sm %s jit %.3f hp %.2f lp %.2f Bpct %.2f"%(r["selA_fwd"],r["tA_fwd"],r["maxA_fwd"],r["near_tA_fwd"],r["iou_qfwd"],r["iou_smfwd"],r["iou_jitfwd"],r["pear_hpfwd"],r["pear_lpfwd"],r["Bpct_at_Atopfwd"]))
    print(" "*17,"| rev selA %.3f tA %.0f max %.0f near %.3f iou_q %s sm %s jit %.3f hp %.2f lp %.2f Bpct %.2f"%(r["selA_rev"],r["tA_rev"],r["maxA_rev"],r["near_tA_rev"],r["iou_qrev"],r["iou_smrev"],r["iou_jitrev"],r["pear_hprev"],r["pear_lprev"],r["Bpct_at_Atoprev"]))
