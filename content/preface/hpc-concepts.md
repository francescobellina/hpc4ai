# HPC concepts — a primer

This page is a vocabulary guide. It answers, in one place and in plain language,
the terms that show up in every HPC lecture, exercise and benchmark report:
*core*, *cache*, *thread*, *process*, *OpenMP*, *MPI*, *memory bandwidth*,
*O(n)*, *speedup*, and friends.

It is not course material and it does not replace it. Read it once now, so the
lectures can use the vocabulary without re-explaining it; come back to it when a
term blocks you.

The order below is the order in which the concepts depend on each other:
hardware first, then the memory hierarchy, then the cost model (complexity and
bandwidth), then parallelism, then the two tools (OpenMP and MPI).

---

## 1. The hardware ladder

**Core.** An independent execution unit inside the CPU. It has its own pipeline,
its own registers, and usually its own private L1 and L2 caches. A modern
processor has from a few to more than a hundred of them.

**Pipeline.** The core does not execute instructions one after another: it runs
them through a chain of stages (fetch, decode, execute, memory access, write
back), so several instructions are in flight at the same time, like cars on an
assembly line. Modern cores have dozens of stages, plus *superscalar* execution
(multiple instructions per clock cycle) and *out-of-order* execution (the core
runs whatever is ready, not what is written in the source).

**Clock.** A 3 GHz clock ticks every 0.33 ns. In that time light travels about
10 cm. This is the easiest way to remember that the physical distance between
core, caches and RAM is a performance parameter, not trivia.

**Hardware threads (SMT).** One core can expose two logical CPUs to the
operating system. The two share the execution units, so they do not double the
compute power; they help fill the idle slots left by memory waits. On
numeric, memory-bound HPC codes the gain is often close to zero.

**RAM (DRAM).** Main memory. Volatile, cheap, large, and much slower than the
logic in the core. Every bit is a capacitor that must be refreshed.

**GPU.** Thousands of simpler cores designed to run the same instruction on many
data at once. Excellent for data-parallel work, poor for code full of branches.

| Level | Typical size | Approx. latency | Cycles at 3 GHz |
|---|---|---|---|
| Registers | few KB | < 1 ns | 1 |
| L1 cache | 32-64 KB per core | ~1 ns | 4 |
| L2 cache | 256 KB - 2 MB per core | ~3-5 ns | 12 |
| L3 cache | 8 MB to >100 MB, shared | ~10-20 ns | 40 |
| RAM | tens to hundreds of GB | ~80-100 ns | 250-300 |
| NVMe SSD | hundreds of GB to TB | ~20-100 µs | tens of thousands |
| Spinning disk | TB | ~5-10 ms | millions |

:::{figure} figures/cache-hierarchy.png
:name: fig-cache-hierarchy
:width: 55%

The memory hierarchy of a modern machine: L1 and L2 are private to each core,
L3 is shared by all cores, and below sit RAM and external storage.
*Image: Wikimedia Commons, "Multi-level Cache Hierarchy diagram" by
Ferry24.Milan, CC BY-SA 4.0, via Wikipedia "Memoria cache".*
:::

**The memory wall.** Core speed has grown much faster than RAM speed. A modern
core executes hundreds of instructions in the time RAM needs for a single
answer. The CPU is a powerful pump attached to a narrow pipe: everything the
computation does with data goes through that pipe, and the pipe is the
bottleneck. This is why most scientific codes are **memory-bound**, not
compute-bound.

---

## 2. Cache memory

**The cache, in one sentence.** *A cache is a small, fast copy of data kept
close to the core, so that it does not have to go and look for it far away.*

- **copy** — the real content lives in RAM; the cache keeps a copy of what was
  used recently;
- **small** — from tens of KB (L1) to tens of MB (L3), against GBs of RAM;
- **close** — the closer to the core, the shorter the wire and the smaller the
  latency.

**Cache line.** The unit of transfer between cache and RAM: typically 64 bytes.
The cache never brings one byte: it brings the whole line, because the request
cost is dominated by latency, not by payload (64 bytes cost about as much to
fetch as 8), and because the neighbouring bytes are usually needed next.

**Hit and miss.** A *hit* is an access served by the cache; a *miss* is an
access that must go one level down. Misses come in three flavours:
*compulsory* (first ever access), *capacity* (the working set does not fit) and
*conflict* (the data would fit, but the set was full).

**Tag, index, offset.** The address is split into fields: *offset* (which byte
inside the line), *index* (which set to look in) and *tag* (which block of RAM
is really stored there). Example: a 32 KB L1 with 64-byte lines and 8-way
associativity has 32768 / (64 x 8) = 64 sets, so 6 index bits and 6 offset
bits; the rest of the address is the tag.

