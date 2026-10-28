"""Score set F1 with the committed face-only rule (prereg 22feecb §2, §5, §6). Numbers only.
Usage: PYTHONPATH=src python score_f1.py <preds dir> regions_f1.json out.json
Inputs per region: preds_<seg>__<kind><i>.npz with rv3_fwd, rv3_rev (A), dn_fwd, dn_rev (B), valid (non-zero CT on all 17 layers)."""
import json, math, sys, numpy as np
from inkcheck.node_d_v2 import face_only_from_maps, RULE_FACE_ONLY
pdir, sel_p, out_p = sys.argv[1:4]; SEL = json.load(open(sel_p))
def ld(rid): d = np.load(f"{pdir}/preds_{rid.replace('|', '__')}.npz"); return {k: d[k] for k in d.files}
def run(A, B, valid):
    o, why, n = face_only_from_maps(A, B, valid); return dict(outcome=o, why=why, numbers={k: (round(v, 5) if isinstance(v, float) else v) for k, v in n.items()})
R = {"rule": RULE_FACE_ONLY, "regions": {}, "controls": {}}; pos = []
for seg, s in SEL.items():
    for kind in ("positive", "blank"):
        for i, t in enumerate(s[kind]):
            rid = f"{seg}|{kind[:3]}{i}"; d = ld(rid); v = d["valid"].astype(bool)
            r = run({"fwd": d["rv3_fwd"], "rev": d["rv3_rev"]}, {"fwd": d["dn_fwd"], "rev": d["dn_rev"]}, v)
            r.update(seg=seg, kind=kind, row=t["row"], col=t["col"], um=s["um"]); R["regions"][rid] = r
            if kind == "positive": pos.append((rid, s["um"]))
            print(rid, r["outcome"], r["numbers"]["iou_best"], round(r["numbers"]["s1_face_asym"], 3), r["numbers"]["valid_frac"], r["numbers"]["p_best"], flush=True)
rng = np.random.default_rng(0)  # (a) one permutation per positive, drawn in selection order
for i, (rid, um) in enumerate(pos):
    d = ld(rid); v = d["valid"].astype(bool); b = max(1, round(500 / um)); H, W = (v.shape[0] // b) * b, (v.shape[1] // b) * b
    perm = rng.permutation((H // b) * (W // b))
    def shuf(a):
        t = a[:H, :W].reshape(H // b, b, W // b, b).swapaxes(1, 2).reshape(-1, b, b)[perm]
        return t.reshape(H // b, W // b, b, b).swapaxes(1, 2).reshape(H, W)
    ra = run({"fwd": d["rv3_fwd"][:H, :W], "rev": d["rv3_rev"][:H, :W]}, {"fwd": shuf(d["dn_fwd"]), "rev": shuf(d["dn_rev"])}, v[:H, :W])
    R["controls"][f"{rid}|a_block_shuffle"] = dict(ra, block_px=b)
    m = pos[(i + 1) % len(pos)][0]; d2 = ld(m); h = min(v.shape[0], d2["valid"].shape[0]); w = min(v.shape[1], d2["valid"].shape[1])
    vv = v[:h, :w] & d2["valid"][:h, :w].astype(bool)
    rb = run({"fwd": d["rv3_fwd"][:h, :w], "rev": d["rv3_rev"][:h, :w]}, {"fwd": d2["dn_fwd"][:h, :w], "rev": d2["dn_rev"][:h, :w]}, vv)
    R["controls"][f"{rid}|b_A_with_B_of_{m}"] = rb
    print("ctrl", rid, ra["outcome"], rb["outcome"], flush=True)
# §6
P = [r for r in R["regions"].values() if r["kind"] == "positive"]; Bl = [r for r in R["regions"].values() if r["kind"] == "blank"]
segs = sorted(SEL); n_pos, n_seg, n_bl = len(P), len(segs), len(Bl)
pf = sum(r["outcome"] == "FLAG" for r in P); sf = sum(any(r["outcome"] == "FLAG" for r in P if r["seg"] == s) for s in segs)
c1 = pf >= math.ceil(2 / 3 * n_pos) and sf >= math.ceil(2 / 3 * n_seg)
bl_eval = [r for r in Bl if r["outcome"] != "NOT_EVALUABLE"]; bf = sum(r["outcome"] == "FLAG" for r in bl_eval)
c2 = "UNTESTED" if n_bl < 4 else (bf <= max(1, math.floor(0.1 * n_bl)))
ca = [c for k, c in R["controls"].items() if "|a_" in k]; cb = [c for k, c in R["controls"].items() if "|b_" in k]
af, bfc = sum(c["outcome"] == "FLAG" for c in ca), sum(c["outcome"] == "FLAG" for c in cb)
c3 = af == 0 and bfc <= max(1, math.floor(0.1 * len(cb)))
verdict = ("ACCEPTED" if c1 and c2 is True and c3 else "PROVISIONAL" if c1 and c3 and c2 == "UNTESTED" else "REJECTED")
R["summary"] = dict(N_pos=n_pos, N_segments=n_seg, N_blank=n_bl, pos_flagged=pf, pos_needed=math.ceil(2 / 3 * n_pos), segments_flagged=sf,
                    segments_needed=math.ceil(2 / 3 * n_seg), pos_not_evaluable=sum(r["outcome"] == "NOT_EVALUABLE" for r in P),
                    blank_evaluable=len(bl_eval), blank_flagged=bf, controls_a_flagged=af, controls_a=len(ca), controls_b_flagged=bfc, controls_b=len(cb),
                    criterion1_sensitivity=c1, criterion2_specificity=c2, criterion3_controls=c3, verdict=verdict)
json.dump(R, open(out_p, "w"), indent=1); print(json.dumps(R["summary"], indent=1))
