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
| 3 | WILSON `wnode01` (serial), `wnode04` (OpenMP): 2 × Xeon E5-2650, 8 cores/socket | `GCC/13.2.0` |
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

All 13 checks pass on WILSON (log `results/es02/es02_collect_20261116_124412.txt`):
OpenMP with 1, 2, 4 and 8 threads and six `mpiexec` layouts (1 × 1 to 4 × 1) on the
login node, and the three Slurm jobs, all `COMPLETED 0:0`.

:::{table} Slurm runs on partition `lab4` with `--hint=nomultithread`; masks from `--cpu-bind=verbose`.
:name: r-tab-es02

| Run | Request | Lines | Nodes | CPUs per task (mask) |
|---|---|---|---|---|
| OpenMP (job 61828) | 1 task × 4 CPUs | 4 | `wnode25` | 0–3 (`0xf`) |
| MPI (job 61829) | 4 tasks × 1 CPU | 4 | `wnode25` | 0, 16, 1, 17 |
| Hybrid (job 61830) | 2 nodes × 2 tasks × 4 CPUs | 16 | `wnode26`, `wnode27` | 0–3 and 4–7 on each node |
:::

On `wnode25` CPUs 0–15 are the physical cores of socket 0 and 16–31 those of
socket 1, so every thread gets its own physical core, and without `--distribution`
the MPI ranks alternate between the sockets. On the login node, `mpiexec` instead
binds each rank to one core when there are at most two ranks and to a whole socket
when there are more, which is the Open MPI 4 default. Login-node tests therefore
check the program, not the placement.

## Exercise 3 — Tiny stories, many threads

### Task and implementation

`llama2.c` (`run.c`, supplied by the course) generates a story one token at a time.
Every token is a forward pass that multiplies each weight matrix of the model by a
vector, so each token reads all the weights once and performs one multiplication
and one addition per weight. In the ideal case $p$ threads give $p$ times the
speed, until together they ask for more data than the memory of the node can
deliver. From then on the speed is capped at (node bandwidth) / (bytes per token).

The profile of the serial program points at `matmul`. Each output row of
`matmul` is an independent dot product, so the rows are shared among the threads
with one `#pragma omp parallel for` (`run_omp_mm.c`). The attention heads are also
independent: `run_omp.c` parallelizes their loop as well. The remaining parts of
the forward pass (`rmsnorm`, RoPE, residuals, SwiGLU) are short loops and stay
serial.

```c
#pragma omp parallel for private(i)
for (i = 0; i < d; i++) {          // rows of xout are split among threads
    float val = 0.0f;
    for (int j = 0; j < n; j++) val += w[i * n + j] * x[j];
    xout[i] = val;
}
```

```bash
module load GCC/13.2.0
gcc -O3 -o run run.c -lm
gcc -O3 -fopenmp -o run_omp run_omp.c -lm
OMP_NUM_THREADS=$T OMP_PLACES=cores OMP_PROC_BIND=spread \
    srun --ntasks=1 --cpus-per-task=16 --cpu-bind=cores \
    ./run_omp stories110M.bin -t 0 -n 256 -i "Once upon a time"
```

All runs use one exclusive `sandy_bridge` node of partition `wilson`
(2 × Xeon E5-2650, 8 cores per socket, 20 MiB of L3 per socket, two NUMA nodes),
`--hint=nomultithread`, greedy decoding (`-t 0`), at most 256 steps and the prompt
"Once upon a time". The stories end earlier with the end-of-sequence token, after
222 steps (15M) and 243 steps (110M). The serial baseline ran on `wnode01`
(job 61832) and the OpenMP runs on `wnode04` (job 62659). Every point is
repeated 3 times; the spread between repetitions is below 1.3%, and 2.5% for 15M
at 16 threads.

### Validation

With greedy decoding the three serial repetitions of each model print the same
text, and all 92 OpenMP runs (1 to 16 threads, both versions, `spread` and
`close`) print exactly the same text as the serial program (`cmp`). The result is
bit-identical because the threads split the rows, not the sums inside a row: every
dot product is summed by one thread in the serial order. All 96 job steps are
`COMPLETED 0:0`. `sacct` reports the job itself as `FAILED 1:0`, but that comes
from the last line of the script, a `grep -c` with zero matches under
`set -o pipefail`: it signals that no text differed.

### Results

:::{table} Serial program (one core, `wnode01`) and weight bytes read per token from the model configuration. Effective bandwidth = tok/s × bytes per token.
:name: r-tab-es03-serial

