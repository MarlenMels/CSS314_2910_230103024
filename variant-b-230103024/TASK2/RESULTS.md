# CS482 — Empirical Scalability Diagnostics: Karp–Flatt

**Student ID:** 230103024  
**Instructor:** Sufyan bin Uzayr  
**Branch:** `practice-230103024`  
**Status:** All three experiments executed for P = 1, 2, 4; Git push not verified.

## Hardware and environment

- CPU: **Not provided**
- Logical cores: **Not provided**
- OS: **Not provided for these runs**
- Python: **Not provided**

## Method

Worker counts: P = 1, 2, 4. All times are wall-clock seconds measured with `time.perf_counter()`, including process startup and shutdown. Each experiment uses its own P=1 baseline. Speedup S(p) = T1/Tp; efficiency E(p) = S(p)/p × 100%; Karp–Flatt e(p) = (p × Tp/T1 − 1)/(p − 1) for p ≥ 2. One run per configuration was supplied.

## Measured results

| Experiment | T1 (s) | T2 (s) | T4 (s) | e(2) | e(4) | Diagnosis |
|---|---:|---:|---:|---:|---:|---|
| A: Serial Tail | 3.882017 | 2.261262 | 1.387859 | 0.164993 | 0.143346 | Relatively stable Karp–Flatt; fixed serial tail |
| B: Lock Contention | 5.235551 | 10.806738 | 11.846649 | 3.128214 | 2.683643 | Negative scaling and severe lock contention; e(4) is lower than e(2) |
| C: Privatized State | 0.611395 | 0.320118 | 0.192403 | 0.047172 | 0.086260 | Good speedup and efficiency; e(4) above 0.05 |

## Experiment A — Serial Tail

`exp_a_serial.py`: 16 chunks of 2,000,000 iterations of `sin(i)*cos(i)`, preceded by a 0.40s sequential sleep.

| P | Runtime (s) | Speedup | Efficiency | Karp–Flatt | Checksum |
|---|---:|---:|---:|---:|---:|
| 1 | 3.882017 | 1.0000 | 100.00% | N/A | 6.1691618058 |
| 2 | 2.261262 | 1.7167 | 85.84% | 0.164993 | 6.1691618058 |
| 4 | 1.387859 | 2.7971 | 69.93% | 0.143346 | 6.1691618058 |

The identical checksums support computational consistency. The ratio e(4)/e(2) = **0.869**, within the instructor's required interval [0.80, 1.25]. This is consistent with a relatively stable serial fraction, although measured values are above the illustrative ~0.10–0.14 range at P=2.

## Experiment B — Lock Contention

`exp_b_contention.py`: 2,000,000 increments of a shared `Value` protected by a `Lock`.

| P | Runtime (s) | Speedup | Efficiency | Karp–Flatt | Count |
|---|---:|---:|---:|---:|---:|
| 1 | 5.235551 | 1.0000 | 100.00% | N/A | 2,000,000 |
| 2 | 10.806738 | 0.4845 | 24.22% | 3.128214 | 2,000,000 |
| 4 | 11.846649 | 0.4419 | 11.05% | 2.683643 | 2,000,000 |

The counter matches the intended total at every P. T4 > T1 and speedup is below 1 for P=2 and P=4, indicating negative scaling due to synchronization overhead. However, **e(4) < e(2)**, so the instructor's requirement that Karp–Flatt increase sharply from P=2 to P=4 is **not met**, despite severe contention.

## Experiment C — Privatization

`exp_c_fixed.py`: 20,000,000 increments accumulated in process-private counters, followed by a single reduction.

| P | Runtime (s) | Speedup | Efficiency | Karp–Flatt | Count |
|---|---:|---:|---:|---:|---:|
| 1 | 0.611395 | 1.0000 | 100.00% | N/A | 20,000,000 |
| 2 | 0.320118 | 1.9099 | 95.50% | 0.047172 | 20,000,000 |
| 4 | 0.192403 | 3.1777 | 79.44% | 0.086260 | 20,000,000 |

All counts are correct. T4 < T1 and E4 = **79.44%**, exceeding the instructor's >70% efficiency criterion. The Karp–Flatt value at P=4 is **0.086260**, above the handout's aspirational ≤0.03 threshold; this is reported rather than altered.

## Instructor sign-off checklist

| Requirement | Status | Evidence |
|---|---|---|
| A: e(4)/e(2) within [0.80, 1.25] | **PASS** | 0.143346 / 0.164993 ≈ 0.869 |
| B: T4 > T1 | **PASS** | 11.846649 > 5.235551 seconds |
| B: e(4) >> e(2) | **FAIL** | 2.683643 < 3.128214 |
| C: T4 < T1 | **PASS** | 0.192403 < 0.611395 seconds |
| C: E4 > 70% | **PASS** | 79.44% |
| All P=1,2,4 measurements provided | **PASS** | Three configurations for each experiment |
| Runs confirmed on student's Mac | **NOT VERIFIED** | Host details not supplied with these results |
| `git push origin practice-230103024` completed | **NOT VERIFIED** | No push confirmation supplied |

## Limitations and conclusion

The supplied timings are empirical single-run measurements; results may vary with hardware, process spawning, OS scheduling, and concurrent load. Experiment A shows the characteristic nearly stable Karp–Flatt metric of a serial tail. Experiment B shows strong negative scaling from lock contention, although its Karp–Flatt metric decreases between P=2 and P=4. Experiment C restores useful parallel speedup and exceeds the instructor's 70% efficiency requirement at four workers. Experiments B and C process different numbers of increments, so their total runtimes are not directly comparable as equivalent workloads.

To finalize the submission, add the actual host details above, commit this report and the scripts, and push the `practice-230103024` branch.
