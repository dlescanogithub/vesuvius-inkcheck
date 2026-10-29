"""Face-only node D, set F2: mechanical visit order + region selection (PREREG_F2.md §2-§3). Uses ONLY the committed F1
listing/eligibility, the team ink maps, the meshes and the raw CT (blank >= 80 % valid-CT check). No model output exists.
Usage: python select_f2.py plan <segments_info.json> plan_f2.json        (visit order; metadata only)
       python select_f2.py select plan_f2.json <inputs dir> regions_f2.json selection_log_f2.txt
<segments_info.json> = the 2026-10-28 F1 crawl (crawl2_f1.py output; not committed because it lists out-of-scope scrolls)."""
import json, os, re, sys, hashlib, traceback, urllib.request
H = os.path.dirname(os.path.abspath(__file__)); F1 = os.path.join(H, "..", "f1")
sys.path.insert(0, F1)
B = "https://vesuvius-challenge-open-data.s3.amazonaws.com/"; LOW = ("7.91um", "8.64um", "9.362um", "9.366um")
BLANK_TARGET, MAX_VISITS, MAX_ATTEMPTS = 8, 18, 30

def plan(info_p, out_p):
    I = json.load(open(info_p)); E = [e for e in json.load(open(f"{F1}/eligibility_f1.json")) if e["eligible"]]
    used = {(s, g) for s, g in json.load(open(f"{F1}/pick_f1.json"))}
    by = {}
    for e in E:
        s, g = e["scroll"], e["segment"]
        if (s, g) in used: continue
        r = I[f"{s}/segments/{g}/"]
        svs = [x for x in r["sv"] if any(x.split("/")[1].startswith(u) for u in LOW)]
        if not svs or not r["ink"]: continue
        sv = svs[0]; volid = re.search(r"volume-(\d{14})", sv).group(1)
        mesh = [m for m in r["mesh"] if f"-on-{volid}-" in m]
        if not mesh: continue
        ink = sorted(r["ink"], key=lambda t: (re.findall(r"-(\d{14})-", t[0].split("/")[-1])[-1], t[0]))[-1][0]
        by.setdefault(s, []).append(dict(scroll=s, segment=g, ink_map=ink, sv=f"{s}/segments/{g}/{sv}", mesh=f"{s}/segments/{g}/{mesh[0]}"))
    order, k = [], 0
    while any(len(v) > k for v in by.values()):
        for s in sorted(by):
            v = sorted(by[s], key=lambda x: x["segment"])
            if len(v) > k: order.append(v[k])
        k += 1
    keys = [x["scroll"] + "__" + x["segment"][:14] for x in order]; assert len(set(keys)) == len(keys)
    json.dump(dict(listing_sha256=hashlib.sha256(open(info_p, "rb").read()).hexdigest(), n=len(order),
                   per_scroll={s: len(v) for s, v in sorted(by.items())}, order=order), open(out_p, "w"), indent=1)
    print(len(order), {s: len(v) for s, v in sorted(by.items())})

def get(u, p):
    if os.path.exists(p): return
    os.makedirs(os.path.dirname(p), exist_ok=True); urllib.request.urlretrieve(u, p + ".part"); os.replace(p + ".part", p)

def select_all(plan_p, inputs, out_p, log_p):
    from select_regions_f1 import select
    P = json.load(open(plan_p))["order"]; res, log = {}, open(log_p, "a")
    nb = visits = attempts = 0
    for seg in P:
        if nb >= BLANK_TARGET or visits >= MAX_VISITS or attempts >= MAX_ATTEMPTS: break
        attempts += 1; key = seg["scroll"] + "__" + seg["segment"][:14]; d = f"{inputs}/{key}"
        try:
            get(B + seg["ink_map"], f"{d}/map.tif"); get(B + seg["mesh"] + "x.tif", f"{d}/mesh_x.tif")
            get(B + seg["sv"] + "0/.zarray", f"{d}/sv_zarray.json")
            r = select(seg, d)
        except Exception as e:
            msg = f"SKIP {key}: {type(e).__name__}: {str(e)[:200]}"; print(msg, flush=True); log.write(msg + "\n"); log.flush()
            try: os.remove(f"{d}/map.tif")
            except OSError: pass
            continue
        visits += 1; nb += len(r["blank"]); res[key] = r
        msg = (f"VISIT {visits} {key} tiles {r['n_tiles']} pos {[(t['row'], t['col'], round(t['ink_frac'], 3), t['strokes'], t['ct_valid_frac']) for t in r['positive']]} "
               f"blank {[(t['row'], t['col'], t['dist_to_ink_mm'], t['ct_valid_frac']) for t in r['blank']]} visited {len(r['blank_visited'])} cum_blank {nb}")
        print(msg, flush=True); log.write(msg + "\n"); log.flush(); json.dump(res, open(out_p, "w"), indent=1)
        try: os.remove(f"{d}/map.tif")  # maps are large; re-fetchable
        except OSError: pass
    s = f"STOP attempts={attempts} visits={visits} blanks={nb} positives={sum(len(r['positive']) for r in res.values())}"
    print(s); log.write(s + "\n"); json.dump(res, open(out_p, "w"), indent=1)

if __name__ == "__main__":
    if sys.argv[1] == "plan": plan(*sys.argv[2:4])
    else: select_all(*sys.argv[2:6])
