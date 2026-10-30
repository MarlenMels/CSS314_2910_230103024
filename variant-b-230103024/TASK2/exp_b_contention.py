"""Experiment B: contended shared counter."""
import argparse
import time
from multiprocessing import Process, Value, Lock


def contended_worker(shared_counter, lock, iterations):
    for _ in range(iterations):
        with lock:
            shared_counter.value += 1


def run_contended(p, total_increments=2_000_000):
    counter = Value('i', 0)
    lock = Lock()
    counts = [total_increments // p + (1 if i < total_increments % p else 0) for i in range(p)]
    procs = [Process(target=contended_worker, args=(counter, lock, count)) for count in counts]
    t0 = time.perf_counter()
    for proc in procs:
        proc.start()
    for proc in procs:
        proc.join()
    elapsed = time.perf_counter() - t0
    assert all(proc.exitcode == 0 for proc in procs), 'Worker failed'
    assert counter.value == total_increments, f'Wrong count: {counter.value}'
    return elapsed


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--increments', type=int, default=2_000_000)
    args = parser.parse_args()
    runtimes = {}
    for p in (1, 2, 4):
        runtimes[p] = run_contended(p, args.increments)
        print(f'P={p} | Time={runtimes[p]:.6f}s | Count={args.increments}', flush=True)
    t1 = runtimes[1]
    for p in (2, 4):
        tp = runtimes[p]
        speedup = t1 / tp
        e = ((p * tp / t1) - 1) / (p - 1)
        print(f'P={p} | Speedup={speedup:.4f}x | Efficiency={speedup/p*100:.2f}% | Karp-Flatt={e:.6f}')


if __name__ == '__main__':
    main()
