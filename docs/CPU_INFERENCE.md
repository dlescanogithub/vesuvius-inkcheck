# Running `scrollprize/ink_9um` ink detection on a CPU only machine — measured numbers

This guide is for people who **don't have a GPU**. Every timing below was measured on one machine and copied from its run logs, not estimated. The logs are `phase2_log.txt` and `control/p4_ink9_s42.log`, and all times are wall-clock.

**Machine:** an 8 vCPU "Intel Xeon Processor" VM with 1 thread per core and 15 GB RAM. No GPU; the log says `Using CPU device`. Python 3.14, with the villa `vesuvius` package from `villa/vesuvius/src`.

## 1. Command

```bash
export PYTHONPATH=/path/to/villa/vesuvius/src
export OMP_NUM_THREADS=4 MKL_NUM_THREADS=4      # see section 3 - this matters
python -m vesuvius.ink_detection.inference.infer \
    <surface_volume.zarr> <checkpoint.pth> <out.tif> \
    --layer-start 7 --layer-end 24 \            # 17 layers; --layer-end is EXCLUSIVE
    --direction forward --no-compile --num-workers 2
```

- `--no-compile` skips `torch.compile`. On CPU, the compile warm-up is not worth it for one segment.
- `--layer-end` is **exclusive**. Our first run passed `w+16` and silently got 16 layers instead of the 17 the model expects (logged at 15:31:07). Use `w+17`.
- The model was trained near 9.6 µm. Feed it surface volumes at about 9 µm, such as the native 8.64 µm scans. For 2.4 µm data, use OME-Zarr pyramid level 2 in XY and mean-pool 4× in depth (that is what we did for the Paris 4 control).
- Outputs are uint8 with label smoothing 0.5. To read them as probabilities, use `clip((v/255 − 0.25)/0.5, 0, 1)`.

## 2. Measured timings (single model, 17 layers, patch 128, stride 64)

| Run | Grid | Masked area | Wall time | s / cm² |
|---|---|---|---|---|
| Paris 4 control crop, seed42 (529 patches) | 1536×1536 @ 9.6 µm | 2.17 cm² (full crop) | **48.7 s** (user 3m42.8s) | 22 |
| PHerc0343P 20250511003658, s42 | 3440×2060 @ 8.64 µm | 3.27 cm² | 249 s | 76 |
| PHerc0343P, s43 | 〃 | 3.27 cm² | 206 s | 63 |
| PHerc0343P, dense_native (Erwin) | 〃 | 3.27 cm² | 195 s | 60 |
| PHerc0343P, klavis dense9um | 〃 | 3.27 cm² | 174 s | 53 |
| PHerc0343P, soup (4-checkpoint average) | 〃 | 3.27 cm² | 512 s | 157 |
| PHerc0800 auto_grown_…213516907, dn | 2160×2240 | 1.70 cm² | 128 s | 75 |
| PHerc0800 …220042762, dn | 2040×2000 | 1.58 cm² | 62 s | 39 |
| PHerc0800 …220955262, dn | 2100×2100 | 1.53 cm² | 102 s | 67 |
| PHerc0800 …222030940, dn | 2580×2580 | 2.34 cm² | 143 s | 61 |
| PHerc0800 …225813045, dn | 2300×2260 | 1.83 cm² | 128 s | 70 |
| PHerc0800 …010146642, dn | 980×980 | 0.36 cm² | 37 s | 103 (start-up dominated) |
| PHerc1203 auto_grown_…230830031, dn | 4640×5360 | 14.67 cm² | 756 s | 52 |
| PHerc1203 …231446965, dn | 5200×5200 | 11.41 cm² | 759 s | 67 |
| PHerc1203 …221856743, dn | 5060×4520 | 10.66 cm² | 376 s | 35 |
| PHerc1203 …104534929, dn | 4320×4320 | 7.80 cm² | 248 s | 32 |
| PHerc1203 …230118636, dn | 3280×4260 | 7.37 cm² | 216 s | 29 |
| PHerc1203 …165041633, dn | – | 4.36 cm² (p>0 area) | 203 s | 47 |
| PHerc1203 …222256117, dn | – | 7.07 cm² (p>0 area) | 213 s | 30 |
| PHerc1203 …000321811, dn | – | 6.91 cm² (p>0 area) | 228 s | 33 |
| PHerc1203 …230830030, dn | – | 5.73 cm² (p>0 area) | 319 s | 56 |
| Paris 4 crop, dense_native, **2 threads, 1 worker, nice 15** (sharing the box) | 1536×1536 @ 9.6 µm | 2.17 cm² | 198 s* | 91 |
| Paris 4 degraded variants ×9, dense_native, **2 threads, 1 worker** | 1536×1536 @ 9.6 µm | 2.17 cm² | 80–89 s each | 37–41 |
| PHerc0343P from 2.215 µm scan pooled to 8.86 µm, dense_native, **2 threads** | 3355×2005 | ≈4.3 cm² | 221 s | ≈51 |

