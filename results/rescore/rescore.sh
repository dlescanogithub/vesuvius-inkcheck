#!/bin/bash
# Re-run inkcheck (same settings, same seed => same point estimates) on every existing prediction behind the cards, to add
# the tile-bootstrap CIs. Outputs results/rescore/<group>/<name>.json; original JSONs are left untouched.
# nice 19, PASSIVE, 2 threads, one job at a time, resumable.
cd /workspace/vesuvius
export OMP_WAIT_POLICY=PASSIVE KMP_BLOCKTIME=0 OMP_NUM_THREADS=2 MKL_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2
REPO=prize_oct/publish/vesuvius-inkcheck; O=$REPO/results/rescore; PY=.venv314/bin/python
export PYTHONPATH=$REPO/src
while [ ! -f $REPO/results/negctrl/CTRL_DONE ]; do sleep 30; done
ic () { # out pred ref args...
  out=$1; shift; mkdir -p $(dirname $O/$out)
  [ -f $O/$out.json ] || nice -n 19 $PY -m inkcheck "$@" --workers 2 --out $O/$out > $O/$out.log 2>&1
  echo "$(date -Is) $out $(grep -m1 '"verdict"' $O/$out.json)"
}
RP=prize_oct/results/reader_v2/preds
for t in rv2 rv3 d9v4C; do ic reader_v2/paris4-20231005123336__$t $RP/paris4-20231005123336__$t.tif control/p4_ref_ds8.jpg --pred-um 9.6 --ref-um 19.2 --ref-origin 512,1536; done
ic reader_v2/paris4-20231005123336__dn prize_oct/results/p4_ink9_dn.tif control/p4_ref_ds8.jpg --pred-um 9.6 --ref-um 19.2 --ref-origin 512,1536
ic reader_v2/paris4-20231005123336__s42 control/p4_ink9_s42.tif control/p4_ref_ds8.jpg --pred-um 9.6 --ref-um 19.2 --ref-origin 512,1536
for seg in 20250904233748-0_b2 20250905172054-1_b2; do id=${seg:0:14}; REF=$(ls data_raw/PHerc0343P/segments/$seg/ink-detection/*new_canon*.tif)
  for t in rv2 rv3 d9v4C s42 dn; do ic reader_v2/343P-${id}__$t $RP/343P-${id}__$t.tif "$REF" --pred-um 8.64 --ref-um 2.215 --mask prize_oct/results/reader_v2/343P_${id}_mask_layer15.png; done; done
REF343=$(ls data_raw/PHerc0343P/segments/20250511003658-tifxyz/ink-detection/*new_canon*.tif)
for m in dn kl s42 s43 soup; do ic controls/343P_${m}_8.64um preds/343P_ctrl/${m}_w7_forward.tif "$REF343" --pred-um 8.64 --ref-um 2.215 --mask prize_oct/results/343P_mask_layer15.png; done
SR=prize_oct/study/results
for j in dn_w5 kl_w5 s42_w5 s43_w5 soup_w5 dn_w4 dn_w6; do ic study/343P_from2um_$j $SR/343P_from2um_$j.tif "$REF343" --pred-um 8.86 --ref-um 2.215 --mask $SR/343P_from2um_mask.png; done
touch $O/RESCORE_DONE
