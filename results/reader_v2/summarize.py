# Build SUMMARY.md from scores.jsonl (last row per segment/checkpoint wins).
import json, collections
PUB = {('343P-20250904233748', 'rv2'): 0.8058, ('343P-20250905172054', 'rv2'): 0.7282}  # reader-v2 results/040000.json auc_map
rows = collections.OrderedDict()
for l in open('scores.jsonl'):
    r = json.loads(l); rows[(r['segment'], r['checkpoint'])] = r
segs = sorted({k[0] for k in rows}, key=lambda s: (not s.startswith('paris'), s))
order = ['rv2', 'rv3', 'd9v4C', 's42', 'dn']
f = lambda v, n=3: '—' if v is None else f'{v:.{n}f}'
out = ['| segment | checkpoint | verdict | r_bp (z) | AUC (Reader v2 published) | stroke recall (chance) | area cm² | note |', '|---|---|---|---|---|---|---|---|']
for s in segs:
    for c in order:
        r = rows.get((s, c))
        if not r: continue
        pub = PUB.get((s, c)); auc = f(r['auc']) + (f' ({pub:.3f})' if pub else '')
        out.append(f"| {s} | {c} | **{r['verdict']}** | {f(r['r_bp'])} ({f(r['r_bp_z'],1)}) | {auc} | {f(r['stroke_recall'],2)} ({f(r['stroke_recall_chance'],2)}) | {f(r['area_cm2'],2)} | {r['note']} |")
open('SUMMARY_TABLE.md', 'w').write('\n'.join(out) + '\n'); print('\n'.join(out))
