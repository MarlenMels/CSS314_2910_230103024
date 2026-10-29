"""Student-specific deterministic parameters and numerical serialization."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
RESULTS = ROOT / "results"
SALT_ID = "30103024"
STRIDES = (1, 2, 4, 8, 16, 32, 64, 128)
WORKERS = (1, 2, 4, 8)
ITERATIONS = 5_000_000


def parameters(student_id: str = SALT_ID) -> dict:
    if len(student_id) != 8 or not student_id.isascii() or not student_id.isdigit():
        raise ValueError("salting ID must contain exactly eight ASCII digits")
    h = int(hashlib.sha256(student_id.encode()).hexdigest()[:8], 16)
    return {"student_id": "230103024", "salting_id": student_id, "sha256_prefix_int": h,
            "N": 1024 + (h % 9) * 64,
            "buffer_elements": 16_777_216, "seed": h % 100_007}


def write_json(name: str, value: dict) -> None:
    RESULTS.mkdir(exist_ok=True)
    (RESULTS / name).write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")


def digest_array(array: np.ndarray, decimals: int = 6) -> dict:
    """Digest salting ID, shape, dtype and rounded little-endian C-order float64 bytes."""
    values = np.ascontiguousarray(np.round(array, decimals=decimals), dtype="<f8")
    header = json.dumps({"salting_id": SALT_ID, "shape": list(values.shape), "dtype": "<f8",
                         "decimals": decimals}, sort_keys=True, separators=(",", ":")).encode()
    return {"sha256": hashlib.sha256(header + b"\n" + values.tobytes(order="C")).hexdigest(),
            "shape": list(values.shape), "dtype": "float64", "byte_order": "little",
            "round_decimals": decimals, "salting_id": SALT_ID,
            "serialization": "sorted compact JSON header including salting ID and shape + newline + C-order <f8 bytes"}
