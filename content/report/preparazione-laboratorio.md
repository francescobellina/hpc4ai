---
title: Preparazione laboratorio — Parallel Hello, World! su WILSON
---

:::{note} Pagina di preparazione
:class: prep-page

Questa pagina riporta i comandi per replicare l'esercizio su WILSON: eseguili prima della relazione.
:::

:::{note} Script unico di verifica
Tutti i controlli sono raccolti in
[`codes/exec2/checks.sh`](codes/exec2/checks.sh). Dalla cartella del repository
sul **WILSON**, dopo `git pull`:

```bash
cd content/report/codes/exec2
bash -l checks.sh all      # build + test brevi + job Slurm + verifica output
bash -l checks.sh all      # rieseguibile: validate riusa jobs.tsv
```

Sottocomandi: `build`, `quick`, `submit`, `wait`, `validate` (default `all`).
Lo script stampa `OK`/`FAIL` per ogni controllo e termina con exit code diverso
da zero se qualcosa non torna. I test `quick` girano sul nodo di login: sono
brevi, i job veri passano da Slurm.
:::

Questa pagina riporta i comandi del corso per l'esercizio [Parallel Hello, World!](https://virgilio.mib.infn.it/~marcoce/teaching/hpc4ai/content/exercises/parallel-hello-world.html), adattati all'account `fbellina2` su `wilson.mib.infn.it`. Esegui i blocchi in ordine.

Il corso fissa la partizione `lab4` e i percorsi dei moduli. Conferma con `sinfo` e `module spider` prima di inviare i job.

Ogni blocco `bash` va eseguito nella shell indicata:

- **Client** (terminale del laboratorio): comandi di accesso.
- **WILSON** (dopo `ssh`): tutti gli altri comandi.

## 1. Accesso dal client

Sul **client**:

```bash
ssh fbellina2@wilson.mib.infn.it
```

Sul **WILSON**, verifica sessione e directory:

```bash
hostname
pwd
echo "$HOME"
```

## 2. Directory di lavoro

Sul **WILSON**:

```bash
mkdir -p ~/hpc4ai/es02-parallel-hello-world
cd ~/hpc4ai/es02-parallel-hello-world
```

## 3. Moduli

Sul **WILSON**:

```bash
module use /srv/software/easybuild/hmns/x86-64-v2/modules/all/Core
module spider GCC/13.2.0
module spider OpenMPI/4.1.6
module load GCC/13.2.0
module load OpenMPI/4.1.6
module list
```

## 4. Creazione dei codici

Sul **WILSON**, i blocchi `cat > file << 'EOF'` creano i file direttamente nella directory di lavoro. Il delimitatore quotato `'EOF'` evita l'espansione delle variabili.

### 4.1 Versione a memoria condivisa (OpenMP)

```bash
cat > hello_shared_world.c << 'EOF'
#include <stdio.h>
#include <unistd.h>
#include <omp.h>

int main(void)
{
    char hostname[256];
    gethostname(hostname, sizeof hostname);

    #pragma omp parallel
    {
        int thread = omp_get_thread_num();
        int threads = omp_get_num_threads();

        printf("Hello from thread %d/%d on %s\n", thread, threads, hostname);
    }

    return 0;
}
EOF
```

### 4.2 Versione ibrida (MPI + OpenMP, con affinità)

