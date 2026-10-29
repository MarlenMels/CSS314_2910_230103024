"""Stride reduction and two genuine matrix loop orders."""
from __future__ import annotations

import json
import statistics
import time

import numpy as np

from salt import RESULTS, STRIDES, digest_array, parameters


def naive_ijk(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    n = a.shape[0]
    out = np.empty((n, n), dtype=np.float64)
    for i in range(n):
        for j in range(n):
            # dot performs the inner k reduction over a strided B column.
            out[i, j] = np.dot(a[i, :], b[:, j])
    return out


def interchanged_ikj(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    n = a.shape[0]
    out = np.zeros((n, n), dtype=np.float64)
    for i in range(n):
        for k in range(n):
            # Contiguous j row update; no matrix-multiply shortcut.
            out[i, :] += a[i, k] * b[k, :]
    return out


def loop_benchmark() -> list[dict]:
    params = parameters()
    n = params["N"] // 2
    rng = np.random.default_rng(params["seed"])
    a = rng.uniform(-1, 1, size=(n, n)).astype(np.float64)
    b = rng.uniform(-1, 1, size=(n, n)).astype(np.float64)
    reference = a @ b
    rows = []
    outputs = {}
    for label, operation in (("i-j-k", naive_ijk), ("i-k-j", interchanged_ikj)):
        samples = []
        result = None
        for _ in range(3):
            start = time.perf_counter_ns()
            result = operation(a, b)
            samples.append(time.perf_counter_ns() - start)
        assert result is not None
        max_error = float(np.max(np.abs(result - reference)))
        np.testing.assert_allclose(result, reference, atol=1e-12, rtol=1e-12)
        outputs[label] = result
        rows.append({"algorithm": label, "salted_N": params["N"], "subblock_M": n,
                     "samples_ns": ",".join(map(str, samples)), "median_runtime_ns": statistics.median(samples),
                     "max_absolute_error_vs_numpy": max_error, "numpy_allclose_atol": 1e-12,
                     "numpy_allclose_rtol": 1e-12, "digest_sha256": digest_array(result)["sha256"]})
    np.testing.assert_allclose(outputs["i-j-k"], outputs["i-k-j"], atol=1e-12, rtol=1e-12)
    speedup = rows[0]["median_runtime_ns"] / rows[1]["median_runtime_ns"]
    for row in rows:
        row["speedup_ijk_over_ikj"] = speedup
    (RESULTS / "loop_interchange.json").write_text(json.dumps({
        "student_id": "230103024", "salting_id": "30103024", "salted_N": params["N"],
        "subblock_M": n, "algorithms": rows, "speedup_ijk_over_ikj": speedup,
        "reference": "NumPy matrix multiplication", "tolerance_atol": 1e-12,
        "tolerance_rtol": 1e-12, "verified": True}, indent=2) + "\n")
    return rows


def main() -> None:
    RESULTS.mkdir(exist_ok=True)
    loop_benchmark()
    print("M1: stride and loop interchange TSV written")


if __name__ == "__main__":
    main()
