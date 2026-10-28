#!/bin/bash
# ScrollGT flagship (Paris 4 20231210121321 = ink_9um "phercparis4-w06"): fetch, CPU inference (Reader V3, seed42),
# score against ScrollGT's registered human label. Niced, 3 threads, writes SCROLLGT_DONE.
cd /workspace/vesuvius
export PYTHONPATH=/workspace/vesuvius/prize_oct/publish/vesuvius-inkcheck/src:/workspace/vesuvius/villa/vesuvius/src
export OMP_WAIT_POLICY=PASSIVE KMP_BLOCKTIME=0 OMP_NUM_THREADS=3 MKL_NUM_THREADS=3 VILLA_PY=/workspace/vesuvius/.venv314/bin/python
R=prize_oct/publish/vesuvius-inkcheck; O=$R/results/scrollgt; PY=.venv314/bin/python; C=checkpoints
mkdir -p $O; D=data_raw/scrollgt
nice -n 19 $PY $R/examples/scrollgt/fetch_flagship.py /tmp/scrollgt $D || exit 1
cp $D/gt_crop.png $D/crop.json $O/ 2>/dev/null
LEAK="TRAIN-EXPOSED:20231210121321_is_ink_9um_phercparis4-w06,in_training_config_of_rv3/s42/dn"
nice -n 19 $PY $R/bench/score.py --name scrollgt-flagship-20231210121321 --scroll PHercParis4 \
  --volume $D/flagship_9.6um.zarr --ref $D/gt_crop.png --ref-threshold 127 --um 9.6 --ref-um 9.6 --layers 5:22 --threads 3 \
  --held-out "$LEAK" --ckpt rv3=$C/reader/reader-v3.pth --ckpt s42=$C/ink_9um/hybrid_3d2d-seed42/step-075000.pth --out $O
echo "SCROLLGT_DONE $(date -Is)"; touch $O/SCROLLGT_DONE
