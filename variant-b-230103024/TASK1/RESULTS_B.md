# CS482 — Scalability Diagnostics: Variant B

**Student ID:** 230103024  
**Instructor:** Sufyan bin Uzayr  
**Required Git branch:** `variant-b-230103024`

## Execution environment and methodology

The measurements below are **student-provided local benchmark results**, replacing the previous ChatGPT Linux-container results. The exact OS, CPU model, Python version, and multiprocessing start method for these runs were **not included with the submitted outputs** and should be inserted from `update_environment.py` before submission. Git branch creation and push have not been independently verified.

Each experiment was measured once for P ∈ {1, 2, 4, 8}. Timing includes multiprocessing startup and teardown. The handout's performance targets are illustrative and not substituted for observed results.

Formulas: **Speedup** S(p) = T₁/Tₚ; **Efficiency** E(p) = 100 × S(p)/p; **Karp–Flatt** e(p) = (p × Tₚ/T₁ − 1)/(p − 1), undefined at p=1. Experiment A uses a separate T₁ baseline for each chunk size.

## Experiment A — Granularity trap (1,000,000 items)

### Fine-grained dispatch (chunksize = 1)

| P | Runtime (s) | Speedup | Efficiency | Karp–Flatt | Checksum |
|---|---:|---:|---:|---:|---:|
| 1 | 19.716292 | 1.000000 | 100.000% | N/A | 131434424 |
| 2 | 13.336145 | 1.478410 | 73.921% | 0.352805 | 131434424 |
| 4 | 17.141685 | 1.150196 | 28.755% | 0.825890 | 131434424 |
| 8 | 18.043991 | 1.092679 | 13.658% | 0.903065 | 131434424 |

### Coarse-grained dispatch (chunksize = 10,000)

| P | Runtime (s) | Speedup | Efficiency | Karp–Flatt | Checksum |
|---|---:|---:|---:|---:|---:|
| 1 | 9.240755 | 1.000000 | 100.000% | N/A | 131434424 |
| 2 | 4.759394 | 1.941582 | 97.079% | 0.030088 | 131434424 |
| 4 | 2.472572 | 3.737305 | 93.433% | 0.023430 | 131434424 |
| 8 | 1.380171 | 6.695367 | 83.692% | 0.027837 | 131434424 |

**Diagnosis:** All eight runs produced the same checksum, verifying output consistency. With chunksize=1, the master must dispatch many tiny tasks; efficiency drops from 73.921% at P=2 to 13.658% at P=8, while e(p) rises from 0.353 to 0.903. With chunksize=10,000, dispatch costs are amortized over larger work units: S₈ = 6.695 and e(p) remains nearly flat at approximately 0.02–0.03. At P=8, coarse chunking is approximately **13.07× faster** than fine chunking for the same total workload.

## Experiment B — Shared IPC queue contention (400,000 items)

| P | Runtime (s) | Speedup | Efficiency | Karp–Flatt | Check |
|---|---:|---:|---:|---:|---|
| 1 | 2.219953 | 1.000000 | 100.000% | N/A | PASS |
| 2 | 5.076796 | 0.437274 | 21.864% | 3.573788 | PASS |
| 4 | 5.267030 | 0.421481 | 10.537% | 2.830116 | PASS |
| 8 | 6.633912 | 0.334637 | 4.183% | 3.272357 | PASS |

**Diagnosis:** T₈ > T₄ > T₂ > T₁, demonstrating monotonically worsening runtime and negative scaling (S₈ = 0.335). All correctness checks passed. Karp–Flatt values are very high, consistent with shared-queue IPC overhead, but **not monotonically increasing**: e(2)=3.574, e(4)=2.830, e(8)=3.272. The measured pattern supports a serious communication bottleneck without meeting the handout's strict monotonic e(p) criterion.

## Experiment C — Buffered aggregation (10,000,000 items; batch size = 10,000)