```bash
cat > hello_parallel_world.c << 'EOF'
#define _GNU_SOURCE
#include <sched.h>
#include <stdio.h>
#include <mpi.h>
#include <omp.h>

/* Write the CPUs in mask as a compact list, for example "0-3,8,10-11". */
static void format_cpu_set(const cpu_set_t *mask, char *buffer, size_t size)
{
    size_t used = 0;

    buffer[0] = '\0';
    for (int cpu = 0; cpu < CPU_SETSIZE; ++cpu) {
        if (!CPU_ISSET(cpu, mask))
            continue;

        int last = cpu;
        while (last + 1 < CPU_SETSIZE && CPU_ISSET(last + 1, mask))
            ++last;

        const char *separator = used > 0 ? "," : "";
        int written = (last == cpu)
            ? snprintf(buffer + used, size - used, "%s%d", separator, cpu)
            : snprintf(buffer + used, size - used, "%s%d-%d", separator, cpu, last);
        if (written < 0 || (size_t)written >= size - used)
            break;  /* buffer full: the list is truncated */

        used += written;
        cpu = last;
    }
}

int main(int argc, char *argv[])
{
    int rank, ranks, name_length;
    char processor_name[MPI_MAX_PROCESSOR_NAME];

    MPI_Init(&argc, &argv);
    MPI_Comm_rank(MPI_COMM_WORLD, &rank);
    MPI_Comm_size(MPI_COMM_WORLD, &ranks);
    MPI_Get_processor_name(processor_name, &name_length);

    #pragma omp parallel
    {
        int thread = omp_get_thread_num();
        int threads = omp_get_num_threads();
        cpu_set_t mask;
        char cpus[1024];

        CPU_ZERO(&mask);
        if (sched_getaffinity(0, sizeof mask, &mask) == 0)
            format_cpu_set(&mask, cpus, sizeof cpus);
        else
            snprintf(cpus, sizeof cpus, "unknown");

        printf("Hello from thread %d/%d from rank %d/%d on %s (core affinity = %s)\n",
               thread, threads, rank, ranks, processor_name, cpus);
    }

    MPI_Finalize();
    return 0;
}
EOF
```

### 4.3 Versione Python (mpi4py + threading)

```bash
cat > hello_parallel_world.py << 'EOF'
#!/usr/bin/env python3
"""Hybrid hello world: several MPI processes, each with several threads."""
import os
import socket
import threading

from mpi4py import MPI


def format_cpu_set(cpus):
    """Return the CPUs as a compact list, for example "0-3,8,10-11"."""
    ranges = []
    for cpu in sorted(cpus):
        if ranges and cpu == ranges[-1][1] + 1:
            ranges[-1][1] = cpu
        else:
            ranges.append([cpu, cpu])
    return ",".join(str(a) if a == b else f"{a}-{b}" for a, b in ranges)


def greet(thread, threads, rank, ranks, hostname):
    cpus = format_cpu_set(os.sched_getaffinity(0))
    print(f"Hello from thread {thread}/{threads} from rank {rank}/{ranks} "
          f"on {hostname} (core affinity = {cpus})", flush=True)


def main():
    comm = MPI.COMM_WORLD
    rank, ranks = comm.Get_rank(), comm.Get_size()
    hostname = socket.gethostname()
    # Like OpenMP, default to one thread per available CPU.
    threads = int(os.environ.get("OMP_NUM_THREADS", len(os.sched_getaffinity(0))))

    workers = [threading.Thread(target=greet,
                                args=(thread, threads, rank, ranks, hostname))
               for thread in range(threads)]
    for worker in workers:
        worker.start()
    for worker in workers:
        worker.join()


if __name__ == "__main__":
    main()
EOF
```

Verifica che i file esistano:

```bash
ls -l hello_shared_world.c hello_parallel_world.c hello_parallel_world.py
```

## 5. Compilazione

Sul **WILSON**, con i moduli del passo 3 caricati:

```bash
gcc -Wall -Wextra -O2 -fopenmp -o hello_shared_world hello_shared_world.c
mpicc -Wall -Wextra -O2 -fopenmp -o hello_parallel_world hello_parallel_world.c
```

Controllo di exit status:

```bash
echo $?
```

Deve stampare `0`.

## 6. Test brevi sul nodo di login

Sul **WILSON**. Sono test brevi: i calcoli veri vanno sui nodi di calcolo tramite Slurm (passo 7).

```bash
export OMP_NUM_THREADS=4
./hello_shared_world

OMP_NUM_THREADS=1 mpiexec -n 1 ./hello_parallel_world
OMP_NUM_THREADS=2 mpiexec -n 1 ./hello_parallel_world
OMP_NUM_THREADS=2 mpiexec -n 2 ./hello_parallel_world
```