| Model | tok/s (mean of 3) | `matmul` share (`gprof`, `-fno-inline`) | Weights read per token | Effective bandwidth |
|---|---|---|---|---|
| 15M | 58.50 | 96.85% | 60.77 MB | 3.55 GB/s |
| 42M | 20.71 | — | 166.76 MB | 3.45 GB/s |
| 110M | 7.81 | 97.61% | 438.12 MB | 3.42 GB/s |
:::

Even the smallest model is larger than the 40 MiB of L3 of the whole node, so the
weights are read from memory at every token. The keys and values of the attention
add 2–3% and are left out of the estimate. The STREAM triad kernel gives 12.65 GB/s
on one core and 51.4 GB/s on the 16 cores of `wnode01`: the serial program uses
only 27–28% of what one core can draw.

:::{table} OpenMP scaling on `wnode04` (`spread`, mean of 3 runs): speedup against the serial program and effective bandwidth.
:name: r-tab-es03-scaling

| Threads | 15M $S_p$ | 42M $S_p$ | 110M $S_p$ | 110M $E_p$ | 110M GB/s | `run_omp_mm` 110M $S_p$ |
|---|---|---|---|---|---|---|
| 1 | 0.96 | 0.98 | 0.98 | 0.98 | 3.4 | 0.98 |
| 2 | 1.80 | 1.84 | 1.85 | 0.93 | 6.3 | 1.82 |
| 4 | 3.30 | 3.48 | 3.53 | 0.88 | 12.1 | 3.37 |
| 8 | 4.92 | 5.43 | 5.78 | 0.72 | 19.8 | 5.20 |
| 16 | 5.20 | 6.53 | 7.11 | 0.44 | 24.3 | 6.34 |
:::

:::{figure} ../esercizi/figures/es03-scaling.png
:name: r-fig-es03-scaling
:width: 90%

Tokens per second (left) and speedup against the serial program (right) for the
three models. Solid lines: `run_omp` (`matmul` and heads); dashed lines:
`run_omp_mm` (`matmul` only).
:::

:::{figure} ../esercizi/figures/es03-banda.png
:name: r-fig-es03-bandwidth
:width: 90%

Effective bandwidth of `run_omp` against the triad bandwidth of the node (open
diamonds: `spread` on `wnode01`; filled diamonds: `close` on `wnode04`).
:::

### Discussion

- **The serial program is not memory bound.** All three models read their weights
  at the same 3.4–3.6 GB/s, a quarter of the single-core triad bandwidth. Without
  `-ffast-math` the compiler must keep the floating-point sums of the dot product in
  order, so every addition waits for the previous one. GCC 16 on the Mac vectorizes
  only the multiplications and keeps an in-order reduction; this is a different
  compiler and architecture from WILSON, but the ordering rule is the same. With
  the 3-cycle latency of a `float` addition on Sandy Bridge (A. Fog, *Instruction
  tables*), at most one weight is processed every 3 cycles, 3.7 GB/s at 2.8 GHz,
  close to the measured value. The core frequency during these runs was not
  measured. Each extra thread adds an independent chain of additions while the
  memory still has spare bandwidth, which is why scaling is almost ideal up to
  4 threads.
- **The three models do not scale the same way.** At 16 threads the speedup is
  5.2, 6.5 and 7.1. Each forward pass opens $7L+1$ or $8L+1$ parallel regions
  ($L$ layers), and each region has a fixed cost for starting and synchronizing the
  threads. The 15M model has the least work per region: at 16 threads a region
  lasts 67 µs on average, about as long as at 8 threads (71 µs), and 15M gains only
  5.7% from 8 to 16 threads.
- **The memory bandwidth is not the limit either.** At 16 threads the 110M model
  reads 24.3 GB/s, 47% of the node's triad bandwidth, and the bandwidth per thread
  falls from 3.4 to 1.5 GB/s. With 8 threads packed on one socket (`close`,
  single run) the 110M model is 4.7% faster than with `spread`, although triad
  gives only 25.6 GB/s on one socket. Amdahl's law with the serial share of the
  profile would allow a speedup of 11.8 at 16 threads for `run_omp_mm`, against
  6.3 measured. The Karp–Flatt serial fraction grows from 0.06 at 4 threads to
  0.10 at 16, so the loss grows with the number of threads. Compatible causes that
  were not measured separately are the barriers of the parallel regions, the lower
  clock with all cores active (2.40 GHz measured in Exercise 5) and the NUMA
  placement of the `mmap`-ed weights, which sit wherever the page cache put them.
