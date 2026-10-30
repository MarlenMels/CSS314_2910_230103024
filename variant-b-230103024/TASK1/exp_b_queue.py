"""Experiment B: shared IPC queue contention (Variant B)."""
import argparse
import multiprocessing as mp
import time


def queue_worker(out_queue, items_per_worker):
    for i in range(items_per_worker):
        out_queue.put(i % 7)


def run_queue_benchmark(p, total_items=400_000):
    q = mp.Queue()
    counts = [total_items // p + (i < total_items % p) for i in range(p)]
    workers = [mp.Process(target=queue_worker, args=(q, n)) for n in counts]
    t0 = time.perf_counter()
    for w in workers:
        w.start()
    checksum = 0
    for _ in range(total_items):
        checksum += q.get()
    for w in workers:
        w.join()
    elapsed = time.perf_counter() - t0
    assert all(w.exitcode == 0 for w in workers), 'Worker failed'
    expected = sum((n // 7) * 21 + sum(range(n % 7)) for n in counts)
    assert checksum == expected, f'Incorrect checksum {checksum} != {expected}'
    q.close()
    return elapsed


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--total-items', type=int, default=400_000)
    parser.add_argument('--workers', type=int, nargs='+', default=[1, 2, 4, 8])
    args = parser.parse_args()
    times = {}
    for p in args.workers:
        t = run_queue_benchmark(p, args.total_items)
        times[p] = t
        print(f'P={p} T={t:.6f}s ITEMS={args.total_items} CHECK=PASS', flush=True)
    if 1 in times:
        for p, t in times.items():
            s = times[1] / t
            e = 'N/A' if p == 1 else f'{((p*t/times[1])-1)/(p-1):.6f}'
            print(f'METRIC P={p} SPEEDUP={s:.6f} EFFICIENCY={100*s/p:.3f}% KF={e}', flush=True)


if __name__ == '__main__':
    main()
