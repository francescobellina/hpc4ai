# codes/exec2 — Parallel Hello, World!

Programma diagnostico che riporta thread, rank e nodi di un'esecuzione parallela.
Corrisponde all'[Esercitazione 2](../../esercitazioni/es02-parallel-hello-world.md).

## File previsti

| File | Scopo |
|---|---|
| `hello_shared_world.c` | memoria condivisa: $T$ thread OpenMP, una riga per thread |
| `hello_parallel_world.c` | ibrido: $P$ rank MPI × $T$ thread OpenMP, $P \times T$ righe |
| `run_openmp.slurm` | script di batch: `--cpus-per-task=T`, `OMP_NUM_THREADS=$SLURM_CPUS_PER_TASK` |
| `run_mpi.slurm` | script di batch: `--ntasks=P --cpus-per-task=1`, `OMP_NUM_THREADS=1` |
| `run_hybrid.slurm` | script di batch: `--nodes=2 --ntasks=P --cpus-per-task=T` |

I sorgenti vanno aggiunti in questa cartella quando l'esercitazione è svolta; la
validazione locale usa la demo Python del notebook.

## Dipendenze (WILSON)

```bash
module use /srv/software/easybuild/hmns/x86-64-v2/modules/all/Core
module load GCC/13.2.0
module load OpenMPI/4.1.6
```

## Build

```bash
gcc   -fopenmp hello_shared_world.c   -o hello_shared_world
mpicc -fopenmp hello_parallel_world.c -o hello_parallel_world
```

## Esecuzione

```bash
export OMP_NUM_THREADS=4
./hello_shared_world                 # T = 4

mpiexec -n 4 ./hello_parallel_world  # P = 4, T = OMP_NUM_THREADS
```

## Parametri di default

| Parametro | Default |
|---|---|
| `P` (rank MPI) | 4 |
| `T` (thread OpenMP) | `OMP_NUM_THREADS`, non impostato → numero di core visibili |
| Nodi | 1 (OpenMP/MPI), 2 (ibrido) |

Ogni riga stampa: rank/totale rank, thread/totale thread, nome del nodo
(optional: maschera di affinità).
