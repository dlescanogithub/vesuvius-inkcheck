#!/bin/bash
# Score the three negative controls (all must FAIL). nice 19, PASSIVE, 2 threads.
cd "$(dirname "$0")"; R=/workspace/vesuvius
export OMP_WAIT_POLICY=PASSIVE OMP_NUM_THREADS=2 MKL_NUM_THREADS=2 PYTHONPATH=../../src
PY=$R/.venv314/bin/python; P=$R/prize_oct/results/p4_ink9_dn.tif
WO=$($PY -c "import json;print('%d,%d'%tuple(json.load(open('controls.json'))['wrongregion_origin']))")
nice -n 19 $PY -m inkcheck $P $R/control/p4_ref_ds8.jpg --pred-um 9.6 --ref-um 19.2 --ref-origin $WO --workers 2 --out ctrl_wrongregion --title "NEG CONTROL: wrong region" > ctrl_wrongregion.log 2>&1
nice -n 19 $PY -m inkcheck $P ctrl_tileshuffle_ref.png --pred-um 9.6 --ref-um 19.2 --ref-origin 0,0 --workers 2 --out ctrl_tileshuffle --title "NEG CONTROL: 2 mm tiles of the reference shuffled" > ctrl_tileshuffle.log 2>&1
nice -n 19 $PY -m inkcheck ctrl_phasenoise_pred.tif $R/control/p4_ref_ds8.jpg --pred-um 9.6 --ref-um 19.2 --ref-origin 512,1536 --workers 2 --out ctrl_phasenoise --title "NEG CONTROL: phase-randomised prediction" > ctrl_phasenoise.log 2>&1
# positive twin: the same prediction against the true unshuffled window (cut exactly like the shuffled one)
nice -n 19 $PY -m inkcheck $P $R/control/p4_ref_ds8.jpg --pred-um 9.6 --ref-um 19.2 --ref-origin 512,1536 --workers 2 --out pos_paris4_dn --title "POSITIVE twin: Paris 4 dn" > pos_paris4_dn.log 2>&1
$PY make_controls_b.py && nice -n 19 $PY -m inkcheck $P ctrl_tileshuffle_rot_ref.png --pred-um 9.6 --ref-um 19.2 --ref-origin 0,0 --workers 2 --out ctrl_tileshuffle_rot --title "NEG CONTROL: 2 mm tiles deranged and rotated 90/270" > ctrl_tileshuffle_rot.log 2>&1
touch CTRL_DONE
