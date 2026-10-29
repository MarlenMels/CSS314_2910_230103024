"""Stride reduction and two genuine matrix loop orders."""
from __future__ import annotations

import csv
import statistics
import time

import numpy as np

from salt import RESULTS, STRIDES, digest_array, parameters


def stride_benchmark() -> list[dict]:
    count = parameters()["buffer_elements"]
    data = np.ones(count, dtype=np.float64)
    rows = []
    with (RESULTS / "stride_results.tsv").open("w", newline="") as output:
        writer = csv.DictWriter(output, fieldnames=["student_id", "salting_id", "stride", "elements_accessed", "warmups", "repetitions",
                                             "runtime_ns_samples", "median_runtime_ns", "ns_per_access",
                                             "reduction", "verified"], delimiter="\t")
        writer.writeheader()
        for stride in STRIDES:
            view = data[::stride]
            for _ in range(5):
                np.sum(view)
            samples = []
            total = None
            for _ in range(5):
                start = time.perf_counter_ns()
                total = float(np.sum(view))
                samples.append(time.perf_counter_ns() - start)
            expected = len(view)
            if total != expected:
                raise AssertionError(f"stride {stride}: {total} != {expected}")
            row = {"student_id": "230103024", "salting_id": "30103024",
                   "stride": stride, "elements_accessed": expected, "warmups": 5,
                   "repetitions": 5, "runtime_ns_samples": ",".join(map(str, samples)),
                   "median_runtime_ns": statistics.median(samples),
                   "ns_per_access": statistics.median(samples) / expected,
                   "reduction": total, "verified": True}
            writer.writerow(row)
            rows.append(row)
    return rows


if __name__ == "__main__":
    RESULTS.mkdir(exist_ok=True)
    stride_benchmark()
