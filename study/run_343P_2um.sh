#!/bin/bash
# Same-segment two-scan control: PHerc0343P 20250511003658 from the 2.215 um / 111 keV scan pooled to 8.86 um
# vs our native 8.64 um / 116 keV render. Same checkpoints, same inkcheck settings.  2 threads, nice 15.
cd "${WS:-.}"; export PYTHONPATH=${VILLA_SRC:-villa/vesuvius/src} OMP_NUM_THREADS=2 MKL_NUM_THREADS=2
while [ -n "${WAITPID:-}" ] && kill -0 $WAITPID 2>/dev/null; do sleep 10; done
declare -A CK=( [s42]=checkpoints/ink_9um/hybrid_3d2d-seed42/step-075000.pth [s43]=checkpoints/ink_9um/hybrid_3d2d-seed43/step-075000.pth [soup]=checkpoints/erwin/soup42_last4.pth [dn]=checkpoints/erwin/dense_native_016000.pth [kl]=checkpoints/klavis/dense9um-w016excluded-step075000.pth )
V=prize_oct/study/343P_from2um_8.86um.zarr; R=prize_oct/study/results; REF=$(ls data_raw/PHerc0343P/segments/20250511003658-tifxyz/ink-detection/*new_canon*.tif)
[ -f $R/343P_from2um_mask.png ] || prize_oct/.venv/bin/python -c "
import sys; sys.path.insert(0,'tools'); from zread import read_local; from PIL import Image; import numpy as np
v=read_local('$V/0'); Image.fromarray(((v[13]>0)*255).astype(np.uint8)).save('$R/343P_from2um_mask.png')"
for job in ${JOBS:-dn:5 kl:5 s42:5 dn:4 dn:6 s43:5 soup:5}; do m=${job%:*}; w=${job#*:}; o=$R/343P_from2um_${m}_w$w
  t0=$(date +%s)
  [ -f $o.tif ] || nice -n 15 .venv314/bin/python -m vesuvius.ink_detection.inference.infer $V ${CK[$m]} $o.tif --layer-start $w --layer-end $((w+17)) \
      --direction forward --no-compile --num-workers 1 > $o.log 2>&1
  t1=$(date +%s)
  nice -n 15 prize_oct/.venv/bin/inkcheck $o.tif "$REF" --pred-um 8.86 --ref-um 2.215 --mask $R/343P_from2um_mask.png --workers 2 \
      --out $o --title "PHerc0343P 20250511003658: $m w$w on 2.215um/111keV scan pooled to 8.86um" > $o.inkcheck.log 2>&1
  echo "$(date '+%F %T') $m w$w infer $((t1-t0))s inkcheck $(( $(date +%s)-t1 ))s $(tail -2 $o.inkcheck.log | head -1)" >> $R/343P_2um_log.txt
done; echo DONE >> $R/343P_2um_log.txt
