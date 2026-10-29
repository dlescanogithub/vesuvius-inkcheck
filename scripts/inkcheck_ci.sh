#!/usr/bin/env bash
# Run one inkcheck comparison for CI and decide pass/fail from the ink card.
# Used by the composite GitHub Action (action.yml); runnable locally:
#   INKCHECK_PRED=pred.png INKCHECK_REF=ref.png INKCHECK_PRED_UM=9.6 INKCHECK_REF_UM=19.2 scripts/inkcheck_ci.sh
# Environment:
#   INKCHECK_PRED, INKCHECK_REF, INKCHECK_PRED_UM, INKCHECK_REF_UM   required
#   INKCHECK_OUT        output prefix (default inkcheck-out/check)
#   INKCHECK_ARGS       extra check options (word-split), e.g. "--ref-origin 128,128 --workers 2"
#   INKCHECK_CARD_ARGS  provenance options for the ink card (word-split), e.g. "--scroll PHerc0139 --model my-model"
#   INKCHECK_FAIL_ON    FAIL (default: fail the job on FAIL or INVALID), WEAK (also on WEAK), never
#   INKCHECK_CONTROL    1 (default) = also run the wrong-place negative control and include it in the card
#   GITHUB_OUTPUT / GITHUB_STEP_SUMMARY  set by GitHub Actions; optional locally
set -euo pipefail
: "${INKCHECK_PRED:?set INKCHECK_PRED}" "${INKCHECK_REF:?set INKCHECK_REF}"
: "${INKCHECK_PRED_UM:?set INKCHECK_PRED_UM}" "${INKCHECK_REF_UM:?set INKCHECK_REF_UM}"
OUT="${INKCHECK_OUT:-inkcheck-out/check}"
FAIL_ON="${INKCHECK_FAIL_ON:-FAIL}"
CONTROL="${INKCHECK_CONTROL:-1}"
PY="${INKCHECK_PYTHON:-python}"
mkdir -p "$(dirname "$OUT")"
read -r -a EXTRA <<< "${INKCHECK_ARGS:-}"
read -r -a PROV <<< "${INKCHECK_CARD_ARGS:-}"

set +e
inkcheck "$INKCHECK_PRED" "$INKCHECK_REF" --pred-um "$INKCHECK_PRED_UM" --ref-um "$INKCHECK_REF_UM" \
  --out "$OUT" --no-card "${EXTRA[@]}" "${PROV[@]}"
rc=$?
set -e
if [ "$rc" -gt 2 ]; then echo "inkcheck crashed (exit $rc)" >&2; exit "$rc"; fi

CTRL_ARGS=()
if [ "$CONTROL" = "1" ]; then
  # same prediction rolled to the wrong place (inkcheck.quick.wrong_place); it must FAIL
  "$PY" - "$INKCHECK_PRED" "$OUT.control_pred.npy" <<'PY'
import sys, numpy as np
from inkcheck.io import load_map
from inkcheck.quick import wrong_place
np.save(sys.argv[2], wrong_place(load_map(sys.argv[1])))
PY
  set +e
  inkcheck "$OUT.control_pred.npy" "$INKCHECK_REF" --pred-um "$INKCHECK_PRED_UM" --ref-um "$INKCHECK_REF_UM" \
    --out "$OUT.control" --no-card --title "wrong_place control" "${EXTRA[@]}" > "$OUT.control.log"
  crc=$?
  set -e
  if [ "$crc" -gt 2 ]; then echo "control run crashed (exit $crc)" >&2; exit "$crc"; fi
  CTRL_ARGS=(--control "$OUT.control.json")
fi

inkcheck card "$OUT.json" --out "$OUT" "${CTRL_ARGS[@]}" "${PROV[@]}"
inkcheck report --validate "$OUT.card.json"
VERDICT=$("$PY" -c 'import json,sys; print(json.load(open(sys.argv[1]))["verdict"]["final"])' "$OUT.card.json")
echo "inkcheck final verdict: $VERDICT"

if [ -n "${GITHUB_OUTPUT:-}" ]; then
  { echo "verdict=$VERDICT"; echo "card=$OUT.card.json"; echo "card-md=$OUT.card.md"; } >> "$GITHUB_OUTPUT"
fi
if [ -n "${GITHUB_STEP_SUMMARY:-}" ]; then cat "$OUT.card.md" >> "$GITHUB_STEP_SUMMARY"; fi

case "$FAIL_ON:$VERDICT" in
  never:*) exit 0 ;;
  *:INVALID|*:FAIL) echo "::error::inkcheck verdict $VERDICT" >&2; exit 1 ;;
  WEAK:WEAK) echo "::error::inkcheck verdict WEAK (fail-on WEAK)" >&2; exit 1 ;;
  *) exit 0 ;;
esac
