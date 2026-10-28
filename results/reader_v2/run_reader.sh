#!/bin/bash
# Reader v2 / Reader V3 / d9v4C (+ s42, dn baselines) on Reader v2's two held-out PHerc0343P segments and Paris 4.
# CPU, 4 threads, nice >= 10. Resumable (score.py skips existing predictions).
cd /workspace/vesuvius
export PYTHONPATH=/workspace/vesuvius/prize_oct/publish/vesuvius-inkcheck/src:/workspace/vesuvius/villa/vesuvius/src
export OMP_WAIT_POLICY=PASSIVE KMP_BLOCKTIME=0
export VILLA_PY=/workspace/vesuvius/.venv314/bin/python OMP_NUM_THREADS=4 MKL_NUM_THREADS=4
PY=.venv314/bin/python; S=prize_oct/publish/vesuvius-inkcheck/bench/score.py
OUT=prize_oct/results/reader_v2; C=checkpoints
R="--ckpt rv2=$C/reader/reader-v2-step040000.pth --ckpt rv3=$C/reader/reader-v3.pth"
D="--ckpt d9v4C=$C/reader/d9v4C_ft-006000.pth"
B="--ckpt s42=$C/ink_9um/hybrid_3d2d-seed42/step-075000.pth --ckpt dn=$C/erwin/dense_native_016000.pth"
NOTE343="--note d9v4C=LEAK:segment_in_d9v4C_train.txt --held-out reader-v2-holdout(not_in_rv2/rv3_training)"
run343 () { # seg tag ckpts...
  seg=$1; id=${seg:0:14}; shift
  sd=data_raw/PHerc0343P/segments/$seg
  nice -n 10 $PY $S --name 343P-$id --scroll PHerc0343P --volume $sd/surface-volumes/8.64um-1.2m-116keV-volume-20250521134555.zarr \
    --ref $(ls $sd/ink-detection/*new_canon*.tif) --mask $OUT/343P_${id}_mask_layer15.png --um 8.64 --ref-um 2.215 \
    --layers 7:24 --threads 4 $NOTE343 "$@" --out $OUT
}
runp4 () {
  nice -n 10 $PY $S --name paris4-20231005123336 --scroll PHercParis4 --volume control/p4_ctrl_9.6um.zarr \
    --ref control/p4_ref_ds8.jpg --um 9.6 --ref-um 19.2 --ref-origin 512,1536 --layers 5:22 --threads 4 \
    --held-out "w04/w08-not-in-ink_9um/rv2/rv3/d9v4C-train-lists" "$@" --out $OUT
}
echo "RESTART (OMP_WAIT_POLICY=PASSIVE) $(date -Is)"
runp4 $R $D --pred s42=control/p4_ink9_s42.tif --pred dn=prize_oct/results/p4_ink9_dn.tif
for seg in 20250904233748-0_b2 20250905172054-1_b2; do run343 $seg $R; done
for seg in 20250904233748-0_b2 20250905172054-1_b2; do run343 $seg $D; done
for seg in 20250904233748-0_b2 20250905172054-1_b2; do run343 $seg $B; done
echo "DONE $(date -Is)"
