#!/bin/bash
# inkcheck with the camera (IR-traced letters, DomRusso2/ir-truth-9um @7e96b969) as reference, on 343P segment 20250511003658.
# Same predictions as the 343P controls; second, independent reference for the 343P card. nice 19, PASSIVE, 2 threads.
cd /workspace/vesuvius
export OMP_WAIT_POLICY=PASSIVE KMP_BLOCKTIME=0 OMP_NUM_THREADS=2 MKL_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2
REPO=prize_oct/publish/vesuvius-inkcheck; O=$REPO/results/irtruth/inkcheck; PY=.venv314/bin/python; IR=data_raw/ir_truth/repo
export PYTHONPATH=$REPO/src
ic () { out=$1; pred=$2
  [ -f $O/$out.json ] || nice -n 19 $PY -m inkcheck $pred $IR/data/ink_traced_full.png --pred-um 8.64 --ref-um 8.64 --mask $IR/data/valid.png --workers 2 --out $O/$out > $O/$out.log 2>&1
  echo "$(date -Is) $out $(grep -m1 '"verdict"' $O/$out.json)"; }
ic team2.2um_vs_IR $IR/maps/team-2.2um-model-map.png
for m in dn kl s43 soup s42; do ic ${m}_vs_IR preds/343P_ctrl/${m}_w7_forward.tif; done
ic rv3_vs_IR $IR/maps/reader-v3.png
touch $O/IRIC_DONE