| P | Runtime (s) | Speedup | Efficiency | Karp–Flatt | Throughput (items/s) | Checksum |
|---|---:|---:|---:|---:|---:|---:|
| 1 | 0.635179 | 1.000000 | 100.000% | N/A | 15,743,594.58 | 29,999,994 |
| 2 | 0.356403 | 1.782195 | 89.110% | 0.122212 | 28,058,154.73 | 29,999,990 |
| 4 | 0.220642 | 2.878773 | 71.969% | 0.129827 | 45,322,235.43 | 29,999,988 |
| 8 | 0.167750 | 3.786471 | 47.331% | 0.158969 | 59,612,666.81 | 29,999,952 |

**Diagnosis:** Local batching reduces the number of queue messages substantially and yields positive scaling: S₈ = 3.786. However, this is below the handout target S₈ > 5.0, and e(8) = 0.159 exceeds the target e(8) ≤ 0.05. Throughput at P=8 is approximately **988.7×** that of Experiment B at P=8 (59,612,666.81 versus 400,000/6.633912 ≈ 60,296 items/s). This is a throughput comparison across different algorithms and workload sizes, not a controlled same-workload speedup measurement.

**Checksum note:** Experiment C's sums differ across P because each worker starts its `i % 7` sequence at zero; the partitioning changes with worker count. For each P, the observed sum matches the expected sum for that worker partitioning. The varying sums are **not** by themselves evidence of lost data.

## Comparative performance matrix

| Configuration | T₁ (s) | T₂ (s) | T₄ (s) | T₈ (s) | S₈ | e(2) | e(8) | Verdict |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| A: Micro (k=1) | 19.716292 | 13.336145 | 17.141685 | 18.043991 | 1.092679 | 0.352805 | 0.903065 | Dispatch overhead; poor scaling |
| A: Coarse (k=10,000) | 9.240755 | 4.759394 | 2.472572 | 1.380171 | 6.695367 | 0.030088 | 0.027837 | Strong scaling; nearly flat e(p) |
| B: Queue choke | 2.219953 | 5.076796 | 5.267030 | 6.633912 | 0.334637 | 3.573788 | 3.272357 | Negative scaling; e(p) not monotonic |
| C: Buffered batch | 0.635179 | 0.356403 | 0.220642 | 0.167750 | 3.786471 | 0.122212 | 0.158969 | Higher throughput; targets unmet |

## Instructor sign-off checklist

| Requirement | Status | Evidence |
|---|---|---|
| A: Demonstrate chunksize=1 dispatch starvation at 1M | **PASS** | S₈=1.093; E₈=13.658%; e(8)=0.903 |
| A: Coarse-grained improvement | **PASS** | S₈=6.695; e(8)=0.028 |
| B: T₈ > T₁ | **PASS** | 6.633912 > 2.219953 seconds |
| B: Monotonic increase in e(p) | **FAIL** | 3.574 → 2.830 → 3.272 |
| C: >10× throughput vs B at P=8 | **PASS** | Approximately 988.7× throughput |
| C: S₈ > 5.0 | **FAIL** | S₈=3.786471 |
| C: e(8) ≤ 0.05 | **FAIL** | e(8)=0.158969 |
| Git branch and remote push | **NOT VERIFIED** | No Git status/push output supplied |

## Conclusion

The complete 1,000,000-item Experiment A now confirms that fine-grained dispatch creates severe overhead, while coarse chunking scales well. Experiment B shows negative speedup from a shared IPC queue, although its Karp–Flatt values are not monotonic. Experiment C substantially increases throughput by aggregating local results, but its measured eight-worker speedup and Karp–Flatt metric fall short of the instructor's targets. These are the actual submitted measurements; no values have been adjusted to match expected figures.

## Reproduce and submit

```bash
mkdir -p evidence
python3 exp_a_granularity.py | tee evidence/experiment_a_output.txt
python3 exp_b_queue.py | tee evidence/experiment_b_output.txt
python3 exp_c_buffered.py | tee evidence/experiment_c_output.txt
# Verify the branch before committing:
git branch --show-current
# On variant-b-230103024:
git add exp_a_granularity.py exp_b_queue.py exp_c_buffered.py RESULTS_B.md evidence/
git commit -m "Complete Variant B empirical benchmarks and results"
git push -u origin variant-b-230103024
```
