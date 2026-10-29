#!/bin/bash
# score_all.sh <map-name> [...]   e.g.  score_all.sh rv3_reverse rv3 rv2_reverse rv2 dnative_reverse dnative
# Scores each villa map ($WORK/maps/<name>.tif) against Erwin's published ensemble opacity with `inkcheck quick`
# (pip install vesuvius-inkcheck==0.3.0). Reading side = <model>_reverse, blind side = <model>.
# Each run includes inkcheck's built-in wrong-place negative control (node N), which must FAIL.
# Environment: WORK (default ./work; reference PNGs from make_ref.py in $WORK/ref), INKCHECK (default: inkcheck), WORKERS (default 3)
set -uo pipefail
if [[ ${1:-} == -h || ${1:-} == --help ]]; then sed -n '2,6p' "$0"; exit 0; fi
if [[ $# -eq 0 ]]; then sed -n '2,6p' "$0" >&2; exit 1; fi
WORK=${WORK:-work}; IC=${INKCHECK:-inkcheck}; mkdir -p "$WORK/results"
for t in "$@"; do
  $IC quick "$WORK/maps/$t.tif" "$WORK/ref/erwin_opacity.png" --pred-um 8.64 --ref-um 8.64 --mask "$WORK/ref/valid.png" \
     --workers "${WORKERS:-3}" --out "$WORK/results/$t" --json > "$WORK/results/$t.stdout.txt" 2>&1
  echo "$t exit $? (0 = PASS, 2 = FAIL)"
done
