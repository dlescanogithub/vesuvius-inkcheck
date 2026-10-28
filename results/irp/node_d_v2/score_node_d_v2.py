"""Score node D v2 held-out validation (PREREG_NODE_D_V2.md sha256 1bc3423e...) from the pod's cropped predictions.
Usage: score_node_d_v2.py <pod noded/out dir> <regions_render.json> <align_pitch.json> <out.json>
A = Reader V3 (rv3), B = dense_native (dn). Rule = inkcheck.node_d_v2 (committed, unchanged)."""
import sys, json, math, numpy as np
sys.path.insert(0, '/workspace/vesuvius/prize_oct/publish/vesuvius-inkcheck/src'); sys.path.insert(0, '/workspace/vesuvius/hires_test/tools')
from inkcheck.node_d_v2 import face_stats, candidate_rule_v2, RULE_V2
from score import metrics, stroke_width
OUTD, RR, AP, OJ = sys.argv[1:5]
regs = json.load(open(RR)); ap = json.load(open(AP)); meta = json.load(open(f"{OUTD}/job3_meta.json"))
ap = {a["name"]: a for a in (ap if isinstance(ap, list) else ap.get("regions", ap.values()))} if not (isinstance(ap, dict) and regs[0]["name"] in ap) else ap
def load(name):
    d = np.load(f"{OUTD}/preds_{name}.npz"); return {k: (d[k] if k == "valid_d0" else d[k].astype(np.float32) / 255.) for k in d.files}
def maps(d, ck, face):
    return d.get(f"{ck}_d0_{face}"), [d[f"{ck}_{s}_{face}"] for s in ("plus", "minus") if f"{ck}_{s}_{face}" in d]
def score(dA, dB, valid, evaluable):
    st = {}
    for f in ("fwd", "rev"):
        A, Aoff = maps(dA, "rv3", f); B, Boff = maps(dB, "dn", f)
        st[f] = face_stats(A, B, Aoff if evaluable else [], Boff if evaluable else [], valid)
    out, why, nums = candidate_rule_v2(st["fwd"], st["rev"])
    if not evaluable: out, why = "NOT_EVALUABLE", ["no winding pitch in 6-60 voxels (counted as not-CANDIDATE)"] + why
    if valid.sum() == 0: out, why = "NOT_EVALUABLE", ["no valid CT pixels on the card window"]
    best = nums["best_face"]
    face_only = bool(nums["iou_best"] >= RULE_V2["min_iou"] and nums["s1_face_asym"] >= RULE_V2["min_face_asym"]) and valid.sum() > 0
    return dict(outcome=out, why=why, numbers={k: (round(v, 4) if isinstance(v, float) else v) for k, v in nums.items()},
                faces={f: dict(iou=round(s["iou"], 4), p=round(s["p"], 4), null_mean=s["null_mean"] and round(s["null_mean"], 4),
                               iou_off=[round(x, 4) for x in s["iou_offwinding"]], s2=s["s2"] and round(s["s2"], 3)) for f, s in st.items()},
                face_only=face_only, best_face=best)
def v1(d, valid, um, best):
    """v1 descriptive: per checkpoint, reading = v2's best face, null = other face; criteria of hires_test verdict
    (ratio>=2, >=5 comps, r to the other checkpoint >=0.3, stroke width 100-500 um); CANDIDATE if both checkpoints pass."""
    if valid.sum() == 0: return dict(outcome="NOT_EVALUABLE")
    oth = "rev" if best == "fwd" else "fwd"; res = {}; cm2 = valid.sum() * (um / 1e4) ** 2
    r = float(np.corrcoef(d[f"rv3_d0_{best}"][valid], d[f"dn_d0_{best}"][valid])[0, 1])
    for ck in ("rv3", "dn"):
        mr, mn = metrics(d[f"{ck}_d0_{best}"], valid, um), metrics(d[f"{ck}_d0_{oth}"], valid, um)
        sw = stroke_width(np.where(valid, d[f"{ck}_d0_{best}"], 0), um); c, cn = mr["comps_per_cm2"], mn["comps_per_cm2"]
        crit = dict(i_ratio=bool((cn == 0 and c > 0) or (cn and c / cn >= 2)), ii_min5=bool(round(c * cm2) >= 5), iii_r=bool(r >= 0.3),
                    iv_width=bool(sw is not None and 100 <= sw["median_um"] <= 500))
        res[ck] = dict(comps_reading=c, comps_null=cn, ratio=round(c / cn, 2) if cn else None, criteria=crit, passes=all(crit.values()))
    return dict(outcome="CANDIDATE" if all(v["passes"] for v in res.values()) else "NOTHING", r_rv3_dn=round(r, 3), models=res)
