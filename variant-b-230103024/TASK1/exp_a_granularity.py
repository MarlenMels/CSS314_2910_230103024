"""Experiment A: multiprocessing dispatch granularity (Variant B)."""
import argparse
import multiprocessing as mp
import time


def collatz_steps(n: int) -> int:
    steps = 0
    while n > 1:
        n = n // 2 if n % 2 == 0 else 3 * n + 1
        steps += 1
    return steps


def run_granularity(workers: int, total_items: int = 1_000_000, chunk_size: int = 1):
    t0 = time.perf_counter()
    with mp.Pool(processes=workers) as pool:
        results = pool.map(collatz_steps, range(1, total_items + 1), chunksize=chunk_size)
    return time.perf_counter() - t0, sum(results)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--total-items', type=int, default=1_000_000)
    parser.add_argument('--workers', type=int, nargs='+', default=[1, 2, 4, 8])
    parser.add_argument('--chunks', type=int, nargs='+', default=[1, 10_000])
    args = parser.parse_args()
    for chunk in args.chunks:
        print(f'CHUNK={chunk} TOTAL={args.total_items}', flush=True)
        times, sums = {}, {}
        for p in args.workers:
            t, checksum = run_granularity(p, args.total_items, chunk)
            times[p], sums[p] = t, checksum
            print(f'P={p} T={t:.6f}s CHECKSUM={checksum}', flush=True)
        assert len(set(sums.values())) == 1, 'Checksum mismatch'
        if 1 in times:
            for p, t in times.items():
                s = times[1] / t
                e = 'N/A' if p == 1 else f'{((p*t/times[1])-1)/(p-1):.6f}'
                print(f'METRIC CHUNK={chunk} P={p} SPEEDUP={s:.6f} EFFICIENCY={100*s/p:.3f}% KF={e}', flush=True)


if __name__ == '__main__':
    main()
