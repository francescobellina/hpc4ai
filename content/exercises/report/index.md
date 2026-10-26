# Exercises for the report

These are the laboratory exercises of the course that go into the individual
report. They are collected here with the theory, the meaning of each task, and
the technical specifications needed to carry them out.

Two exercises:

1. **The Basel problem** — floating-point arithmetic: single-precision partial
   sums of $\zeta(2)$, order of summation, truncation versus rounding error.
2. **Parallel Hello, World!** — how a parallel run is organized: OpenMP
   threads, MPI ranks, hybrid layout, Slurm scheduling.

The companion notebook [`report-exercises.ipynb`](../../report/notebooks/report-exercises.ipynb)
contains a runnable Python/NumPy version of Exercise 1 (partial sums,
convergence study, error plot) and reference material for Exercise 2 (Python
threading demo plus C, MPI and Slurm templates).

## How the report is written

Send the report as a single PDF at least two weeks before the exam; the report
is discussed during the oral examination. For each exercise:

- describe the implementation and the procedure used to validate it;
- include only **short** code excerpts that support the discussion, plus the
  commands needed to build and run;
- provide the **full source code separately** (private repository or shared
  folder);
- state **all parameters** that affect the result: problem size, numerical
  precision, iterations, dataset/model configuration.

For every performance measurement, record the machine: on WILSON the partition,
number and type of nodes, MPI ranks, OpenMP threads, CPU allocation, loaded
modules; on a laptop the processor model, OS and compiler version. Report
elapsed times **together with** the problem and resource sizes. Repeat short
runs when their variability is comparable with the differences studied.

Scaling definitions used throughout:

$$S_p = \frac{T_1}{T_p}, \qquad E_p = \frac{S_p}{p},$$

with $T_1$ the baseline time and $T_p$ the time on $p$ equivalent processing
elements. For **strong scaling** keep the global problem fixed; for **weak
scaling** keep the local work per processing element roughly constant and state
how the global problem grows.

---

## Exercise 1 — The Basel problem

### The mathematics

Pietro Mengoli (1650) asked whether the sum of inverse squares,

$$\zeta(2) = \sum_{n=1}^{\infty} \frac{1}{n^2} = \frac{1}{1^2} + \frac{1}{2^2} + \frac{1}{3^2} + \dots,$$

has a closed form. Euler (1734) showed it is exactly

$$\zeta(2) = \frac{\pi^2}{6} = 1.644934066848226436472415\dots$$

Since a computer cannot sum infinitely many terms, define the partial sum

$$S(N) = \sum_{n=1}^{N} \frac{1}{n^2}.$$

The goal is to verify numerically that $S(N) \to \pi^2/6$ and to study **how the
order of the operations changes the result**.

### The floating-point idea

Single precision (binary32, NumPy `float32`) stores about **7 decimal digits**:
machine epsilon is

$$\varepsilon \approx 1.19 \times 10^{-7}, \qquad \varepsilon = 2^{-23}.$$

Two error sources compete:

- **Truncation error** — we drop the tail:
  $\pi^2/6 - S(N) \approx \displaystyle\int_N^\infty \frac{dx}{x^2} = \frac{1}{N}$.
  It shrinks like $1/N$.
- **Rounding error** — each addition rounds to the nearest representable
  `float32`. The worst case grows like $N\varepsilon$, and the practical effect
  is that **adding a tiny term to a large running sum loses those bits**.

Direct order (small $n$ first) grows the partial sum to $\approx 1.64$ quickly.
Once $1/n^2$ drops below $\varepsilon \cdot S \approx 2\times10^{-7}$, i.e.
around $n \approx 2200$, the added terms no longer change the sum: the direct
sum **stops improving** even though we keep adding terms.

Reverse order (large $n$ first) adds the smallest terms while the running sum is
still small, so each addition keeps its relative precision. It tracks the
truncation error much further and approaches the exact value.

The exercise is therefore about **where truncation dominates, where rounding
takes over, and why the summation order matters**.

### Technical specifications

The code must:

- accept $N$ as a command-line argument (or a notebook parameter);
- sum in **direct** or **reverse** order, selected at runtime;
- print $N$, the computed partial sum (single precision) and its **absolute
  error** with respect to $\pi^2/6$, with the error computed in **double
  precision**;
- use a machine-readable, one-line record so results can be plotted.

Precision must be unambiguous. In C: state the compiler and options, e.g.

```bash
gcc -O2 -Wall -Wextra -o basel basel.c -lm
```

Do **not** silently rely on options that reorder floating-point operations
(`-ffast-math`, `-Ofast`): they change the very thing being measured. In Python
/NumPy: declare the array dtype (`np.float32`) and compute the reference error in
`np.float64`.

Cost and memory: an array of $10^9$ `float32` values needs **4 GB**, and a pure
Python loop to $N=10^9$ takes tens of minutes. Process the terms **in chunks**
(the notebook uses chunks of $2^{20}$) or cap the largest $N$.

