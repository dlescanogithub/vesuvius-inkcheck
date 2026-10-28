#!/bin/bash
# Re-score 0841-w00-map rv3 (scored before the bootstrap existed) from its saved prediction; same settings. nice 19, 2 threads.
cd /workspace/vesuvius
REPO=prize_oct/publish/vesuvius-inkcheck
while [ ! -f $REPO/results/irtruth/inkcheck/IRIC_DONE ]; do sleep 30; done
export PYTHONPATH=$REPO/src OMP_WAIT_POLICY=PASSIVE KMP_BLOCKTIME=0 OMP_NUM_THREADS=2 MKL_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2
NC=$REPO/results/newcases
nice -n 19 .venv314/bin/python $REPO/bench/score.py --name 0841-w00-map --scroll 0841 --um 9.366 --ref $NC/refs/0841-w00__map.png \
  --ref-um 2.401246658566221 --ref-origin 333.0426540284359,333.12796208530744 --layers 5:22 --threads 2 \
  --held-out crop_512_1536_2560_2560 --pred rv3=$NC/scores/preds/0841-w00-map__rv3.tif --out $REPO/results/rescore/newcases
touch $REPO/results/rescore/R0841_DONE