- **Parallelizing the attention heads** adds 4%, 6% and 12% at 16 threads. The
  attention takes at most 1.6–2.3% of the serial time, but that serial share
  matters more and more as the rest speeds up.

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
`sandy_bridge` nodes of WILSON, always with exclusive nodes (one for the
single-node runs, up to all eight for scaling), starting from the course batch
scripts and changing one aspect at a time. Every run was kept with its input
file, batch script and output; all 36 HPL runs report `PASSED` (largest residual
$5.3 \times 10^{-3}$ against a threshold of 16) and all 21 HPCG runs `VALID`; all 57
jobs ended `COMPLETED 0:0`.

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

The problem size $N = 41280$ (12.7 GiB) was chosen from the size series: going from
12288 to 24576 gains 16.7%, from 24576 to 41280 only 8.2%, at 84% of peak. A
full-memory run with $N = 82560$ (50.8 GiB, run `R01`, 2 × 8) reaches
268.3 GFLOP/s, **87.4%** of peak, only 3.1% above $N = 41280$ but 7.8 times longer
(1398 s). The layout ranking was not re-checked at $N = 82560$.

### Scaling

**The question.** If we double the resources, does the work go twice as fast? In
the ideal case the efficiency, the rate per node compared with one node alone,
stays at 1. In practice the nodes must exchange data over the network, and that
cost does not shrink when nodes are added. We tested two ways of growing, up to the
8 `sandy_bridge` nodes of the partition: a fixed problem (strong scaling) and a
problem that grows with the nodes (memory-scaled HPL with $N \propto \sqrt{p}$, weak
HPCG with a fixed 104³ grid per process). Each node runs the best single-node
layout: 2 × 8 for HPL and 16 × 1 for HPCG. There is one run per point; all 12 HPL
runs report `PASSED` and all 15 HPCG runs `VALID`.

:::{table} Efficiency per node relative to one full node (HPL: $T_1/(k\,T_k)$ for strong and $R_k/(k R_1)$ for memory-scaled; HPCG: $R_k/(k R_1)$ on the validated rate, 60 s requested).
:name: r-tab-es05-scaling

| Nodes | HPL strong, $N$ = 41280 | HPL memory-scaled | HPCG weak, 104³ per process | HPCG strong, 256³ |
|---|---|---|---|---|
| 1 | 1.00 (179.9 s) | 1.00 ($N$ = 41280) | 1.00 (8.70 GFLOP/s) | 1.00 (8.64 GFLOP/s) |
| 2 | 0.80 (112.1 s) | 0.87 ($N$ = 58368) | 0.95 (16.53) | 0.98 (16.90) |
| 4 | 0.66 (68.2 s) | 0.85 ($N$ = 82560) | 0.81 (28.27) | 0.44 (15.33) |
| 8 | 0.27 (82.2 s) | 0.55 ($N$ = 116736) | 0.64 (44.63) | 0.18 (12.10) |
:::

:::{figure} ../esercizi/figures/es05-hpl-scaling.png
:name: r-fig-hpl-scaling
:width: 90%

HPL. Left: **strong scaling** (fixed matrix, $N = 41280$), speedup over one core
(log axes; dashed: ideal). Right: efficiency relative to one node for strong
scaling and, for comparison, for the **memory-scaled** runs, where $N$ grows as
$\sqrt{p}$.
:::

**HPL.** At fixed $N$ the time falls from 180 s on one node to 68 s on four
(688 GFLOP/s, the best absolute value), then *rises* to 82 s on eight nodes: each
process holds only 0.8 GiB of the matrix, so computation shrinks while panel
broadcasts and pivot-row swaps do not. Growing the matrix with the nodes keeps the
efficiency at 0.85 up to four nodes. On eight nodes both series drop sharply
(memory-scaled 0.55, 1144 GFLOP/s, 927 s against 509 s expected at constant
efficiency). Two things change at eight nodes, the process grid (4 × 4 instead of
2 × 4) and the use of all eight nodes, and with one run per point we cannot tell
these causes apart. Inside a node the one-core run reaches 108% of the 2.40 GHz
per-core peak, because turbo raises the clock when few cores are active; efficiency
is therefore quoted relative to a full node.

:::{figure} ../esercizi/figures/es05-hpl-memory.png
:name: r-fig-hpl-memory
:width: 100%

