# study/: scripts behind `docs/RESOLUTION_STUDY.md`

The scripts were run from a workspace root with this layout. All paths are relative to that root; set `WS` and `VILLA_SRC` for the `.sh` files.

```
villa/                          # git clone https://github.com/ScrollPrize/villa (ink inference CLI)
checkpoints/{ink_9um,erwin,klavis,hecate}/   # public checkpoints (Hugging Face)
control/p4_ctrl_9.6um.zarr      # Paris 4 20231005123336 crop, level 2 of the 2.4 um scan, pooled 4x in z
control/p4_ref_ds8.jpg          # published new_canon ink map, ds8 (19.2 um)
data_raw/PHerc0343P/segments/20250511003658-tifxyz/...  # public 343P segment, ink map, 2.215 um surface volume
prize_oct/{results,study}/      # outputs (copied here into results/)
```

| script | does |
|---|---|
| `make_degraded_p4.py`, `make_degraded_p4_b.py` | blur, bin and noise variants of the Paris 4 input |
| `run_ablation.sh` | dense_native inference plus inkcheck on each variant (2 threads) |
| `make_343P_from_2um.py`, `run_343P_2um.sh` | same-segment two-scan control: 2.215 um surface volume, level 2, mean-pooled 4x in z, 5 checkpoints |
| `psd_compare.py`, `layer_snr.py` | blur and noise proxies (spectral HF/LF ratio, adjacent-layer high-pass correlation) |
| `stroke_geometry.py` | stroke size and ink fraction of both references on a 19.2 um grid |
| `scan_stats.py` | statistics of unlabelled 0800/1203 maps and their depth nulls |
| `collect.py` | full study tables and dose-response plot (contain Paris 4 scores: kept private until 2027-06-25; the shipped `results/study/tables.md` is verdict-only for Paris 4) |
