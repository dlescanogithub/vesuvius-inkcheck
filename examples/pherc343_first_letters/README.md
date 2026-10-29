# PHerc.343 "first letters": reproduce the IRP check end to end

This folder reproduces the inkcheck result for the PHerc.343 first-letters region published by Erwin Nieuwlaar
([Nieuwlaar/pherc343-first-letters](https://github.com/Nieuwlaar/pherc343-first-letters), commit
`e8370f1f88a211166056df62ea6fcfffe4a1063e`, 2026-10-07). Three public 9 µm ink models, run with
[villa](https://github.com/ScrollPrize/villa)'s inference on a native 8.64 µm surface render of his mesh, are scored
against his published 4-model ensemble image with `inkcheck quick`.

**Code only.** No scroll data, renders, ink maps or images derived from them ship here. Everything is downloaded or
regenerated locally into a work folder (default `./work`). Vesuvius Challenge data are CC BY-NC 4.0 with additional
terms, so do not commit or redistribute the downloaded or derived files.

## Versions

| component | version |
|---|---|
| Erwin's mesh, letter boxes, umbilicus, ensemble image | `Nieuwlaar/pherc343-first-letters` @ `e8370f1f` |
| CT volume | `PHerc0343/volumes/20250521140437-8.640um-1.2m-116keV-masked.zarr/0` on the open-data bucket (uint8, uncompressed, 128³ chunks) |
| inference | `ScrollPrize/villa` @ `39a8cf3a124bdd5540ee826e1cb30047c8dc8c85` (2026-10-26), `vesuvius.ink_detection.inference.infer` |
| models | Reader V3 (`reader-v3.pth`) and Reader v2 (`reader-v2-step040000.pth`) by Domenico Russo, [DomRusso2/reader-v2](https://github.com/DomRusso2/reader-v2) (MIT); Erwin Nieuwlaar's `dense_native_016000`, [Nieuwlaar/ink9um-dense-native](https://huggingface.co/Nieuwlaar/ink9um-dense-native) (MIT) |
| scoring | `vesuvius-inkcheck==0.3.0` (PyPI) |

## Steps

Python ≥ 3.10 with `numpy scipy pillow tifffile zarr` for the scripts here; villa's own dependencies (PyTorch etc.)
for step 3. Everything runs on CPU.

```bash
export WORK=$PWD/work
# 1. Erwin's public inputs
git clone https://github.com/Nieuwlaar/pherc343-first-letters
git -C pherc343-first-letters checkout e8370f1f88a211166056df62ea6fcfffe4a1063e
E1=pherc343-first-letters; S=concat_w047-w048_R5B2_z9500-11000

# 2. Native 8.64 um render of his concatenated mesh: 27 layers (k = 20..46, offset k - 32.5 voxels along the outward
#    normal), raw render rows 600:2100, cols 650:5550. Fetches ~1.4k chunks from
#    https://vesuvius-challenge-open-data.s3.amazonaws.com/ (cached in $WORK/cache, resumable).
python render_surface.py $E1/outputs/$S.tifxyz --umb $E1/inputs/umbilicus_PHerc0343.json \
    --out $WORK/render_L.zarr --cache $WORK/cache --procs 3
#    expect: "[normals] frac pointing outward before sign fix 0.9969 sign 1", shape [27, 1500, 4900]

# 3. villa inference, both directions, layers 6..22 (= Erwin's d=+1 window k = 26..42)
git clone https://github.com/ScrollPrize/villa && git -C villa checkout 39a8cf3a124bdd5540ee826e1cb30047c8dc8c85
export VILLA_SRC=$PWD/villa/vesuvius/src PYTHON=python3
./run_infer.sh rv3     /path/to/reader-v3.pth
./run_infer.sh rv2     /path/to/reader-v2-step040000.pth
./run_infer.sh dnative /path/to/dense_native_016000.pth
#    -> $WORK/maps/<model>.tif (forward = blind side) and <model>_reverse.tif (reverse = reading side)

# 4. Reference map from his published ensemble image, on the render grid
python make_ref.py --erwin-repo $E1 --out $WORK/ref

# 5. Score (each run includes the wrong-place negative control)
pip install vesuvius-inkcheck==0.3.0
./score_all.sh rv3_reverse rv3 rv2_reverse rv2 dnative_reverse dnative

# 6. Secondary check: letter-box AUC against 2000 random translations
python lb_auc.py --render $WORK/render_L.zarr --maps $WORK/maps --boxes $E1/inputs/${S}_letter_boxes.json \
    --out $WORK/results/letterbox_auc.json
```

Checkpoints: Reader v2 / V3 are linked from the reader-v2 repository. dense_native is published on Hugging Face as
`weights/dense_native_016000.safetensors`; villa loads `.pth`, and `examples/fetch_paris4_example.py` shows the
safetensors → `.pth` conversion used in this repository.

## Expected output

`make_ref.py`: valid fraction 0.776, ink (o > 0) 18.9 % of valid pixels, letter boxes cover 0.335 of it, ink inside
boxes 42.1 % vs 7.2 % outside, grey check 0 (the overlay inversion is exact). Overlap 4.2 cm².

`inkcheck quick` (192 shift nulls; p = 0.0052, the smallest attainable, for every PASS; every wrong-place control FAILs):

| model | in Erwin's ensemble? | side | verdict | r_bp | null mean / max | z | stroke recall vs chance (strokes) | AUC |
|---|---|---|---|---|---|---|---|---|
| Reader V3 | no | reading (`rv3_reverse`) | **PASS** | 0.632 | 0.048 / 0.126 | 25.9 | 0.51 vs 0.09 (65) | 0.947 |
| Reader V3 | no | blind (`rv3`) | FAIL | 0.105 | 0.047 / 0.133 | | 0.12 vs 0.09 (64) | 0.668 |
| Reader v2 | no | reading | **PASS** | 0.639 | 0.048 / 0.117 | 26.3 | 0.54 vs 0.09 (65) | 0.951 |
| Reader v2 | no | blind | FAIL | 0.088 | 0.043 / 0.108 | | 0.13 vs 0.08 (64) | 0.677 |
| dense_native | **yes** (circular) | reading | PASS | 0.605 | 0.049 / 0.116 | 25.7 | 0.55 vs 0.07 (65) | 0.946 |
| dense_native | yes | blind | FAIL | 0.077 | 0.044 / 0.097 | | 0.11 vs 0.07 (64) | 0.592 |

`lb_auc.py` (letter-box AUC, reading / null 95th percentile / blind; p = 0.001, the smallest attainable with 2000 shifts, for every reading side): Reader V3 0.7068 / 0.6172 / 0.5403,
Reader v2 0.6829 / 0.6028 / 0.5399, dense_native 0.6542 / 0.6005 / 0.4576. Pairwise r between reading-side maps:
dense_native~rv3 0.847, dense_native~rv2 0.869, rv3~rv2 0.929.

Small numerical differences (third decimal) are possible across library versions and CPU thread counts.

## Caveats

- **The reference is a model ensemble, not ground truth.** Erwin's image is the mean z-score of four models
  (dense_native, `ink_9um` s42 and s43, Hecate) on the same scan; a PASS means "agrees with his published ensemble at
  letter level", not "this is ink". dense_native is one of the four, so its row is circular and only a pipeline check.
- **Held-out status.** Reader V3's training list (`triage/reader_v3_train_segments.json` in this repository) covers
  PHerc0139, 0814, 0009B, 0500P2, 0172 and the detached fragment PHerc0343P, but no rolled PHerc. 343 segment, so this
  region is held out for Reader V3 and Reader v2, and neither is in the ensemble. They do share a training scroll
  (PHerc0139) with `ink_9um`, so a shared learned bias cannot be fully excluded; the blind-side FAIL and the
  wrong-place control rule out texture and alignment artefacts, not that.
- **The overlay is inverted, not the raw ensemble.** Opacity is recovered from his PNG as o = (R − B) / 135 (his
  sidecar's overlay rule), clipped at 0, so ensemble scores below his 0.35 display threshold are lost; the cyan
  row lines are masked out.
- **Side matters.** With `--direction both`, villa's forward output is the blind side of this render and the reverse
  output is the reading side. Only the reading side PASSes; the blind side FAILs for all three models, which doubles
  as a sanity check that the result is not texture alone.
- **Data terms.** The render, maps, reference PNGs and results are derived from Vesuvius Challenge data (CC BY-NC
  4.0 + terms). Keep them in `$WORK`, which is not tracked.
