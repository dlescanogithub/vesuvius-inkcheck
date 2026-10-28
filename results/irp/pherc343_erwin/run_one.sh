#!/bin/bash
# run_one.sh <model> ; reading side = *_reverse ; done-marker out/<model>.DONE
set -euo pipefail
cd /workspace/vesuvius/prize_oct/erwin343; source /workspace/vesuvius/.venv314/bin/activate
export OMP_NUM_THREADS=2 MKL_NUM_THREADS=2 PYTHONPATH=/workspace/vesuvius/villa/vesuvius/src:/workspace/vesuvius/prize_oct/erwin343/pylib
M=$1; O=out; mkdir -p $O tmp_$M; [[ -f $O/$M.DONE ]] && exit 0
C=/workspace/vesuvius/checkpoints
case $M in
 dnative) CK=$C/erwin/dense_native_016000.pth;;
 s42) CK=$C/ink_9um/hybrid_3d2d-seed42/step-075000.pth;;
 s43) CK=$C/ink_9um/hybrid_3d2d-seed43/step-075000.pth;;
esac
if [[ $M != hecate ]]; then
  # render layer index = Erwin k - 20 ; d=+1 window k=26..42 -> 6..22 (end exclusive 23)
  (cd tmp_$M && TMPDIR=$PWD nice -n 15 python -m vesuvius.ink_detection.inference.infer ../render_L.zarr $CK out.tif \
     --overlap 0.5 --blend-mode hann --batch-size 4 --direction both --layer-start 6 --layer-end 23 --no-compile --num-workers 2)
  mv tmp_$M/out.tif $O/$M.tif; mv tmp_$M/out_reverse.tif $O/${M}_reverse.tif
else
  # zc = 32.5 + d = 33.5 in Erwin's frame -> 13.5 in ours
  nice -n 15 python /tmp/erwin/ink/scripts/hecate_prep.py --src render_L.zarr --out tmp_$M/prep.zarr --native-um 8.64 --native-um-z 8.64 --target-um 9.6 --z-center 13.5 --nz 16
  for R in "" --reverse; do SUF=""; [[ -n $R ]] && SUF=_reverse
    (cd tmp_$M && TMPDIR=$PWD nice -n 15 python $C/hecate/hecate.py --checkpoint $C/hecate/hecate_9.6um.pth --input prep.zarr --spacing-um 9.6 --output out$SUF.png --device cpu --batch-size 4 $R)
    mv tmp_$M/out$SUF.png $O/hecate$SUF.png; done
fi
rm -rf tmp_$M; touch $O/$M.DONE