### Convergence study

Sample $N$ up to about $10^8$–$10^9$ and plot the absolute error versus $N$ for
both orders (log–log is natural). Use **log-spaced** $N$, because the error
scales as a power of $N$. Discuss:

- the range where truncation ($\approx 1/N$) dominates, and where rounding takes
  over;
- the $N$ where each order stops improving, and how that value follows from
  machine epsilon.

### Optional — SIMD intrinsics

Write a SIMD version (AVX on x86, NEON on ARM/Apple silicon) and compare speed
and accuracy with the scalar version. Check the supported instruction set
(`lscpu` on Linux). On WILSON the `lab4` partition mixes processor generations:
run timings in a batch job on a compute node and pin the node type with
`--constraint`.

### Report checklist

- the precision used (compiler options, or Python/NumPy types);
- how close the single-precision sum gets to $\pi^2/6$, and whether the direct
  and reverse sums agree;
- the sampling of $N$ and the plot of absolute error versus $N$ for both orders;
- the discussion: where truncation and rounding dominate, and where each order
  stops improving.

---

## Exercise 2 — Parallel Hello, World!

### The idea of the exercise

Write a small program that reports **how a parallel run is organized**: which
processes and threads are started and on which nodes they run. Besides
introducing OpenMP, MPI and Slurm, the program is a **diagnostic tool**: running
it with the same Slurm request and environment as a real calculation shows
whether the processes and threads are laid out as intended.

### Shared memory (OpenMP)

Threads share one address space inside a single process. The number of threads
is controlled by `OMP_NUM_THREADS`. Reference program:

```bash
export OMP_NUM_THREADS=4
/srv/software2/lab/bin/hello_shared_world
```

Write a similar C program (OpenMP preferred, `pthread` otherwise) or a Python
script. Each **thread** prints one line with at least: its thread number, the
total number of threads, and the compute-node name. Test different
`OMP_NUM_THREADS` and verify **exactly one line per thread** (order is not part
of the result).

Note: Python's `threading` module reproduces the thread *hierarchy*, but ordinary
Python code is limited by the GIL and does not necessarily run concurrently on
multiple cores. C with OpenMP does.

### Distributed memory (MPI) and hybrid

MPI ranks are **separate processes** (possibly on different nodes), started and
communicated through `mpiexec`/`srun`. Reference hybrid program:

```bash
mpiexec -n 4 /srv/software2/lab/bin/hello_parallel_world
```

Extend the program so that **every MPI process also creates its OpenMP
threads**. Each thread prints one line with: MPI rank and number of ranks,
thread number and number of threads in that process, and the compute-node name.
Optionally report the CPU-affinity mask.

For $P$ ranks and $T$ threads per rank the program must print **$P \times T$
lines**. Validate: every rank present, each rank has thread indices $0 \dots
T-1$, and changing `OMP_NUM_THREADS` changes the threads, not the number of MPI
processes.

### Technical specifications

Modules on WILSON before compiling an MPI program (hierarchical environment):

```bash
module use /srv/software/easybuild/hmns/x86-64-v2/modules/all/Core
module load GCC/13.2.0
module load OpenMPI/4.1.6
```

Compile (illustrative names):

```bash
gcc  -fopenmp hello_shared_world.c -o hello_shared_world
mpicc -fopenmp hello_parallel_world.c -o hello_parallel_world
```

Useful calls:

- node name — `MPI_Get_processor_name` (MPI), `gethostname` (`<unistd.h>`),
  `socket.gethostname` (Python);
- affinity mask — `sched_getaffinity` (`<sched.h>`),
  `os.sched_getaffinity` (Python; not available on macOS).

### Running on compute nodes (Slurm)

The login-node tests are only for very short checks. Real runs go through
**Slurm** with a batch script that loads the same modules used to compile and
launches the program with `srun`. Write three kinds of script:

- **OpenMP run** — one task with several CPUs: `--cpus-per-task=T` and
  `export OMP_NUM_THREADS=$SLURM_CPUS_PER_TASK`;
- **MPI run** — several tasks with one CPU each: `--ntasks=P`,
  `--cpus-per-task=1`, `OMP_NUM_THREADS=1`;
- **hybrid run** — several tasks with several CPUs each, on **two nodes**:
  `--nodes=2 --ntasks=P --cpus-per-task=T`.

For each run check that the number of output lines, the ranks, the thread
numbers and the node names agree with the Slurm request.

### Report checklist

- the shared-memory program and its output for different `OMP_NUM_THREADS`,
  showing one line per thread;
- the hybrid MPI + OpenMP program and the commands used to build and launch it;
- the validation runs with one and several ranks and different thread counts,
  including the $P \times T$ line check, the ranks, and the thread indices;
- the batch scripts and output of the OpenMP, MPI and hybrid runs on the compute
  nodes;
- the CPU-affinity masks, if you reproduce that part of the reference output.
