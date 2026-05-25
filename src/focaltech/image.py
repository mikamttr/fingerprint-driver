#image.py - Image processing utilities for FocalTech fingerprint data.

from pathlib import Path
import time

import numpy as np
from PIL import Image


def raw16_to_gray8(raw: bytes, width: int, height: int) -> np.ndarray:
    expected_size = width * height * 2

    if len(raw) < expected_size:
        raise RuntimeError(f"RAW too small: {len(raw)} < {expected_size}")

    raw = raw[:expected_size]

    arr = np.frombuffer(raw, dtype="<i2")
    arr = arr.reshape((height, width))

    arr = -arr

    arr_min = int(arr.min())
    arr_max = int(arr.max())

    if arr_max == arr_min:
        return np.zeros((height, width), dtype=np.uint8)

    return ((arr - arr_min) * 255 / (arr_max - arr_min)).astype(np.uint8)


def save_capture(raw: bytes, width: int, height: int, output_dir="captures"):
    output_path = Path(output_dir)
    output_path.mkdir(exist_ok=True)

    timestamp = int(time.time())

    raw_path = output_path / f"finger_{timestamp}.raw"
    png_path = output_path / f"finger_{timestamp}.png"

    raw_path.write_bytes(raw)

    img8 = raw16_to_gray8(raw, width, height)
    Image.fromarray(img8, mode="L").save(png_path)

    return raw_path, png_path