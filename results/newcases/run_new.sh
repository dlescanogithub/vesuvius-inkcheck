#!/bin/bash
# New held-out cases (PHerc0841, PHerc0009B, PHerc0172, PHerc0500P2): Reader V3 + dense_native (+ Reader v2) on CPU.
# nice 19, OMP_WAIT_POLICY=PASSIVE, 3 threads, one job at a time; resumable (score.py skips existing preds).
cd /workspace/vesuvius
export PYTHONPATH=/workspace/vesuvius/prize_oct/publish/vesuvius-inkcheck/src:/workspace/vesuvius/villa/vesuvius/src
export OMP_WAIT_POLICY=PASSIVE KMP_BLOCKTIME=0 OMP_NUM_THREADS=3 MKL_NUM_THREADS=3 OPENBLAS_NUM_THREADS=3
export VILLA_PY=/workspace/vesuvius/.venv314/bin/python
PY=.venv314/bin/python; S=prize_oct/publish/vesuvius-inkcheck/bench/score.py
NC=prize_oct/publish/vesuvius-inkcheck/results/newcases; OUT=$NC/scores; C=checkpoints
J=$NC/cases.json
declare -A CK=([rv3]=$C/reader/reader-v3.pth [dn]=$C/erwin/dense_native_016000.pth [rv2]=$C/reader/reader-v2-step040000.pth)
field () { $PY -c "import json,sys;c=json.load(open('$J'))['$1'];r=c['refs'].get('$2',{});print(eval(sys.argv[1]))" "$3"; }
run () { # case tag
  case=$1; tag=$2
  refs=$($PY -c "import json;print(' '.join(json.load(open('$J'))['$case']['refs']))")
  first=""
  for r in $refs; do
    name=$case-$r
    args="--name $name --scroll ${case%%-*} --um $(field $case $r "c['pred_um']") --ref $(field $case $r "r['ref']") \
      --ref-um $(field $case $r "r['ref_um']") --ref-origin $(field $case $r "'%f,%f'%tuple(r['ref_origin'])") \
      --layers $(field $case $r "c['layers']") --threads 3 --held-out $(field $case $r "'crop_'+'_'.join(map(str,c['crop_origin']+c['crop_shape']))")"
    rm=$(field $case $r "r.get('ref_mask','')"); [ -n "$rm" ] && args="$args --ref-mask $rm"
    [ -f $OUT/${name}__${tag}.json ] && continue
    if [ -z "$first" ]; then
      nice -n 19 $PY $S $args --volume $(field $case $r "c['volume']") --ckpt $tag=${CK[$tag]} --out $OUT; first=$name
    else
      nice -n 19 $PY $S $args --pred $tag=$OUT/preds/${first}__$tag.tif --out $OUT
    fi
  done
}
echo "START $(date -Is)"
for tag in rv3 dn; do for c in 0841-w00 0009B-125754 0172-w082 0500P2-371; do echo "== $c $tag $(date -Is)"; run $c $tag; done; done
touch $NC/STAGE1_DONE
for tag in rv3 dn; do for c in 0172-w083 0500P2-377; do echo "== $c $tag $(date -Is)"; run $c $tag; done; done
for c in 0841-w00 0009B-125754 0172-w082 0500P2-371 0172-w083 0500P2-377; do echo "== $c rv2 $(date -Is)"; run $c rv2; done
echo "DONE $(date -Is)"; touch $NC/RUN_DONE