**Associativity.** How many places a block can occupy inside its set (the
*ways*). *Direct-mapped* (1 way) is the simplest but collides often;
*set-associative* (8 or 12-16 ways) is the standard, because all ways are
searched in parallel; *fully associative* is used only for small structures such
as the TLB.

:::{figure} figures/cache-operation.png
:name: fig-cache-operation
:width: 60%

How a cache answers a request: the processor sends an address, the cache
compares the stored tags, and on a miss it loads the block from main memory.
*Image: Wikimedia Commons, "Cache operation diagram" by Ferry24.Milan,
CC BY-SA 4.0, via Wikipedia "Memoria cache".*
:::

**Locality.** Two regularities make the hierarchy work:

- *temporal locality*: a value used now is likely used again shortly;
- *spatial locality*: a value used now makes its neighbours likely to be used.

The hardware *prefetcher* exploits this: it recognises regular patterns
(sequential or constant stride) and loads data in advance. Random access, such
as following scattered pointers, defeats it completely.

**Write policies.** *Write-through* sends the write to RAM immediately (simple,
lots of traffic); *write-back* keeps it in the cache and marks the line *dirty*,
flushing it only when the line is evicted. Modern caches are write-back.

**False sharing.** Two cores writing to two different variables that happen to
share a cache line invalidate each other's copy on every write. The program is
correct but slow. The fix is to pad variables onto separate lines.

---

## 3. Latency and memory bandwidth

**Latency**: the time to obtain one datum, from request to answer.
**Bandwidth**: how many bytes per second can be transferred once the flow is
running.

The car analogy: latency is the travel time from one city to another,
bandwidth is how many cars per second arrive, that is, how wide the motorway
is.

To saturate a bandwidth you need many requests in flight at the same time.
Little's law (`L = lambda x W`: elements in the system = arrival rate x
residence time) gives the rule of thumb: bytes in flight = latency x bandwidth.
With 100 ns of latency and 50 GB/s of bandwidth, 100e-9 x 50e9 = 5000 bytes
must be in flight, that is about 80 cache lines.

The standard bandwidth benchmark is the STREAM *triad*, `a = b + s*c`: read two
arrays, write a third. The reference implementation is in
[reference](../reference/linux.md); the usual estimate for NumPy counts
3 x 8 bytes per element.

**NUMA.** On multi-socket machines the RAM is attached to a socket. Accessing
the memory of the other socket is slower, so where a thread runs matters.

---

## 4. Complexity, O(...)

Big-O describes how the cost grows when the input size `n` grows. It ignores
constants and lower-order terms: it does not say how fast a program is, only how
it scales.

| Notation | Growth | Example |
|---|---|---|
| O(1) | constant | read one array element by index |
| O(log n) | halves at each step | binary search |
| O(n) | one pass over the data | sum of an array |
| O(n log n) | typical efficient sorting | merge sort, heapsort |
| O(n^2) | all pairs | comparing every pair of points |

Two caveats that matter for HPC:

1. Big-O ignores the memory hierarchy. An O(n) algorithm with random access can
   be slower than an O(n log n) one with sequential access, because the cache
   works much better on the second.
2. Constants matter. An O(n^2) implementation with a small constant can beat an
   O(n log n) one for small `n`.

Physics example: all-pairs interactions in a simulation of `N` particles cost
O(N^2). That is why *neighbour lists* and *cut-offs* exist: they reduce the work
to roughly O(N) for short-range interactions.

---

## 5. Cores, threads, processes

**Process.** A program in execution, with its own address space. Two processes
cannot see each other's memory unless they exchange it explicitly (pipes,
sockets, MPI messages). Creating one is relatively expensive; the isolation is
the price.

**Thread.** A flow of execution inside a process. All threads of a process
share the same memory, but each has its own stack and registers. Creating a
thread is cheap; sharing memory is the price, because unsynchronised concurrent
access produces *race conditions*.

**Scheduler and affinity.** The operating system assigns software threads to
hardware threads. Moving a thread to another core invalidates its cached data,
so HPC codes often pin threads to cores (*thread affinity*, controlled in
OpenMP with `OMP_PROC_BIND` and `OMP_PLACES`).

**Shared memory vs distributed memory.**

- *shared memory*: threads of one process work on the same data. Model:
  **OpenMP**.
- *distributed memory*: processes on different nodes, each with its own RAM,
  exchange data with messages. Model: **MPI**.

**The GIL.** In CPython a global lock allows only one thread at a time to
execute Python bytecode. Threads therefore do not speed up pure Python
numerics; libraries written in C (NumPy) release the GIL and do benefit.

---

## 6. Measuring parallel performance

