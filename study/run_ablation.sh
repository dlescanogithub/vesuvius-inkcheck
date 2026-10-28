#!/bin/bash
# Resolution/SNR ablation on Paris-4: dense_native inference on each degraded volume, then inkcheck.
# CPU-light: 2 threads, 1 worker, nice 15.
cd "${WS:-.}"; export PYTHONPATH=${VILLA_SRC:-villa/vesuvius/src} OMP_NUM_THREADS=2 MKL_NUM_THREADS=2
R=prize_oct/study/results; mkdir -p $R
for v in ${VARIANTS:-blur1 blur2 blur3 bin2 noise_sd16}; do
  t0=$(date +%s)
  [ -f $R/p4_${v}_dn.tif ] || nice -n 15 .venv314/bin/python -m vesuvius.ink_detection.inference.infer prize_oct/study/p4_${v}.zarr \
     checkpoints/erwin/dense_native_016000.pth $R/p4_${v}_dn.tif --layer-start 5 --layer-end 22 --direction forward --no-compile --num-workers 1 > $R/p4_${v}_dn.log 2>&1
  t1=$(date +%s)
  nice -n 15 prize_oct/.venv/bin/inkcheck $R/p4_${v}_dn.tif control/p4_ref_ds8.jpg --pred-um 9.6 --ref-um 19.2 --ref-origin 512,1536 \
     --workers 2 --out $R/paris4_${v}_dn --title "Paris 4 dn, input $v" > $R/paris4_${v}_dn.inkcheck.log 2>&1
  echo "$(date '+%F %T') $v infer $((t1-t0))s inkcheck $(( $(date +%s)-t1 ))s $(tail -2 $R/paris4_${v}_dn.inkcheck.log | head -1)" >> $R/ablation_log.txt
done
echo DONE >> $R/ablation_log.txt
