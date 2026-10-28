#!/bin/bash
# Reproduce the two control checks (paths are relative to the vesuvius workspace).
# Paris 4: held-out segment 20231005123336, 9.6 um pooled from the 2.4 um scan.
# 343P:    segment 20250511003658 rendered from the native 8.64 um / 116 keV scan.
set -eu
export OMP_NUM_THREADS=${OMP_NUM_THREADS:-2}
IC="nice -n 15 ${INKCHECK:-inkcheck}"
OUT=${OUT:-prize_oct/results}
REF343=$(ls data_raw/PHerc0343P/segments/20250511003658-tifxyz/ink-detection/*new_canon*.tif)
MASK343=$OUT/343P_mask_layer15.png   # not shipped (scroll data): save (layer 15 of the 8.64 um render > 0) as PNG

$IC control/p4_ink9_s42.tif control/p4_ref_ds8.jpg --pred-um 9.6 --ref-um 19.2 --ref-origin 512,1536 \
    --out $OUT/paris4_s42_9.6um --title "Paris 4 20231005123336 (held out): ink_9um seed42 @9.6um vs new_canon ds8"
[ -f prize_oct/results/p4_ink9_dn.tif ] && $IC prize_oct/results/p4_ink9_dn.tif control/p4_ref_ds8.jpg --pred-um 9.6 --ref-um 19.2 \
    --ref-origin 512,1536 --out $OUT/paris4_dn_9.6um --title "Paris 4 20231005123336 (held out): dense_native @9.6um vs new_canon ds8"
for m in dn kl s42 s43 soup; do
  $IC preds/343P_ctrl/${m}_w7_forward.tif "$REF343" --pred-um 8.64 --ref-um 2.215 --mask $MASK343 \
      --out $OUT/343P_${m}_8.64um --title "PHerc0343P 20250511003658: $m @8.64um (native scan) vs new_canon 2.215um" || true
done
# same comparison on the Paris-4 analysis grid (19.2 um) for a like-for-like comparison
$IC preds/343P_ctrl/dn_w7_forward.tif "$REF343" --pred-um 8.64 --ref-um 2.215 --mask $MASK343 --analysis-um 19.2 \
    --out $OUT/343P_dn_8.64um_grid19.2 --title "PHerc0343P: dn @8.64um vs new_canon, analysed on a 19.2um grid" || true