Attese: 4 righe per il primo comando, poi 1, 2 e 4 righe.

## 7. Job Slurm

Controlla partizione e stato prima di inviare:

```bash
sinfo -p lab4
squeue -u "$USER"
```

Crea i tre script batch:

```bash
cat > job_openmp.sh << 'EOF'
#!/bin/bash
#SBATCH --job-name=hello_openmp
#SBATCH --partition=lab4
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --hint=nomultithread
#SBATCH --time=5:00
#SBATCH --output=%x.%j.out

export OMP_NUM_THREADS=$SLURM_CPUS_PER_TASK
srun ./hello_shared_world
EOF

cat > job_mpi.sh << 'EOF'
#!/bin/bash
#SBATCH --job-name=hello_mpi
#SBATCH --partition=lab4
#SBATCH --ntasks=4
#SBATCH --cpus-per-task=1
#SBATCH --hint=nomultithread
#SBATCH --time=5:00
#SBATCH --output=%x.%j.out

module use /srv/software/easybuild/hmns/x86-64-v2/modules/all/Core
module load GCC/13.2.0
module load OpenMPI/4.1.6

export OMP_NUM_THREADS=1
srun ./hello_parallel_world
EOF

cat > job_hybrid.sh << 'EOF'
#!/bin/bash
#SBATCH --job-name=hello_hybrid
#SBATCH --partition=lab4
#SBATCH --nodes=2
#SBATCH --ntasks-per-node=2
#SBATCH --cpus-per-task=4
#SBATCH --hint=nomultithread
#SBATCH --time=5:00
#SBATCH --output=%x.%j.out

module use /srv/software/easybuild/hmns/x86-64-v2/modules/all/Core
module load GCC/13.2.0
module load OpenMPI/4.1.6

export OMP_NUM_THREADS=$SLURM_CPUS_PER_TASK
srun ./hello_parallel_world
EOF
```

Invio, monitoraggio e lettura:

```bash
sbatch job_openmp.sh
sbatch job_mpi.sh
sbatch job_hybrid.sh
squeue -u "$USER"
ls *.out
```

Quando i job terminano, leggi l'output ordinato:

```bash
sort hello_hybrid.<JOBID>.out
```

Sostituisci `<JOBID>` con l'ID mostrato da `sbatch`/`squeue`. Per cancellare un job: `scancel <JOBID>`.

Attese:

| Job | Righe attese | Controllo |
|---|---|---|
| `hello_openmp` | 4 | thread 0 a 3, stesso nodo |
| `hello_mpi` | 4 | rank 0 a 3, un thread ciascuno |
| `hello_hybrid` | 16 | 2 nodi × 2 rank × 4 thread; i rank 0 e 1 condividono un nodo, i rank 2 e 3 l'altro |

## 8. Variante Python (opzionale)

Sul **WILSON**, con i moduli del passo 3:

```bash
source /srv/software2/venv/python39/bin/activate
python3 -c "import mpi4py; print(mpi4py.__version__)"
OMP_NUM_THREADS=2 mpiexec -n 2 python3 hello_parallel_world.py
```

Nota: con il GIL di CPython i thread Python non danno vero parallelismo di calcolo; la variante serve a mostrare la gerarchia processi/thread.

## 9. Pulizia e uscita

Sul **WILSON**, dopo aver copiato l'output:

```bash
deactivate 2>/dev/null
exit
```

Sul **client**, se serve il log: `scp fbellina2@wilson.mib.infn.it:~/hpc4ai/es02-parallel-hello-world/*.out .`

## Da confermare in laboratorio

- Partizione `lab4` e limiti di tempo (`sinfo -p lab4`).
- Percorso del modulo `module use` e versioni `GCC/13.2.0`, `OpenMPI/4.1.6` (`module spider`).
- Percorso del virtualenv Python per la variante opzionale.
- Directory di lavoro remota indicata dal laboratorio: qui è `~/hpc4ai/es02-parallel-hello-world`.
