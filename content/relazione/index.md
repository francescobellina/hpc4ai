---
title: HPC4AI — Laboratory report
subtitle: High-Performance Computing for AI Applications in Physics
short_title: Report (EN)
authors:
  - name: Francesco Bellina
numbering:
  heading_2: true
  heading_3: true
exports:
  - format: pdf
    template: plain_latex
    output: ../../exports/hpc4ai-report.pdf
    id: hpc4ai-report-pdf
---

:::{warning} Draft
This report is being assembled from the laboratory notebook (Part II of this book,
in Italian). Sections marked **To be completed** wait for runs that are still
missing. Every number below comes from a logged run; nothing is estimated unless
stated.
:::

## Introduction

This report summarizes the exercises for the report of the HPC4AI course. For each
exercise it gives the implementation, the validation procedure, the main results
and their discussion, following the course checklist. Short code excerpts support
the discussion; the full source code, batch scripts and analysis scripts are in the
project repository, one folder per exercise (`codes/exec1/` … `codes/exec5/`), and
the raw logs are in `results/`.

### Computing environment

Unless stated otherwise, runs were performed on the WILSON cluster
(`wilson.mib.infn.it`) through Slurm. The machine and the allocation of each
exercise are listed in its own section.

:::{table} Machines used in this report.
:name: r-tab-machines

| Exercise | Machine | Software |
|---|---|---|
| 1 | macOS client, Apple M3 Pro (arm64) | Apple clang 21.0.0; Python 3.12.14, NumPy 2.5.3 |
| 2 | WILSON, partition `lab4` (to be completed) | `GCC/13.2.0`, `OpenMPI/4.1.6` |
| 4 | WILSON `wnode25`: 2 × Xeon E5-2683 v4, 16 cores/socket | system `gcc` 11.5.0, `perf` 5.14.0 |
| 5 | WILSON `wnode01`–`08`: 2 × Xeon E5-2650, 8 cores/socket | `GCC/13.2.0`, `OpenMPI/4.1.6`, `HPL/2.3`, `HPCG/3.1` |
:::

## Exercise 1 — The Basel problem

### Task and implementation

The partial sums $S(N) = \sum_{n=1}^{N} 1/n^2$ converge to $\pi^2/6$. The C program
`basel_naive.c` reads $N$, the summation order (direct $1 \to N$ or reverse
$N \to 1$) and the precision (`float32` or `float64`) from the command line,
accumulates the sum in the requested type, and prints $N$, the sum and the absolute
error $\Delta = |S(N) - \pi^2/6|$, computed in double precision:

```c
if (reverse)
    for (long n = N; n >= 1; --n) sum += 1.0f / ((float)n * (float)n);
else
    for (long n = 1; n <= N; ++n) sum += 1.0f / ((float)n * (float)n);
printf("%ld %d %.9f %.6e\n", N, reverse, (double)sum,
       fabs((double)sum - exact));
```

```bash
gcc -O2 -Wall -Wextra -o basel basel_naive.c -lm
./basel 1000000 0 1     # N = 10^6, direct order, float32
```

No `-ffast-math`: it would reorder the sum, which is the quantity under study.
$N$ is sampled log-uniformly from $10$ to $10^9$. There are no random seeds or
stopping criteria.

### Validation

The reference $\pi^2/6 = 1.644934066848226$ is computed from `M_PI` in double
precision. In `float64` both orders must agree and follow the truncation error
$\approx 1/N$; in `float32` the direct sum must stall once $1/n^2 < \varepsilon\,S$,
i.e. around $n \approx 1/\sqrt{\varepsilon S} \approx 2200$.

### Results

:::{table} Partial sum and absolute error at $N = 10^6$.
:name: r-tab-basel

| Precision | Order | $S(N)$ | $\Delta$ |
|---|---|---|---|
| `float32` | direct | 1.644725323 | 2.087441e-04 |
| `float32` | reverse | 1.644932985 | 1.081542e-06 |
| `float64` | direct | 1.644933067 | 9.999995e-07 |
| `float64` | reverse | 1.644933067 | 9.999995e-07 |
:::

:::{figure} ../esercizi/figures/basel-error-vs-N.png
:name: r-fig-basel
:width: 85%

Absolute error versus $N$ for both precisions and both orders (log–log). Dashed
line: truncation error $\approx 1/N$; dotted lines: machine epsilon of `float32`
and `float64`.
:::

### Discussion

- **Truncation dominates** as long as the added terms are representable: all four
  curves follow $1/N$ up to $N \approx 2 \times 10^3$.
- **Rounding dominates the direct `float32` sum** beyond that point: the error
  stalls at $2.09 \times 10^{-4}$, because each new term is smaller than half an
  ulp of the running sum and is lost.
- **Summing in reverse order** adds the small terms first, keeps the relative
  precision, and follows truncation down to $\approx 9 \times 10^{-9}$ before
  flattening.