**Concurrency** is about structure: several activities advance in the same
interval, possibly on one core, by taking turns. **Parallelism** is about
execution: several activities really run at the same time, on several cores.

**Speedup** `S(p) = T1 / Tp` (serial time divided by parallel time).
**Efficiency** `E(p) = S(p) / p`: how much of the theoretical parallelism is
actually used. 50% efficiency on 64 cores means you are getting the equivalent
of 32.

**Amdahl's law** (fixed problem). If a fraction `f` is parallelisable:

```text
S(p) = 1 / ((1 - f) + f/p)
```

As `p` grows, the speedup tends to `1 / (1 - f)`: the serial part dominates.
With 5% of serial code the maximum speedup is 20, whatever the core count.

**Gustafson's law** (problem grows with the processors): `S(p) = (1 - f) + f p`,
nearly linear. The two laws answer different questions: "how much faster is this
problem?" and "how much bigger a problem can I solve?".

**Strong and weak scaling.** *Strong*: same problem, more processors, measure
the runtime. *Weak*: the problem grows with the processors so that the work per
processor stays constant; ideally the runtime stays constant.

**Overheads.** Parallelism is not free: creation and management of threads or
processes, synchronisation (barriers, locks), load imbalance (uneven task
durations) and communication.

---

## 7. OpenMP

An API for shared-memory parallelism in C, C++ and Fortran. The program starts
as a single thread (the *master*); at a parallel region a *team* of threads is
created, and the master rejoins them at the end. This is the **fork-join**
model.

Key directives: `parallel`, `parallel for`, `critical`, `atomic`, `barrier`,
`single`, `master`, `task`.

Key clauses: `private(x)`, `shared(x)`, `firstprivate(x)`, `reduction(op:x)`,
`schedule(static|dynamic|guided, chunk)`, `default(none)`.

`reduction` is the correct way to sum or to take a maximum in parallel: each
thread accumulates into a private copy, and the copies are combined at the end.
Without it, concurrent updates of the same variable are a race condition.

```bash
gcc -fopenmp -o prog prog.c
OMP_NUM_THREADS=4 ./prog
```

False sharing appears here too: counters kept next to each other in an array
are shared between threads; pad them onto separate cache lines.

See [reference/openmp](../reference/openmp.md).

---

## 8. MPI

A standard for programs made of processes that do not share memory. Each
process has its own RAM, and the only way to get data from another process is
to receive it in a message. The same program runs on a laptop and on thousands
of nodes of a supercomputer.

The execution model is **SPMD** (Single Program, Multiple Data): all processes
run the same program and distinguish themselves by their *rank* (0 to
`size - 1`).

Core objects:

- **communicator**: the group of processes allowed to talk to each other
  (`MPI_COMM_WORLD` is all of them; `split` creates sub-groups);
- **point-to-point**: `Send` and `Recv` between two ranks;
- **collectives**: operations involving the whole communicator — `broadcast`,
  `scatter`, `gather`, `reduce`, `all-reduce`, `alltoall`, `barrier`.

Collectives are implemented with tree algorithms, so they scale logarithmically
and are much faster than hand-written point-to-point exchanges.

**Blocking vs non-blocking.** `Send`/`Recv` return only when the buffer can be
reused; `Isend`/`Irecv` return immediately and are completed later with `Wait`.
Non-blocking calls are the way to overlap communication with computation.

**Deadlock.** If two processes both `Send` before both `Recv`, and the messages
are large enough to use the rendezvous protocol, each waits for a receiver
that is itself stuck sending. Use `Sendrecv`, or make the order asymmetric
(even ranks send first, odd ranks receive first).

**Halo / ghost cells.** In grid simulations each process owns a region and
needs the border of its neighbours. The exchanged borders are the *halo*, the
copies are *ghost cells*. This is the most common communication pattern in
fluid, electromagnetic and molecular-dynamics codes.

```bash
mpirun -n 4 python mpi_demo.py   # add --oversubscribe if slots are limited
```

See [reference/mpi](../reference/mpi.md).

---

## 9. Quick glossary