R = {"rule": RULE_V2, "regions": {}, "controls": {}}
pos = [g for g in regs if g["kind"] == "positive"]; data = {}
for g in regs:
    n = g["name"]; d = load(n); data[n] = d; P = ap[n]["pitch"]; valid = d["valid_d0"].astype(bool)
    s = score(d, d, valid, P is not None); s.update(kind=g["kind"], seg=g["seg"], pitch=P, valid_px=int(valid.sum()),
                                                    windows=meta["items"][n]["windows"], v1=v1(d, valid, g["um"], s["best_face"]))
    R["regions"][n] = s; print(n, s["outcome"], s["numbers"]["iou_best"], s["numbers"]["s1_face_asym"], s["numbers"]["s2_best"], s["face_only"], s["v1"]["outcome"], flush=True)
# controls: (a) B block-shuffled in 0.5 mm blocks, one permutation for all faces/offsets; (b) A_i with B_{i+1}, cyclic
rng = np.random.default_rng(0)
for i, g in enumerate(pos):
    n = g["name"]; d = data[n]; P = ap[n]["pitch"]; valid = d["valid_d0"].astype(bool); b = max(1, round(500 / g["um"]))
    H, W = (valid.shape[0] // b) * b, (valid.shape[1] // b) * b; perm = rng.permutation((H // b) * (W // b))
    def shuf(a):
        t = a[:H, :W].reshape(H // b, b, W // b, b).swapaxes(1, 2).reshape(-1, b, b)[perm]
        return t.reshape(H // b, W // b, b, b).swapaxes(1, 2).reshape(H, W)
    dB = {k: (shuf(v) if k.startswith("dn_") else v[:H, :W]) for k, v in d.items()}
    sa = score(dB, dB, valid[:H, :W], P is not None); R["controls"][f"{n}|a_block_shuffle"] = dict(outcome=sa["outcome"], numbers=sa["numbers"], block_px=b)
    m = pos[(i + 1) % len(pos)]; d2 = data[m["name"]]; h = min(valid.shape[0], d2["valid_d0"].shape[0]); w = min(valid.shape[1], d2["valid_d0"].shape[1])
    cA = {k: v[:h, :w] for k, v in d.items()}; cB = {k: v[:h, :w] for k, v in d2.items()}; vv = valid[:h, :w] & d2["valid_d0"][:h, :w].astype(bool)
    sb = score(cA, cB, vv, P is not None and ap[m["name"]]["pitch"] is not None)
    R["controls"][f"{n}|b_A_with_B_of_{m['name']}"] = dict(outcome=sb["outcome"], numbers=sb["numbers"])
for k, c in R["controls"].items(): print("ctrl", k, c["outcome"], c["numbers"]["iou_best"])
NP, NB = len(pos), sum(g["kind"] == "blank" for g in regs)
cand = lambda kind, key="outcome": [n for n, s in R["regions"].items() if s["kind"] == kind and (s[key] == "CANDIDATE" if key == "outcome" else s[key] is True)]
pc = cand("positive"); bc = cand("blank"); segs = sorted({R["regions"][n]["seg"] for n in pc}); cc = [k for k, c in R["controls"].items() if c["outcome"] == "CANDIDATE"]
need = math.ceil(2 / 3 * NP); allow = max(1, math.floor(0.10 * NB))
c1 = len(pc) >= need and len(segs) >= 4; c2 = len(bc) <= allow; c3 = len(cc) == 0
R["verdict"] = dict(N_pos=NP, N_blank=NB, N_blank_evaluable=sum(1 for s in R["regions"].values() if s["kind"] == "blank" and s["valid_px"] > 0 and s["pitch"] is not None),
                    pos_candidates=pc, segments_with_candidate=segs, need_pos=need, sensitivity=c1, blank_candidates=bc, blank_allow=allow, specificity=c2,
                    control_candidates=cc, n_controls=len(R["controls"]), controls=c3, VERDICT="ACCEPTED" if c1 and c2 and c3 else "REJECTED",
                    side_by_side={"v2": [len(pc), len(bc)], "face_only": [len(cand("positive", "face_only")), len(cand("blank", "face_only"))],
                                  "v1": [sum(1 for s in R["regions"].values() if s["kind"] == "positive" and s["v1"]["outcome"] == "CANDIDATE"),
                                         sum(1 for s in R["regions"].values() if s["kind"] == "blank" and s["v1"]["outcome"] == "CANDIDATE")]})
# PHerc0343 (Erwin) under v2: diagnosis only (design data, not validation)
if "erwin343" in meta["items"] and __import__("os").path.exists(f"{OUTD}/preds_erwin343.npz"):
    d = load("erwin343"); P = meta["items"]["erwin343"]["pitch"]; valid = d["valid_d0"].astype(bool)
    s = score(d, d, valid, P is not None); s.update(pitch=P, valid_px=int(valid.sum()), v1=v1(d, valid, 8.64, s["best_face"])); R["erwin343_diagnosis"] = s
    print("343", s["outcome"], s["numbers"], s["faces"])
print(json.dumps(R["verdict"], indent=1)); json.dump(R, open(OJ, "w"), indent=1, default=float)
