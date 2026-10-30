#!/bin/bash
# Re-score 0841-w00-map rv3 (scored before the bootstrap existed) from its saved prediction; same settings. nice 19, 2 threads.
#
# --ref-origin 333.04,333.13 is specific to THESE two inputs (issue #1); it is not an origin for the full canvas.
#   PRED = 0841-w00-map__rv3.tif: rv3 on the 2560 x 2560 held-out crop of the 9.366 um w00 volume at canvas
#          y,x = 512,1536 (data_raw/newcases/0841_w00.zarr/crop.json; --held-out crop_512_1536_2560_2560).
#   REF  = refs/0841-w00__map.png: the 16460 x 18560 PHerc0841 map cut by results/newcases/prep_refs.py to that crop
#          plus a 0.8 mm margin. ref_um = 9.366 * 4220 / 16460 = 2.4012 um (3.9005 ref px per pred px); margin =
#          round(800 / 2.4012) = 333 px; the crop starts at 512 * 3.9005 = 1997.04 -> 1997 - 333 = 1664 (y) and
#          1536 * 3.9005 = 5991.13 -> 5991 - 333 = 5658 (x), so pred (0,0) sits at 1997.04 - 1664 = 333.04,
#          5991.13 - 5658 = 333.13 in REF pixels (written to results/newcases/cases.json).
# With a full-canvas (4220 x 4760) w00 render scored against the full 0841_w00_map.tif, use --ref-origin 0,0. Passing
# 333,333 there offsets the pair by ~0.8 mm per axis, outside the +-0.5 mm search, so the best shift lands on the edge.
# Both setups find the same residual shift, ~56 um (6 coarse px): the plain-scale canvas pairing offset (villa#2243).
# The prediction and the cropped reference are scroll-derived and not in this repo (.gitignore); regenerate them with
# results/newcases/prep_refs.py and results/newcases/run_new.sh.
cd /workspace/vesuvius
REPO=prize_oct/publish/vesuvius-inkcheck
while [ ! -f $REPO/results/irtruth/inkcheck/IRIC_DONE ]; do sleep 30; done
export PYTHONPATH=$REPO/src OMP_WAIT_POLICY=PASSIVE KMP_BLOCKTIME=0 OMP_NUM_THREADS=2 MKL_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2
NC=$REPO/results/newcases
nice -n 19 .venv314/bin/python $REPO/bench/score.py --name 0841-w00-map --scroll 0841 --um 9.366 --ref $NC/refs/0841-w00__map.png \
  --ref-um 2.401246658566221 --ref-origin 333.0426540284359,333.12796208530744 --layers 5:22 --threads 2 \
  --held-out crop_512_1536_2560_2560 --pred rv3=$NC/scores/preds/0841-w00-map__rv3.tif --out $REPO/results/rescore/newcases
touch $REPO/results/rescore/R0841_DONE