| Term | Meaning |
|---|---|
| Core | Independent execution unit inside the CPU |
| Hardware thread (SMT) | Logical CPU offered by a core, sharing its units |
| Process | Program in execution, with its own address space |
| Thread | Flow of execution inside a process, sharing memory |
| Cache | Small fast copy of data kept close to the core |
| Cache line | Block of memory transferred at once, typically 64 bytes |
| Hit / miss | Access served by the cache / access that must go one level down |
| Associativity | Number of places a block can occupy inside its set |
| Tag, index, offset | Fields in which an address is split to search the cache |
| Locality | Tendency to reuse recent data and nearby data |
| Prefetching | Loading data in advance when the access pattern is predictable |
| False sharing | Independent variables in the same cache line, contended by cores |
| TLB | Cache of virtual-to-physical address translations |
| NUMA | Memory whose latency depends on the socket it hangs from |
| Latency | Time needed to obtain one datum |
| Bandwidth | Bytes transferred per second |
| Complexity O(f) | How the cost grows when the input size grows |
| Speedup, efficiency | `T1/Tp`; speedup divided by the number of processors |
| Amdahl's law | Speedup limit imposed by the serial part of the code |
| Strong / weak scaling | Same problem with more processors / problem growing with them |
| Load imbalance | Uneven distribution of work across threads or processes |
| Concurrency / parallelism | Activities advancing together / activities running at the same time |
| SIMD | One instruction applied to several data at once |
| GIL | CPython lock that serialises Python bytecode across threads |
| Race condition | Unsynchronised concurrent access, non-deterministic result |
| Reduction | Safe combination of partial values (sum, max) at the end of a region |
| Fork-join | Model where a master creates a team of threads and then rejoins it |
| Barrier | Point where all threads or processes wait for the others |
| Rank | Identifier of an MPI process |
| Communicator | Group of MPI processes that can communicate |
| Collective | MPI operation involving all processes of a communicator |
| SPMD | Model where all processes run the same program on different data |
| Deadlock | Stall where processes or threads wait for each other forever |
| Halo / ghost cells | Copies of the borders received from the neighbours |

---

## 10. Self-check

::::{dropdown} 1. Why does a cache transfer 64-byte lines instead of single bytes?

The cost of a RAM request is dominated by latency, not by payload: fetching 64
bytes costs about as much as fetching 8. On top of that, the bytes next to the
requested one are almost always needed shortly after (spatial locality), so
they are not wasted.

:::

::::{dropdown} 2. A 32 KB L1 cache has 64-byte lines and 8-way associativity. How many sets, and how many index bits?

32768 / (64 x 8) = 64 sets, so 6 index bits (2^6 = 64) and 6 offset bits; the
remaining address bits are the tag.

:::

::::{dropdown} 3. Hit takes 1 ns, miss rate is 3%, miss penalty is 100 ns. What is the average memory access time?

AMAT = 1 + 0.03 x 100 = 4 ns.

:::

::::{dropdown} 4. What is the difference between latency and bandwidth? How many bytes must be in flight for 100 ns of latency and 50 GB/s of bandwidth?

Latency is the time to obtain one datum; bandwidth is the number of bytes per
second once the flow is running. Bytes in flight = latency x bandwidth =
100e-9 x 50e9 = 5000 bytes, about 80 cache lines.

:::

::::{dropdown} 5. Why can summing a matrix by columns be much slower than by rows?

Matrix elements are stored row by row, so summing by rows uses the whole
64-byte line it loads. Summing by columns jumps by `n x 8` bytes at each step,
so every element needs a different line. If `n x 8` is a power of two (for
example n = 512), all the elements of a column fall into the same set, and
conflict misses pile up.

:::

::::{dropdown} 6. If 10% of a program is serial, what is the maximum speedup?

Amdahl's law: S(infinity) = 1 / 0.1 = 10. No number of processors can do
better.

:::

::::{dropdown} 7. Why do Python threads not speed up pure Python numerics, while NumPy does?

The GIL allows only one thread at a time to execute Python bytecode, so the
threads take turns instead of working together. NumPy runs the loop in C and
releases the GIL during the computation, so several threads do work in
parallel.

:::

::::{dropdown} 8. What happens if several OpenMP threads increment the same variable without a reduction?

It is a race condition: some increments are lost, and the result is wrong and
different from run to run. With `reduction`, each thread accumulates into a
private copy and the copies are combined at the end.

:::

::::{dropdown} 9. Why can two MPI processes that both `Send` before both `Recv` block each other?

With large messages the rendezvous protocol waits for the receiver to be
ready, but both processes are stuck in `Send`, so nobody ever receives. The
fix is `Sendrecv`, or making the order asymmetric between even and odd ranks.

:::

::::{dropdown} 10. An O(n^2) algorithm: how much slower when n doubles?

Four times slower, because (2n)^2 = 4n^2.

:::

---

## Where to go next

- [Lecture 2 — performance models (Roofline)](../lectures/lecture02/index.md):
  how to tell whether a kernel is limited by computation or by memory.
- [Lecture 3](../lectures/lecture03/index.md): OpenMP and MPI in practice.
- [Reference: OpenMP](../reference/openmp.md), [reference: MPI](../reference/mpi.md),
  [reference: compilation](../reference/compilation.md).
