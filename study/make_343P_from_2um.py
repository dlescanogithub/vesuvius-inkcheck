"""Same segment, other scan: build a ~8.86 um isotropic surface volume for PHerc0343P 20250511003658
from the published 2.215 um / 111 keV surface volume (OME-Zarr level 2 = 8.86 um in XY, 2.215 um in z;
mean-pool 4 layers in z -> 29 layers).  Same recipe as our Paris-4 control."""
import sys, numpy as np
sys.path.insert(0, "tools"); from zread import read_local; from zfetch import write_local_zarr
src = "data_raw/sv343/PHerc0343P/segments/20250511003658-tifxyz/surface-volumes/2.215um-0.4m-111keV-volume-20260304131111.zarr/2"
v = read_local(src); print("level2", v.shape)
Z = (v.shape[0] // 4) * 4
p = v[:Z].reshape(Z // 4, 4, *v.shape[1:]).astype(np.float32).mean(1)
write_local_zarr("prize_oct/study/343P_from2um_8.86um.zarr", np.rint(p).astype(np.uint8))
r = read_local("renders/343P_20250511003658/0")
def prof(a):
    m = a.min(0) > 0; return [round(float(a[i][m].mean()), 1) for i in range(a.shape[0])]
print("pooled 2.2um layer means:", prof(p)); print("native 8.64 render layer means:", prof(r))
