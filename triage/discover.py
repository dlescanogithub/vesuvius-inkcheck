"""List public segments with a ~8-10 um surface volume on the Vesuvius Challenge open-data bucket and pick up to
K per scroll (evenly spaced in the listing), recording whether the segment also has an ink-detection map (a possible
node-A reference). Writes triage/segments.json. Read-only, anonymous listing."""
import json, re, sys, urllib.request
B = "https://vesuvius-challenge-open-data.s3.amazonaws.com/"
K = int(sys.argv[1]) if len(sys.argv) > 1 else 3


def ls(prefix):
    out, tok = [], None
    while True:
        u = f"{B}?list-type=2&delimiter=/&prefix={prefix}" + (f"&continuation-token={urllib.parse.quote(tok)}" if tok else "")
        x = urllib.request.urlopen(u, timeout=60).read().decode()
        out += re.findall(r"<Prefix>([^<]+)</Prefix>", x)[1:] if "<CommonPrefixes>" in x else []
        m = re.search(r"<NextContinuationToken>([^<]+)", x)
        if not m: return [p for p in out if p != prefix]
        tok = m.group(1)


import urllib.parse
scrolls = [p for p in ls("") if p.startswith("PHerc")]
res = []
for s in scrolls:
    try:
        segs = ls(s + "segments/")
    except Exception as e:
        print(s, "ERR", e); continue
    cand = []
    for seg in segs:
        cand.append(seg)
    pick = [cand[int(i * len(cand) / K)] for i in range(min(K, len(cand)))] if cand else []
    for seg in pick:
        try:
            vols = [v for v in ls(seg + "surface-volumes/") if v.endswith(".zarr/")]
        except Exception:
            vols = []
        um = []
        for v in vols:
            m = re.search(r"/([0-9.]+)um", v)
            if m and 7.0 <= float(m.group(1)) <= 10.0: um.append((float(m.group(1)), v))
        if not um: continue
        u, v = sorted(um)[0]
        try:
            ink = bool(ls(seg + "ink-detection/"))
        except Exception:
            ink = False
        try:
            ink = ink or bool(re.search(r"<Key>", urllib.request.urlopen(f"{B}?list-type=2&max-keys=1&prefix={seg}ink-detection/", timeout=60).read().decode()))
        except Exception:
            pass
        res.append(dict(scroll=s.rstrip("/"), segment=seg.split("/")[-2], volume=v.rstrip("/"), um=u, has_ink_map=ink))
        print(res[-1], flush=True)
    json.dump(res, open("prize_oct/publish/vesuvius-inkcheck/triage/segments.json", "w"), indent=1)
print("n", len(res))
