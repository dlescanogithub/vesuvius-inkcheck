"""Minimal cv2 stand-in (imread only) so the IR-truth scorer runs without OpenCV. Reads with Pillow."""
import numpy as np
from PIL import Image
Image.MAX_IMAGE_PIXELS = None
IMREAD_UNCHANGED = -1
def imread(path, flag=1):
    a = np.array(Image.open(path))
    if flag == 0 and a.ndim == 3:
        a = a[..., :3].mean(-1).astype(a.dtype)
    if a.ndim == 3 and flag != 0:
        a = a[..., ::-1]
    return a
