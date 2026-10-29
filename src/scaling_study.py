"""Spawn-based 5-point stencil strong/weak scaling and conditional Roofline."""
from __future__ import annotations

import csv
import ctypes
import math
import multiprocessing as mp
import os
import statistics
import time

import numpy as np

from salt import RESULTS, WORKERS, digest_array, parameters, write_json
from profile_env import hardware_profile


def stencil_reference(data: np.ndarray) -> np.ndarray:
    result = np.zeros_like(data)
    result[1:-1, 1:-1] = (data[1:-1, 1:-1] + data[:-2, 1:-1] +
                          data[2:, 1:-1] + data[1:-1, :-2] +
                          data[1:-1, 2:]) * 0.2
    return result


def stencil_worker(input_raw, output_raw, n: int, first: int, last: int) -> None:
    source = np.frombuffer(input_raw, dtype=np.float64).reshape(n, n)
    target = np.frombuffer(output_raw, dtype=np.float64).reshape(n, n)
    if first < last:
        target[first:last, 1:-1] = (source[first:last, 1:-1] +
                                   source[first - 1:last - 1, 1:-1] +
                                   source[first + 1:last + 1, 1:-1] +
                                   source[first:last, :-2] +
                                   source[first:last, 2:]) * 0.2


def available_workers() -> tuple[int, str]:
    profile = hardware_profile()
    cores = profile["physical_cores"]
    if isinstance(cores, int) and cores > 0:
        return cores, "OS-reported physical core count"
    return os.cpu_count() or 1, "fallback logical CPU count"


def run_stencil(n: int, workers: int, seed: int, repetitions: int = 3) -> dict:
    ctx = mp.get_context("spawn")
    input_raw = ctx.RawArray(ctypes.c_double, n * n)
    output_raw = ctx.RawArray(ctypes.c_double, n * n)
    source = np.frombuffer(input_raw, dtype=np.float64).reshape(n, n)
    target = np.frombuffer(output_raw, dtype=np.float64).reshape(n, n)
    source[:] = np.random.default_rng(seed).uniform(-1, 1, size=(n, n))
    expected = stencil_reference(source)
    samples = []
    interior = n - 2
    for _ in range(repetitions):
        target.fill(0)
        processes = []
        for p in range(workers):
            first = 1 + interior * p // workers
            last = 1 + interior * (p + 1) // workers
            processes.append(ctx.Process(target=stencil_worker,
                                         args=(input_raw, output_raw, n, first, last)))
        start = time.perf_counter_ns()
        for process in processes:
            process.start()
        for process in processes:
            process.join(timeout=300)
        elapsed = time.perf_counter_ns() - start
        for process in processes:
            if process.is_alive():
                process.terminate()
                process.join()
                raise TimeoutError(f"stencil N={n} P={workers}: timeout")
            if process.exitcode != 0:
                raise RuntimeError(f"stencil N={n} P={workers}: exit {process.exitcode}")
        np.testing.assert_allclose(target, expected, atol=1e-12, rtol=1e-12)
        samples.append(elapsed)
    return {"student_id": "230103024", "salting_id": "30103024",
            "workers": workers, "dimension": n, "elements": n * n,
            "interior_updates": interior * interior, "samples_ns": ",".join(map(str, samples)),
            "median_runtime_ns": statistics.median(samples),
            "checksum": float(np.sum(target)), "max_absolute_error": float(np.max(np.abs(target - expected))),
            "digest_sha256": digest_array(target)["sha256"],
            "verified": True, "start_method": "spawn", "timing_scope": "process start through join"}


def write_tsv(name: str, rows: list[dict]) -> None:
    with (RESULTS / name).open("w", newline="") as output:
        writer = csv.DictWriter(output, fieldnames=list(rows[0]), delimiter="\t")
        writer.writeheader()
        writer.writerows(rows)


