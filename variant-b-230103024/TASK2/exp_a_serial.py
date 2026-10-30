"""Experiment A: fixed serial tail, instructor workload."""
import argparse
import math
import time
from multiprocessing import Pool


def heavy_math(n):
    return sum(math.sin(i) * math.cos(i) for i in range(1, n))


def run_experiment(workers, total_chunks=16, chunk_size=2_000_000):
    start = time.perf_counter()
    time.sleep(0.40)
    with Pool(processes=workers) as pool:
        results = pool.map(heavy_math, [chunk_size] * total_chunks)
    return time.perf_counter() - start, sum(results)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--chunks', type=int, default=16)
    parser.add_argument('--chunk-size', type=int, default=2_000_000)
    args = parser.parse_args()
    runtimes = {}
    checksums = []
    for p in (1, 2, 4):
        t, result = run_experiment(p, args.chunks, args.chunk_size)
        runtimes[p] = t
        checksums.append(result)
        print(f'P={p} | Time={t:.6f}s | Checksum={result:.10f}', flush=True)
    assert all(math.isclose(x, checksums[0], rel_tol=1e-12, abs_tol=1e-8) for x in checksums)
    t1 = runtimes[1]
    for p in (2, 4):
        tp = runtimes[p]
        speedup = t1 / tp
        e = ((p * tp / t1) - 1) / (p - 1)
        print(f'P={p} | Speedup={speedup:.4f}x | Efficiency={speedup/p*100:.2f}% | Karp-Flatt={e:.6f}')


if __name__ == '__main__':
    main()
