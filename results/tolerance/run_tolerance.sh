#!/bin/bash
# Node-B tolerance curve on Paris 4 (PASS control): dense_native on each degraded copy, scored with this repo's inkcheck
# (tile-bootstrap CIs). nice 19, PASSIVE, 2 threads, resumable. Old variants reuse their predictions.
cd /workspace/vesuvius
export OMP_WAIT_POLICY=PASSIVE KMP_BLOCKTIME=0 OMP_NUM_THREADS=2 MKL_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2
PY=.venv314/bin/python; REPO=prize_oct/publish/vesuvius-inkcheck; T=$REPO/results/tolerance; SR=prize_oct/study/results
[ -d prize_oct/study/p4_bin4.zarr ] || PYTHONPATH=villa/vesuvius/src nice -n 19 $PY $REPO/study/make_degraded_p4_c.py
score () { # pred variant
  [ -f $T/paris4_$2_dn.json ] || PYTHONPATH=$REPO/src nice -n 19 $PY -m inkcheck $1 control/p4_ref_ds8.jpg --pred-um 9.6 --ref-um 19.2 \
     --ref-origin 512,1536 --workers 2 --out $T/paris4_$2_dn --title "Paris 4 dn, input $2" > $T/paris4_$2_dn.log 2>&1
  echo "$(date -Is) $2 $(grep -h verdict -m1 $T/paris4_$2_dn.json | head -c 80)"
}
score prize_oct/results/p4_ink9_dn.tif original
for v in blur0.5 blur1 blur1.5 blur2 blur3 bin2 noise_sd16 noise_sd32 noise_sd48; do score $SR/p4_${v}_dn.tif $v; done
for v in noise_sd8 bin3 bin4 blur4 noise_sd64; do
  [ -f $T/p4_${v}_dn.tif ] || PYTHONPATH=villa/vesuvius/src nice -n 19 $PY -m vesuvius.ink_detection.inference.infer prize_oct/study/p4_${v}.zarr \
     checkpoints/erwin/dense_native_016000.pth $T/p4_${v}_dn.tif --layer-start 5 --layer-end 22 --direction forward --no-compile --num-workers 1 > $T/p4_${v}_dn.infer.log 2>&1
  score $T/p4_${v}_dn.tif $v
done
touch $T/TOL_DONE
