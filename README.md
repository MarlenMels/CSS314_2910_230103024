# CS482 Parallel Computing laboratory

Student ID: **230103024**. Deterministic eight-digit salting ID: **30103024**. This directory is the submission root. Measurements below were made on the local Apple M1 Pro machine with Python 3.13.12 and NumPy 2.5.3; timings will vary on another host.

## Structure

- `src/profile_env.py`, `src/salt.py`: M0 host inventory and deterministic parameters.
- `src/stride_bench.py`, `src/dense_kernel.py`: M1 locality and loop interchange.
- `src/false_sharing.py`: M2 multiprocessing counters.
- `src/scaling_study.py`: M3 stencil scaling and roofline summary.
- `verify_outputs.py`: M4 artifact and numerical verifier.
- `results/`: seven measurement files and `verification_receipt.sig`.

## Environment and installation

Python 3.10+ on macOS or Linux, with NumPy. From this directory:

```sh
python3 -m pip install -r requirements.txt
```

The experiments use genuine local processes. Run each command from this directory, in order:

```sh
python3 src/profile_env.py
python3 src/stride_bench.py
python3 src/dense_kernel.py
python3 src/false_sharing.py
python3 src/scaling_study.py
python3 verify_outputs.py
```

For a syntax check, run `python3 -m compileall -q src verify_outputs.py`. Rerunning a benchmark replaces only its corresponding result file. Run the verifier after all experiments.

## M0: hardware and salting

The local CPU is reported as **Apple M1 Pro**, arm64, with 10 physical cores (8 Performance and 2 Efficiency) and 10 logical threads. The OS reports no SMT in this count. Kernel release is **27.0.0**. Python is **CPython 3.13.12**. The OS did not provide reliable base frequency, L1/L2/L3 sizes, or a separate microarchitecture identifier; these remain `null` with explanations in `results/host_profile.json`. An authorized `sysctl -n hw.cachelinesize` query reported a 128-byte cache line, which is recorded in the host profile. The instructor verifier requires exactly 64 bytes and therefore fails on this host without falsifying hardware data. `results/salted_params.json` records SHA-256 prefix integer **629429653**, `N=1088`, `buffer_elements=16777216`, and `seed=85602`.

### Hardware Compatibility Note

This experiment ran on an **Apple M1 Pro (arm64)**. macOS reports `hw.cachelinesize: 128` from `sysctl hw.cachelinesize`; Apple also documents 128-byte cache lines on Apple silicon. The instructor verifier requires `cache_line_bytes == 64`, so Milestone 0 fails on this machine. The reported value is preserved. `hw.cachelinesize` is a system-level OS value; it does not independently establish the physical line size of every L1, L2, or other cache level. The 64-byte counter spacing in M2 therefore may not isolate counters on this host. Other verifier schema differences and its full-ID salting calculation remain unresolved. The official verifier has **not** passed, and the existing JSON receipt is **not** an official signature.

## M1: memory locality and loop interchange

The stride benchmark uses a 128 MiB float64 array, five warmups and five measured reductions per stride. Median nanoseconds per accessed element were: stride 1 **0.184**, 2 **0.278**, 4 **0.541**, 8 **1.113**, 16 **2.961**, 32 **3.360**, 64 **3.335**, 128 **3.574**. Larger strides generally cost more per element because fewer neighboring values are useful from each fetched cache line. These are aggregate reduction times per element, not isolated cache-miss latencies.

For `M=N//2=544`, the median `i-j-k` runtime was about **0.288 s** and `i-k-j` about **0.368 s**; the recorded speedup `T_ijk/T_ikj` is **0.782**. The `i-k-j` row updates have contiguous access but incur more Python/NumPy operation overhead in this implementation. Both orders were checked against independent NumPy matrix multiplication at `atol=rtol=1e-12`. The three raw samples and exact medians are in `results/loop_interchange.json`.

## M2: false sharing

Each of 1, 2, 4 and 8 spawned processes performs 5,000,000 signed-int64 increments. The padded counters start at a 64-byte aligned address and occupy slots 64 bytes apart. Privatized workers accumulate locally and write one result each. The measured `P=8` times were **0.859 s** unpadded, **0.671 s** padded, and **0.285 s** privatized. Relative to each strategy's own `P=1`, the corresponding speedups were **0.869**, **0.864**, and **0.863**. Padding was faster than unpadded at `P=8` in this run, but its own scaling still slowed down. The single run per configuration includes process startup and scheduler noise; it does not isolate cache coherence costs. All 12 totals equal `P × 5,000,000`. The requested Karp–Flatt values are recorded, although workload grows with P here, so they do not estimate a strong-scaling serial fraction.

## M3: strong and weak scaling

The deterministic five-point stencil computes `(center+north+south+west+east)*0.2` for interior cells and leaves the boundary zero. Rows are partitioned across spawned processes. Each run is compared to a sequential NumPy reference; M4 also compares a small case to an independent scalar loop.

Strong scaling fixes `N=1088`. Median times for P=1,2,4,8 were **0.121, 0.124, 0.133, 0.149 s**. Speedups were **1.000, 0.978, 0.909, 0.813**. The expected Amdahl improvement was not realized because process startup and scheduling dominate this small vectorized kernel. Fitted serial fractions are recorded per worker count. No asymptotic ceiling is claimed because fewer than two measured worker counts gave a meaningful fraction in `[0,1]`.

Weak scaling uses `N(P)=ceil(1088 sqrt(P))` and counts only `(N(P)-2)^2` stencil updates. Dimensions were **1088, 1539, 2176, 3078** for P=1,2,4,8. Median times were **0.123, 0.132, 0.146, 0.178 s**. The required work-normalized scaled speedups were **1.000, 0.932, 0.840, 0.692**. This metric is `P × Work(1) × T1 / (Work(P) × TP)`, so ideal weak scaling gives about 1, not P. The measured values fall below 1 as overhead and memory demand grow.

## Roofline

The stencil performs five floating-point operations per interior update: four additions and one multiplication. A no-reuse traffic estimate is five 8-byte loads plus one 8-byte store, or **48 bytes/update**, giving **0.10417 FLOP/byte**. Ideal input reuse would reduce the estimate toward 16 bytes/update and 0.3125 FLOP/byte. The low intensity suggests potential memory sensitivity. A measured sustainable DRAM bandwidth, actual DRAM traffic, and CPU compute peak are unavailable, so a definitive memory-bound or compute-bound classification and numerical roofline ceiling cannot be stated. The P=1 end-to-end throughput in the JSON includes process creation and is not a hardware peak.

## M4: numerical verification

`verify_outputs.py` is the instructor-provided verifier. It currently stops at Milestone 0 because the host reports a 128-byte cache line while the script requires 64. It has not generated `results/verification_receipt.sig`. The official `STUDENT_ID` / `SALTED_N` / `SIGNATURE` receipt will only be generated if all checks complete.

## Limitations and theory versus measurement

The loop-order kernels use NumPy dot or row operations inside different Python loop nests; their call overhead differs. The counter benchmark has one timing per configuration and fixed iterations per worker, so its speedup and Karp–Flatt figures are descriptive. Stencil timing includes spawn and join. Amdahl predicts improvement only when a substantial parallel portion dominates overhead; that condition was not met here. Roofline analysis is conditional because peak bandwidth, peak FLOP/s and actual DRAM traffic were not measured. Cache and clock values unavailable from local OS queries remain unknown rather than inferred from product specifications.
