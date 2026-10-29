"""Real shared-memory processes with explicitly cache-aligned counter slots."""
from __future__ import annotations

import csv
import ctypes
import multiprocessing as mp
import statistics
import time

from salt import ITERATIONS, RESULTS, WORKERS


def aligned_array(ctx: mp.context.BaseContext) -> tuple:
    # Extra slots permit aligning index zero to a 64-byte address.
    array = ctx.RawArray(ctypes.c_int64, 8 * max(WORKERS) + 8)
    address = ctypes.addressof(array)
    base = ((-address) % 64) // ctypes.sizeof(ctypes.c_int64)
    assert (address + base * 8) % 64 == 0
    return array, base, address + base * 8


def worker(array, index: int, iterations: int, mode: str) -> None:
    if mode == "privatized":
        local = 0
        for _ in range(iterations):
            local += 1
        array[index] = local
    else:
        for _ in range(iterations):
            array[index] += 1


def run_once(mode: str, count: int, iterations: int = ITERATIONS) -> dict:
    ctx = mp.get_context("spawn")
    array, base, address = aligned_array(ctx)
    indices = [base + (p * 8 if mode == "padded" else p) for p in range(count)]
    processes = [ctx.Process(target=worker, args=(array, index, iterations, mode))
                 for index in indices]
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
            raise TimeoutError(f"{mode}, P={count}: worker timeout")
        if process.exitcode != 0:
            raise RuntimeError(f"{mode}, P={count}: worker exit {process.exitcode}")
    values = [array[index] for index in indices]
    if values != [iterations] * count:
        raise AssertionError(f"{mode}, P={count}: incorrect counters {values}")
    return {"student_id": "230103024", "salting_id": "30103024",
            "approach": mode, "workers": count, "iterations_per_worker": iterations,
            "runtime_ns": elapsed, "runtime_samples_ns": str(elapsed),
            "counter_total": sum(values), "expected_total": count * iterations,
            "verified": True, "aligned_base_address_mod_64": address % 64,
            "slot_spacing_bytes": 64 if mode == "padded" else 8,
            "start_method": "spawn", "timing_scope": "process start through join"}


def benchmark() -> list[dict]:
    RESULTS.mkdir(exist_ok=True)
    rows = []
    for mode in ("unpadded", "padded", "privatized"):
        baseline = None
        for count in WORKERS:
            row = run_once(mode, count)
            if count == 1:
                baseline = row["runtime_ns"]
            assert baseline is not None
            speedup = baseline / row["runtime_ns"]
            row["speedup"] = speedup
            row["karp_flatt"] = ((1 / speedup) - (1 / count)) / (1 - 1 / count) if count > 1 else ""
            rows.append(row)
            print(f"M2 {mode} P={count}: {row['runtime_ns'] / 1e9:.3f} s", flush=True)
    with (RESULTS / "false_sharing_karp_flatt.tsv").open("w", newline="") as output:
        writer = csv.DictWriter(output, fieldnames=list(rows[0]), delimiter="\t")
        writer.writeheader()
        writer.writerows(rows)
    return rows


if __name__ == "__main__":
    benchmark()