How to read the table:
- The **masked area** is the papyrus area. The time scales with the grid's bounding box, not only with that area.
- Many runs shared the box with other jobs, such as surface rendering or a second inference. That is why the s/cm² values spread from **about 22 to 76 s/cm² per model**.
- Rough planning number on 8 cores: **about 1 minute per cm² per checkpoint**, plus about 10–15 s of start-up per run.
- Five-model ensembles cost 5× that. The soup model was about 2.5× slower than the others in our run, and we did not investigate why.
- \* this run overlapped with a 4-thread Phase 2 job and a second inference; the same input took 80–89 s at 2 threads once the box was quieter. **With only 2 threads a job runs at ~40 s/cm²**, not much slower than with 4–8, so on a shared 8-core box several 2-thread jobs in parallel give the best throughput.
- inkcheck itself takes 18–20 s for a 2 cm² check at 19.2 µm, and 80–130 s for a 3–4 cm² check at 8.6–8.9 µm (2 threads).
- Rendering a tifxyz surface volume (31 layers, 8.64 µm) took 26–96 s per segment on the same box (phase2_log.txt, 15:33–15:46).

## 3. The OMP_NUM_THREADS lesson (cost us 23 minutes)

PyTorch, MKL and the DataLoader workers each start their own thread pools. When several jobs run at once with the default thread count (all cores per process), they **oversubscribe** the CPU.

In our case, one control run that should take about 4 minutes was still running after **23 minutes**. The log entry from 15:54:36 reads: "killed s42 control run (CPU oversubscription, 23 min); restart with OMP_NUM_THREADS=4". After the restart with `OMP_NUM_THREADS=4 MKL_NUM_THREADS=4 --num-workers 2`, the same job finished in **249 s**.

Rules of thumb:
- Set `OMP_NUM_THREADS` × (number of concurrent jobs) ≤ physical cores.
- Keep `--num-workers` small (2).
- Use `nice` for background jobs.
- When two jobs must share a box, give each half the cores rather than letting both claim all of them.

## 4. Resolution caveat — check before you trust a map

A significant global correlation does **not** mean the model reads letters. We checked this with [`inkcheck`](../README.md), comparing our CPU predictions with the published `new_canon` predictions of the same segments. Full numbers are in `../results/` (Paris 4: verdict only; scores withheld under the PHercParis4 publication reservation until 2027-06-25).

| Control | Model | Analysis grid | band-pass r (null mean ± sd, p) | raw r | AUC | stroke recall (chance) | Verdict |
|---|---|---|---|---|---|---|---|
| Paris 4 20231005123336, 9.6 µm pooled from 2.4 µm / 78 keV, **segment not in ink_9um training** | seed42 | 19.2 µm | withheld | withheld | withheld | withheld | **PASS** |
| PHerc0343P 20250511003658, **native 8.64 µm / 116 keV** | dense_native | 8.64 µm | 0.277 (0.054 ± 0.022, p=0.005, z=10) | 0.397 | 0.770 | 16 % (6 %) | **WEAK** |

**Phase 2 aggregate** (taken from `preds/phase2_summary.json`; dense_native, 4 threads, shared box):
- PHerc1203: 22 segments, 112.1 cm² in 4803 s, which is **43 s/cm²**. The total is 80 CPU-wall minutes.
- PHerc0800: 6 segments, 8.0 cm² in 600 s, which is 75 s/cm². Small segments carry a higher per-cm² overhead.
- Phase 2 measures *analysed* (papyrus-mask) area, which is smaller than the p>0 area in the rows above.

### All checkpoints and the follow-up study (details: `RESOLUTION_STUDY.md`)

| run | inference (2 threads) | inkcheck |
|---|---|---|
| 343P 2.2 µm→8.86 µm, 7 runs (dn w4/5/6, kl, s42, s43, soup) | 194–340 s each (≈4.3 cm²) | 80–159 s |
| Paris 4 degraded variants ×9 (2.17 cm²) | 80–89 s | ≈18 s |

All verdicts and metrics are in `RESOLUTION_STUDY.md`.

## 5. Cost
- Compute on CPU is cheap. At ~0.5–1 core-group-minute per cm² per checkpoint, an 8-vCPU VM priced at about $0.20/h (an *assumed* typical on-demand price; check your provider) costs **≈ $0.002–0.004 per cm² per checkpoint**. A 10 cm² segment with a 5-model ensemble is roughly 30–60 min and **< $0.25**.
- Our whole study ran on one shared 8-vCPU box in about 6 wall-clock hours, at zero marginal cost: 15 unlabelled segments, 2 controls × 5 checkpoints, 10 degraded variants, and 7 two-scan runs.
- The expensive part is *not* inference. It is being wrong: always run `inkcheck` on a labelled segment of the same scroll first.


What this means:
- On 343P at 8.64 µm, the model's output is **statistically related** to the known ink: every metric beats every shifted, rotated or flipped reference.
- But it recovers only about 1 in 6 reference strokes, and the map does not look like letters.
- A naive global r of 0.40 (z = 8.6 against shifted references) would have suggested otherwise.
- The two controls differ in **both** voxel size and scan energy/protocol, so this does not isolate resolution as the cause.
- Practical advice: run `inkcheck` on a segment with a published prediction **before** spending CPU-hours on unlabelled segments at that resolution.