HPL **memory-scaled** study (not strong scaling): runs `S016`, `M02`, `M04`, `M08`;
$p$ is the number of MPI processes (2 per node, 8 threads each). Dashed lines:
predictions; dots: measured runs. (a, d) $N$ on the curve $N_1\sqrt{p/p_1}$.
(b, e) Total GFLOP/s against the ideal $R_1\,p/p_1$ (efficiency 1) and the
theoretical peak, with the efficiency $E$ of each run. (c, f) Relative to the
one-node run: memory per process (constant), work per process ($\propto \sqrt{p}$,
the time at efficiency 1) and measured time, $1/E$ times longer. Top row: linear
axes; bottom row: log-log axes, where a power law $p^a$ is a straight line of
slope $a$. Figure labels are in Italian.
:::

The memory-scaled runs keep the matrix storage per process fixed at 6.35 GiB, but
the arithmetic work per process grows as $\sqrt{p}$ (×2.83 on eight nodes). A time
estimate based on memory alone would therefore predict 180 s on every node count;
the ideal time on eight nodes is already 509 s, and the measured one is 927 s. Up to
four nodes the measured times follow the $\sqrt{p}$ prediction with a nearly
constant overhead of 15–18%; on eight nodes they depart from it.

:::{figure} ../esercizi/figures/es05-hpcg-tempi.png
:name: r-fig-hpcg-times
:width: 90%

HPCG strong scaling (global grid 256³): share of benchmark time in the multigrid
(MG), sparse matrix-vector product (SpMV), dot products with global sum (DDOT) and
vector updates (WAXPBY).
:::

**HPCG.** Inside a node HPCG almost stops scaling before the cores run out: going from 8 to
16 processes raises the bandwidth reported by HPCG only from 58.7 to 67.5 GB/s, and
the rate by 17%. Across nodes each node adds its own memory bandwidth, so weak
scaling reaches 44.6 GFLOP/s on eight nodes (efficiency 0.64). In strong scaling the
best rate is on two nodes (16.9 GFLOP/s); beyond that the rate falls although the
multigrid keeps scaling (17.7, 30.1 and 50.3 GFLOP/s on 2, 4 and 8 nodes), because the global sums in
`DDOT` (`MPI_Allreduce`, a synchronisation point at every iteration) grow from 3% to
50% and 77% of the time. The data summed are a few numbers, so the cost is latency
and waiting for the slowest process; the logs do not separate the two.

:::{table} Best results against the theoretical peak (307.1 GFLOP/s per node at 2.40 GHz).
:name: r-tab-es05-final

| Nodes | HPL (GFLOP/s) | HPL / peak | HPCG (GFLOP/s) | HPCG / peak |
|---|---|---|---|---|
| 1 | 268.3 ($N$ = 82560) | 87.4% | 8.70 | 2.83% |
| 8 | 1144.0 ($N$ = 116736) | 46.6% | 44.63 (weak) | 1.82% |
:::

HPL stays about 30 times closer to the peak than HPCG at every node count. Both lose
efficiency on eight nodes for different reasons: HPL in the step from four to eight
nodes, HPCG first inside the node (memory bandwidth) and then across nodes (global
reductions).

## Summary

:::{table} Key results.
:name: r-tab-summary

| Exercise | Key result | Validation |
|---|---|---|
| 1 — Basel | `float32` direct sum stalls at $\Delta = 2.09 \times 10^{-4}$; reverse order reaches $\approx 9 \times 10^{-9}$ | passed (macOS client) |
| 2 — Parallel Hello | $P \times T$ lines in every layout; one physical core per thread in the Slurm runs | 13/13 checks, 3 jobs `COMPLETED 0:0` |
| 3 — Tiny stories | serial 58.5 / 20.7 / 7.8 tok/s, weights read at 3.4 GB/s; OpenMP speedup at 16 threads 5.2 / 6.5 / 7.1, at most 24.3 of 51.4 GB/s | identical text in 92/92 runs |
| 4 — Profiling | loop swap: 3.83× overall, 10.3× on the hotspot; IPC from 0.52 to 2.12 | passed, bit-identical checksums |
| 5 — HPL/HPCG | one node: HPL 85–87% of peak, HPCG 2.8%; eight nodes: HPL 1144 GFLOP/s (47%), HPCG 44.6 GFLOP/s (1.8%) | 36 HPL `PASSED`, 21 HPCG `VALID` |
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
| 3 | `codes/exec3/` | `run.c` (course), `run_omp.c`, `run_omp_mm.c`, `config.c`, `triad.c`, `es03.sh`, `omp_job.sh`, `analyze_es03.py` |
| 4 | `codes/exec4/` | `preprocess.c`, `preprocess_rows.c`, `es04_all.sh` (job used for all measurements) |
| 5 | `codes/exec5/` | `es05.sh` (setup, runs, collection on WILSON), `analyze_es05.py` (tables and figures) |