def benchmark() -> tuple[list[dict], list[dict], dict]:
    RESULTS.mkdir(exist_ok=True)
    params = parameters()
    n0 = params["N"]
    core_count, core_source = available_workers()
    counts = []
    p = 1
    while p <= core_count:
        counts.append(p)
        p *= 2
    if 1 not in counts:
        counts = [1]
    strong = []
    for p in counts:
        row = run_stencil(n0, p, params["seed"])
        baseline = strong[0]["median_runtime_ns"] if strong else row["median_runtime_ns"]
        speedup = baseline / row["median_runtime_ns"]
        fraction = ((1 / speedup) - (1 / p)) / (1 - 1 / p) if p > 1 else None
        row.update({"speedup": speedup, "parallel_efficiency": speedup / p, "efficiency_percent": speedup / p * 100,
                    "amdahl_serial_fraction": fraction if fraction is not None else "",
                    "amdahl_ceiling": 1 / fraction if fraction is not None and 0 < fraction <= 1 else "",
                    "amdahl_fit_valid": fraction is None or 0 <= fraction <= 1,
                    "core_limit_source": core_source})
        strong.append(row)
        print(f"M3 strong P={p}: {row['median_runtime_ns'] / 1e9:.3f} s", flush=True)

    weak = []
    for p in counts:
        n = math.ceil(n0 * math.sqrt(p))
        row = run_stencil(n, p, params["seed"])
        updates = row["interior_updates"]
        elapsed_s = row["median_runtime_ns"] / 1e9
        base = weak[0] if weak else row
        # Baseline-normalized throughput (equivalent to work-adjusted speedup).
        scaled = (p * base["interior_updates"] * base["median_runtime_ns"] /
                  (updates * row["median_runtime_ns"]))
        row.update({"throughput_updates_per_s": updates / elapsed_s,
                    "scaled_speedup": scaled,
                    "gustafson_alpha_from_scaled_speedup": (p - scaled) / (p - 1) if p > 1 else "",
                    "core_limit_source": core_source})
        weak.append(row)
        print(f"M3 weak P={p}, N={n}: {elapsed_s:.3f} s", flush=True)
    for row in strong:
        row["study"] = "strong"
    for row in weak:
        row["study"] = "weak"
    valid = [float(r["amdahl_serial_fraction"]) for r in strong if r["workers"] > 1 and r["amdahl_fit_valid"]]
    fitted_f = statistics.median(valid) if len(valid) >= 2 else None
    for row in strong:
        row["amdahl_predicted_speedup"] = (1 / (fitted_f + (1-fitted_f)/row["workers"])) if fitted_f is not None else ""
    with (RESULTS / "scaling_metrics.tsv").open("w", newline="") as output:
        fields = sorted(set().union(*(row.keys() for row in strong + weak)))
        writer = csv.DictWriter(output, fieldnames=fields, delimiter="\t")
        writer.writeheader()
        writer.writerows(strong + weak)
    one = strong[0]
    updates = one["interior_updates"]
    elapsed_s = one["median_runtime_ns"] / 1e9
    roofline = {
        "student_id": "230103024", "salting_id": "30103024",
        "stencil": "one pass, output interior=(center+north+south+west+east)*0.2; zero boundary",
        "floating_operations_per_update": 5,
        "assumed_bytes_per_update_no_reuse": 48,
        "assumed_bytes_per_update_ideal_reuse": 16,
        "arithmetic_intensity_flop_per_byte_no_reuse": 5 / 48,
        "arithmetic_intensity_flop_per_byte_ideal_reuse": 5 / 16,
        "measured_end_to_end_flop_per_s_P1": 5 * updates / elapsed_s,
        "minimum_input_output_bandwidth_bytes_per_s_P1": 16 * updates / elapsed_s,
        "peak_memory_bandwidth_bytes_per_s": None,
        "peak_compute_flop_per_s": None,
        "classification": "conditional: peaks and actual DRAM traffic unavailable",
        "limitations": ["process startup included in measured elapsed time",
                        "48 B assumes five loads plus one store; 16 B assumes ideal input reuse",
                        "actual DRAM traffic, peak bandwidth and peak FLOP/s not measured"]}
    roofline["estimated_serial_fraction"] = fitted_f
    roofline["amdahl_asymptotic_ceiling"] = 1/fitted_f if fitted_f is not None and fitted_f > 0 else None
    roofline["amdahl_fit_note"] = "Ceiling withheld unless at least two worker counts yield physical serial-fraction estimates"
    roofline["cpu_bandwidth_information"] = "Unavailable: no benchmarked sustainable DRAM bandwidth"
    roofline["estimated_dram_bytes_per_update"] = 48
    roofline["arithmetic_intensity_flop_per_byte"] = 5/48
    write_json("roofline_summary.json", roofline)
    return strong, weak, roofline


if __name__ == "__main__":
    benchmark()
