"""Experiment C: batched local aggregation over IPC queue (Variant B)."""
import argparse
import multiprocessing as mp
import time


def buffered_worker(out_queue, items_per_worker, batch_size=10_000):
    buffer = []
    for i in range(items_per_worker):
        buffer.append(i % 7)
        if len(buffer) >= batch_size:
            out_queue.put(sum(buffer))
            buffer.clear()
    if buffer:
        out_queue.put(sum(buffer))
    out_queue.put(None)


def run_buffered(p, total_items=10_000_000, batch_size=10_000):
    q = mp.Queue()
    counts = [total_items // p + (i < total_items % p) for i in range(p)]
    workers = [mp.Process(target=buffered_worker, args=(q, n, batch_size)) for n in counts]
    t0 = time.perf_counter()
    for w in workers:
        w.start()
    total_sum, active = 0, p
    while active:
        value = q.get()
        if value is None:
            active -= 1
        else:
            total_sum += value
    for w in workers:
        w.join()
    elapsed = time.perf_counter() - t0
    assert all(w.exitcode == 0 for w in workers), 'Worker failed'
    expected = sum((n // 7) * 21 + sum(range(n % 7)) for n in counts)
    assert total_sum == expected, f'Incorrect checksum {total_sum} != {expected}'
    q.close()
    return elapsed, total_sum


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--total-items', type=int, default=10_000_000)
    parser.add_argument('--batch-size', type=int, default=10_000)
    parser.add_argument('--workers', type=int, nargs='+', default=[1, 2, 4, 8])
    args = parser.parse_args()
    times = {}
    for p in args.workers:
        t, checksum = run_buffered(p, args.total_items, args.batch_size)
        times[p] = t
        print(f'P={p} T={t:.6f}s ITEMS={args.total_items} CHECKSUM={checksum} THROUGHPUT={args.total_items/t:.2f}', flush=True)
    if 1 in times:
        for p, t in times.items():
            s = times[1] / t
            e = 'N/A' if p == 1 else f'{((p*t/times[1])-1)/(p-1):.6f}'
            print(f'METRIC P={p} SPEEDUP={s:.6f} EFFICIENCY={100*s/p:.3f}% KF={e}', flush=True)


if __name__ == '__main__':
    main()
