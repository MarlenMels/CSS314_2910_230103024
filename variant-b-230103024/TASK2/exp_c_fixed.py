"""Experiment C: process-private counters and final reduction."""
import argparse
import time
from multiprocessing import Pool


def private_worker(iterations):
    local_sum = 0
    for _ in range(iterations):
        local_sum += 1
    return local_sum


def run_privatized(p, total_increments=20_000_000):
    counts = [total_increments // p + (1 if i < total_increments % p else 0) for i in range(p)]
    t0 = time.perf_counter()
    with Pool(processes=p) as pool:
        results = pool.map(private_worker, counts)
    total = sum(results)
    elapsed = time.perf_counter() - t0
    assert total == total_increments
    return elapsed


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--increments', type=int, default=20_000_000)
    args = parser.parse_args()
    runtimes = {}
    for p in (1, 2, 4):
        runtimes[p] = run_privatized(p, args.increments)
        print(f'P={p} | Time={runtimes[p]:.6f}s | Count={args.increments}', flush=True)
    t1 = runtimes[1]
    for p in (2, 4):
        tp = runtimes[p]
        speedup = t1 / tp
        e = ((p * tp / t1) - 1) / (p - 1)
        print(f'P={p} | Speedup={speedup:.4f}x | Efficiency={speedup/p*100:.2f}% | Karp-Flatt={e:.6f}')


if __name__ == '__main__':
    main()