- In `float64` the order is irrelevant up to $N \approx 10^8$; the error follows
  $1/N$ down to $\approx 10^{-9}$.

**To be completed:** rerun on WILSON for a uniform compiler/CPU pairing;
(Optional) SIMD version.

## Exercise 2 — Parallel Hello, World!

### Task and implementation

A diagnostic program reports how a parallel run is organized. The shared-memory
version (`hello_shared_world.c`) prints one line per OpenMP thread with the thread
index, the number of threads and the node name. The hybrid version
(`hello_parallel_world.c`) starts $P$ MPI ranks, each creating $T$ OpenMP threads,
and prints rank, number of ranks, thread index, threads per process and node name.

```bash
module load GCC/13.2.0 OpenMPI/4.1.6
gcc   -fopenmp hello_shared_world.c   -o hello_shared_world
mpicc -fopenmp hello_parallel_world.c -o hello_parallel_world
```

### Validation

A run is accepted if it prints exactly one line per thread ($P \times T$ lines in the
hybrid case), every rank $0 \dots P-1$ appears with threads $0 \dots T-1$, and the
counts and node names match the Slurm request (`--nodes`, `--ntasks`,
`--cpus-per-task`). Changing `OMP_NUM_THREADS` must change only the threads,
changing the number of tasks only the ranks.

### Results

**To be completed:** batch scripts and outputs of the OpenMP, MPI and hybrid runs
on WILSON, with the line counts and the CPU-affinity masks. So far only a local
Python check has been run; it reproduces the thread hierarchy but, because of the
GIL, is not evidence of parallel execution.

## Exercise 3 — Tiny stories, many threads

**To be completed.** The exercise has not been run yet.

## Exercise 4 — Profiling and optimizing data preparation

### Setup

`preprocess.c` generates a synthetic row-major dataset ($N$ observations × $D$
features, `data[i*d+j]`), computes mean and population variance of each feature,
standardizes the values and computes a linear score per observation. Benchmark size:
$N = 65536$, $D = 256$ (128 MiB per matrix), 5 repetitions. Compilation, on the login
node, with the system compiler:

```bash
gcc -O2 -g -fno-inline -fno-omit-frame-pointer -Wall -Wextra \
    preprocess.c -lm -o preprocess
```

All measurements come from one Slurm job (`61207`, `wnode25`, one physical core,
1 GiB, each step `srun --cpu-bind=cores`); an independent job (`61199`) reproduces
them.

### Prediction

Reading the source, one repetition moves about 2688 MiB, of which 2048 MiB (76%) in
`compute_statistics`: it is the only function that walks the matrix by columns, twice,
with a 2048-byte stride that uses 8 of the 64 bytes of each cache line. The
prediction was therefore that `compute_statistics` dominates, with a share of the
order of its share of the traffic.

### Profile and optimization

The `perf record` profile of the original confirms the hotspot:
`compute_statistics` has **83.61%** of the `Self` samples (183 samples; 86.62% with
30 repetitions and 1069 samples). With $f = 0.836$, Amdahl's law bounds the speedup
obtainable by accelerating only this function to $1/(1-f) = 6.1\times$.

The optimized copy (`preprocess_rows.c`) swaps the loops so that the inner loop
visits the features of one observation contiguously, with one running sum per feature
and two passes (all means first, then all variances):

```c
for (size_t i = 0; i < n; ++i)          /* was: for j { for i } */
    for (size_t j = 0; j < d; ++j)
        mean[j] += data[i*d+j];         /* stride +8 B instead of +2048 B */
```

For each feature the additions happen in the same order $i = 0, \dots, N-1$, so the
results are identical to the bit.

### Validation

Both versions pass the built-in check (`1024 32 1 check` and `65536 256 1 check`:
$\max|\mu_j| \le 2.4 \times 10^{-14}$, variance error $\le 1.2 \times 10^{-11}$). The
full-problem checksums are identical ($2261357.7191473623$, $|a-b| = 0$, well within
the required $10^{-8} + 10^{-10}|a|$).

### Results

:::{table} Elapsed time of `65536 256 5` (bash `time`), three runs per version, job `61207`.
:name: r-tab-es04

| Version | Run 1 (s) | Run 2 (s) | Run 3 (s) | Median (s) | Hotspot `Self` |
|---|---|---|---|---|---|
| Original | 1.902 | 1.901 | 1.902 | **1.902** | `compute_statistics` 83.61% |
| Row traversal | 0.497 | 0.497 | 0.498 | **0.497** | `compute_statistics` 31.91% |
:::

The overall speedup is $1.902 / 0.497 = \mathbf{3.83\times}$ (3.82× in job `61199`).
`compute_statistics` alone becomes 10.3× faster, while the untouched phases keep the
same number of samples. Hardware counters (`perf stat -r 3`) show the cause: the
instruction count is almost unchanged (−2.8%), but cache misses drop 4.91× and the
IPC rises from 0.52 to 2.12.

