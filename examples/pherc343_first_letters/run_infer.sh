#!/bin/bash
# run_infer.sh <model> <checkpoint.pth>
# Runs villa's ink-detection inference (villa commit 39a8cf3, github.com/ScrollPrize/villa) on the rendered surface,
# both directions, on layers 6..22 of the 27-layer render (= Erwin's d=+1 window). Writes
#   $WORK/maps/<model>.tif          forward direction = blind side
#   $WORK/maps/<model>_reverse.tif  reverse direction = reading side
# Environment:
#   WORK       working folder (default ./work); the render must be at $WORK/render_L.zarr
#   VILLA_SRC  path to villa's vesuvius/src at 39a8cf3 (added to PYTHONPATH)
#   PYTHON     python with villa's dependencies (torch, ...), default python3
#   THREADS    CPU threads (default 3)
set -euo pipefail
if [[ ${1:-} == -h || ${1:-} == --help ]]; then sed -n '2,11p' "$0"; exit 0; fi
if [[ $# -ne 2 ]]; then sed -n '2,11p' "$0" >&2; exit 1; fi
T=$1; CK=$(realpath "$2")
WORK=$(realpath "${WORK:-work}"); PY=${PYTHON:-python3}; : "${VILLA_SRC:?set VILLA_SRC to the vesuvius/src folder of villa}"
[[ -f $WORK/maps/$T.tif && -f $WORK/maps/${T}_reverse.tif ]] && { echo "$T already done"; exit 0; }
mkdir -p "$WORK/maps" "$WORK/tmp_$T"
export OMP_NUM_THREADS=${THREADS:-3} MKL_NUM_THREADS=${THREADS:-3} PYTHONPATH=$(realpath "$VILLA_SRC")${PYTHONPATH:+:$PYTHONPATH}
(cd "$WORK/tmp_$T" && TMPDIR=$PWD "$PY" -m vesuvius.ink_detection.inference.infer "$WORK/render_L.zarr" "$CK" out.tif \
   --overlap 0.5 --blend-mode hann --batch-size 4 --direction both --layer-start 6 --layer-end 23 --no-compile --num-workers 1)
mv "$WORK/tmp_$T/out.tif" "$WORK/maps/$T.tif"; mv "$WORK/tmp_$T/out_reverse.tif" "$WORK/maps/${T}_reverse.tif"
echo "$T done"