### Discussion

The measured 3.83× is below the 6.1× Amdahl bound because the bound assumes an
infinitely fast hotspot: with the measured 10.3× acceleration of the hotspot, Amdahl
predicts 4.59×, close to the measured user-space speedup (4.53×); the remaining gap
is the almost constant non-user time (system time and process start-up, ≈ 0.07 s),
which the sampled user-space profile does not see. The estimate is approximate
because $f$ comes from a sampled profile (±0.027 at 183 samples, i.e. a bound
between 5.2× and 7.3×) and depends on the number of repetitions. After the change the
time is spread over four phases with contiguous access; the next step would be to
reduce the number of passes over the 128 MiB matrix (loop fusion).

## Exercise 5 — Benchmarking and scaling with HPL and HPCG

### Setup

HPL (`HPL/2.3`, `NB` = 192) and HPCG (`HPCG/3.1`, 60 s requested) were run on the
`sandy_bridge` nodes of WILSON, one exclusive node per run, starting from the course
batch scripts and changing one aspect at a time. Every run was kept with its input
file, batch script and output; all HPL runs report `PASSED` (largest residual
$5.3 \times 10^{-3}$ against a threshold of 16) and all HPCG runs `VALID`; all jobs
ended `COMPLETED 0:0`.

### Single node

:::{table} Best single-node results and theoretical peak (double precision).
:name: r-tab-es05-node

| Benchmark | Best layout (processes × threads) | Rate (GFLOP/s) | Fraction of peak |
|---|---|---|---|
| HPL, $N = 41280$ | 2 × 8 (one process per socket) | 260.3 ± 3.1 (3 runs) | 84.8% |
| HPCG, 416 × 208 × 208 | 16 × 1 (MPI only) | 8.70 | 2.83% |
:::

The peak uses the effective clock measured with `perf stat` during HPL (2.40 GHz):
$R_{\text{peak}} = 16 \text{ cores} \times 2.40\,\text{GHz} \times 8\,\text{flop/cycle}
= 307$ GFLOP/s per node (AVX, 4 doubles per instruction, one add and one multiply
per cycle, no FMA).

:::{figure} ../esercizi/figures/es05-hpl-layout.png
:name: r-fig-hpl-layout
:width: 90%

HPL at $N = 41280$ on one node, per split of the 16 cores (MPI processes × threads,
grid $P \times Q$): mean and standard deviation of 3 runs.
:::

For HPL every balanced layout is within 3.5% of the best, because almost all the time
is spent in `DGEMM`; the grid shape matters more (1 × 16 with 16 processes: −8.7%).
For HPCG only MPI pays off: the multigrid part does not use the threads, so with
1 × 16 the rate drops by 85%.

### Scaling

**To be completed** with the multi-node campaign (27 jobs submitted on 9 November
2026): HPL strong scaling at fixed $N$ and memory-scaled runs
($N_p \propto \sqrt{p}$); HPCG weak and strong scaling based on the validated rate,
$S_p^{(R)} = R_p/R_1$ and $E_p^{(R)} = S_p^{(R)}/p$, at the same requested duration.

## Summary

:::{table} Key results.
:name: r-tab-summary

| Exercise | Key result | Validation |
|---|---|---|
| 1 — Basel | `float32` direct sum stalls at $\Delta = 2.09 \times 10^{-4}$; reverse order reaches $\approx 9 \times 10^{-9}$ | passed (macOS client) |
| 2 — Parallel Hello | — | to be completed on WILSON |
| 3 — Tiny stories | — | not run |
| 4 — Profiling | loop swap: 3.83× overall, 10.3× on the hotspot; IPC from 0.52 to 2.12 | passed, bit-identical checksums |
| 5 — HPL/HPCG | one node: HPL 85% of peak, HPCG 2.8% | 24 HPL `PASSED`, 6 HPCG `VALID` |
:::

Exercises 4 and 5 show the same lesson from two sides: performance is set by how
data move through the memory hierarchy. HPL reuses each loaded value many times and
reaches 85% of the arithmetic peak; HPCG and the original `compute_statistics` touch
each value once or waste most of each cache line, and run far below it, limited by
memory bandwidth rather than by the floating-point units.

## Appendix — Source code

| Exercise | Folder | Content |
|---|---|---|
| 1 | `codes/exec1/` | `basel_naive.c` |
| 2 | `codes/exec2/` | OpenMP and hybrid programs, Slurm scripts, `checks.sh` |
| 4 | `codes/exec4/` | `preprocess.c`, `preprocess_rows.c`, `es04_all.sh` (job used for all measurements) |
| 5 | `codes/exec5/` | `es05.sh` (setup, runs, collection on WILSON), `analyze_es05.py` (tables and figures) |
