---
title: Preparazione laboratorio — Parallel Hello, World! su WILSON
---

:::{note} Pagina di preparazione
:class: prep-page

Questa pagina riporta i comandi per replicare l'esercizio su WILSON: eseguili prima della relazione.
:::

:::{note} Avvio rapido — un solo blocco
Da incollare in una shell **su WILSON** (terminale Warp dopo `ssh`, oppure
terminale integrato di VS Code in Remote-SSH). Trova il repository, lo aggiorna
ed esegue tutti i controlli tramite `codes/exec2/checks.sh`:

```bash
hostname; which sbatch     # deve stampare un path: sei su WILSON

REPO=$(find ~ -maxdepth 4 -type d -name hpc4ai 2>/dev/null | head -1)
if [ -z "$REPO" ]; then
  git clone git@github.com:francescobellina/hpc4ai.git ~/hpc4ai && REPO=$HOME/hpc4ai
fi
git -C "$REPO" pull --ff-only && bash -l "$REPO/content/report/codes/exec2/checks.sh" all
```

Se `which sbatch` dice `not found` sei sul Mac: apri
`ssh fbellina2@wilson.mib.infn.it`.
:::

:::{note} Script unico di verifica
Tutti i controlli sono raccolti in
[`codes/exec2/checks.sh`](codes/exec2/checks.sh). Dalla cartella
`content/report/codes/exec2` del repository sul **WILSON**:

```bash
bash -l checks.sh all      # build + test brevi + job Slurm + verifica output
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

## 10. Esercizio 3 — Tiny stories, many threads

Guida per l'esercizio [Tiny stories, many threads](https://virgilio.mib.infn.it/~marcoce/teaching/hpc4ai/content/exercises/index.html#tiny-stories-many-threads). I percorsi e i nomi file sono quelli della pagina del corso. Numeri di banda, tipo di nodo e tempo di generazione **non** sono nella pagina: misurali, non copiarli da qui.

Il modello produce il testo **un token alla volta**: ogni token è un forward pass sull'intera rete, e il token emesso diventa l'input del passo successivo. Per questo il tempo cresce con il numero di token, non con una sola moltiplicazione. I modelli (`stories15M`, `stories42M`, `stories110M`) sono addestrati su [TinyStories](https://arxiv.org/abs/2305.07759): continuano un inizio di storia, non rispondono a domande.

Il programma è [`llama2.c`](https://github.com/karpathy/llama2.c) (`run.c`). Nel sorgente pubblico il tempo sta quasi tutto in `matmul` (commento nel codice: *by far the most amount of time is spent inside this little function*). Sul file del corso va **confermato** con il profilo, non dato per scontato: la copia in `/srv/data/...` può essere la versione seriale, senza i `#pragma` del repository upstream.

### 10.1 Copia dei file

Sul **WILSON**. Il corso indica la cartella condivisa; copiala prima di modificarla. I `.bin` grandi si possono lasciare lì e passarli per path.

```bash
ls /srv/data/wilson/project/hpc4ai/exercises/tiny_stories/
mkdir -p ~/hpc4ai/es03-tiny-stories
cd ~/hpc4ai/es03-tiny-stories
cp /srv/data/wilson/project/hpc4ai/exercises/tiny_stories/run.c .
cp /srv/data/wilson/project/hpc4ai/exercises/tiny_stories/tokenizer.bin .
cp /srv/data/wilson/project/hpc4ai/exercises/tiny_stories/prompts.txt .
ls -lh /srv/data/wilson/project/hpc4ai/exercises/tiny_stories/*.bin
```

`ls` deve mostrare `run.c`, `tokenizer.bin`, `stories15M.bin`, `stories42M.bin`, `stories110M.bin`, `prompts.txt`. Se il path non esiste, fermati: non inventare un altro percorso.

### 10.2 Baseline seriale

Sul **WILSON**, smoke test breve sul login node. Le misure vere vanno sul nodo di calcolo (10.6).

```bash
module use /srv/software/easybuild/hmns/x86-64-v2/modules/all/Core
module load GCC/13.2.0
gcc -O3 -o run run.c -lm
./run /srv/data/wilson/project/hpc4ai/exercises/tiny_stories/stories15M.bin \
    -t 0 -n 256 -i "Once upon a time" > story_serial.txt 2> speed_serial.txt
cat speed_serial.txt
```

Cosa significano le opzioni (sono quelle di `run.c`):

| Opzione | Ruolo |
|---|---|
| `-t 0` | temperature 0 = decoding **greedy**: ogni volta il token più probabile. Stesso prompt → stesso testo. Senza questo il confronto seriale/parallelo non è valido. |
| `-n 256` | numero di passi (token) da generare. Il timer parte dopo il primo passo. |
| `-i "..."` | prompt. Tienilo **identico** in ogni misura dello scaling. |
| stdout | testo generato |
| stderr | `achieved tok/s: ...` — è la velocità da riportare, non il testo |

`-t 0` è obbligatorio per la validazione. Con `-t 1` due run dello stesso binario già divergono: non è un bug di OpenMP.

Velocità dei tre modelli, stesso prompt e stesso `-n`:

```bash
DATA=/srv/data/wilson/project/hpc4ai/exercises/tiny_stories
for m in stories15M stories42M stories110M; do
  ./run "$DATA/$m.bin" -t 0 -n 256 -i "Once upon a time" \
      > "story_${m}.txt" 2> "speed_${m}.txt"
  printf '%s  ' "$m"; cat "speed_${m}.txt"
done
```

Attesa qualitativa, non un numero: il modello più grande è più lento. I valori li leggi da `speed_*.txt`.

### 10.3 Dove va il tempo

Profila il binario **seriale** (senza `-fopenmp`). `gprof` non richiede permessi speciali; `perf` sul cluster può essere bloccato — se `perf stat` fallisce, resta su `gprof`.

```bash
DATA=/srv/data/wilson/project/hpc4ai/exercises/tiny_stories
gcc -O3 -pg -o run_prof run.c -lm
./run_prof "$DATA/stories15M.bin" -t 0 -n 256 -i "Once upon a time" > /dev/null
gprof run_prof gmon.out | head -40
```

La funzione in cima alla tabella `% time` è quella da parallelizzare per prima. Nel sorgente pubblico è `matmul`. Se sul file del corso è un'altra, segui il profilo, non questa pagina.

### 10.4 Traffico di memoria per token

Ogni token rilegge i pesi: `matmul` fa \(W x\), e \(W\) non sta nei registri. Stima, da misurare sui file che hai copiato:

```text
byte_per_token ≈ dimensione del .bin − header di Config
BW_eff         ≈ (tok/s) × byte_per_token
```

`ls -l` sul `.bin` dà la dimensione. L'header è piccolo rispetto a 15–110 milioni di float32 (4 byte per parametro): per il confronto con la banda del nodo l'ordine di grandezza basta, ma nel report scrivi la dimensione misurata, non «15 MB».

La banda di picco del nodo **non** è nella pagina del corso. Non inserire un numero preso da un'altra macchina. Sul nodo di calcolo del job: `lscpu` (modello di CPU) e, se c'è, la documentazione del nodo. Segna «da confermare» se non la trovi.

Perché i tre modelli possono scalare in modo diverso: se i pesi entrano in cache, aggiungere thread non aumenta il traffico verso la DRAM; se non entrano, la velocità si avvicina alla banda del nodo e lo speedup si ferma. È l'argomento che il corso chiede, dopo che hai i numeri.

Speedup ed efficienza, come nel testo del corso (\(T_1\) tempo del seriale, \(T_p\) tempo con \(p\) thread, stesso \(N\) e stesso prompt):

\[
S_p = \frac{T_1}{T_p} = \frac{(\mathrm{tok/s})_p}{(\mathrm{tok/s})_1}, \qquad E_p = \frac{S_p}{p}.
\]

Le due forme coincidono solo se il numero di token generati è lo stesso. Usa sempre `-n 256` e `-t 0`.

### 10.5 OpenMP sul forward

Apri `matmul` in `run.c`. Se il ciclo sulle righe di uscita non ha già un pragma, le iterazioni sono indipendenti: la riga `i` scrive solo `xout[i]` e legge `w` e `x`.

```c
void matmul(float* xout, float* x, float* w, int n, int d) {
    // W (d,n) @ x (n,) -> xout (d,)
    int i;
    #pragma omp parallel for private(i)
    for (i = 0; i < d; i++) {
        float val = 0.0f;
        for (int j = 0; j < n; j++)
            val += w[i * n + j] * x[j];
        xout[i] = val;
    }
}
```

Non parallelizzare il ciclo interno su `j` senza una `reduction`: `val` sarebbe una race. `x` è solo letto: non serve proteggerlo.

Il ciclo sulle head in `forward` è il secondo candidato (ogni head scrive la propria fetta di `xb` e `att`). Parallelizzalo solo se il profilo, dopo `matmul`, mostra ancora tempo lì. `rmsnorm` e il residuo sono corti: di solito non pagano il costo di un altro team di thread.

Compila **due** binari. Senza `-fopenmp` il pragma è ignorato e ottieni di nuovo il seriale.

```bash
gcc -O3 -o run_serial run.c -lm
gcc -O3 -fopenmp -o run_omp run.c -lm
```

### 10.6 Validazione: stesso testo

Sul **WILSON**, prima sul login (poche decine di token), poi ripeti nel job.

```bash
DATA=/srv/data/wilson/project/hpc4ai/exercises/tiny_stories
PROMPT="Once upon a time"
./run_serial "$DATA/stories15M.bin" -t 0 -n 64 -i "$PROMPT" > serial.txt
OMP_NUM_THREADS=4 ./run_omp "$DATA/stories15M.bin" -t 0 -n 64 -i "$PROMPT" > omp.txt
diff -u serial.txt omp.txt && echo "TESTO IDENTICO"
```

`diff` vuoto e `TESTO IDENTICO` è il criterio. Se differiscono: temperatura non zero, pragma sul ciclo sbagliato, oppure una race (scrittura condivisa senza `private`). Non confrontare i `tok/s`: quelli devono cambiare.

### 10.7 Scaling sul nodo di calcolo

Non misurare lo scaling sul login node. Un job, un nodo, stesso binario; dentro il job vari solo `OMP_NUM_THREADS`. `--cpus-per-task` deve essere almeno il massimo \(p\) che provi. Quanti core ha il nodo lo leggi **nel job** con `lscpu`, non da questa pagina. Partizione `lab4` come negli script dell'esercizio 2: confermala con `sinfo -p lab4` prima di inviare.

```bash
cat > job_stories.sh << 'EOF'
#!/bin/bash
#SBATCH --job-name=stories_scale
#SBATCH --partition=lab4
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --hint=nomultithread
#SBATCH --time=30:00
#SBATCH --output=%x.%j.out

module use /srv/software/easybuild/hmns/x86-64-v2/modules/all/Core
module load GCC/13.2.0

cd "$SLURM_SUBMIT_DIR"
DATA=/srv/data/wilson/project/hpc4ai/exercises/tiny_stories
PROMPT="Once upon a time"

echo "node=$(hostname)"
lscpu | grep -E 'Model name|CPU\(s\)|Thread|MHz|NUMA'

export OMP_PROC_BIND=close
export OMP_PLACES=cores

for m in stories15M stories42M stories110M; do
  for t in 1 2 4 8; do
    export OMP_NUM_THREADS=$t
    ./run_omp "$DATA/$m.bin" -t 0 -n 256 -i "$PROMPT" \
        > "story_${m}_t${t}.txt" \
        2> "speed_${m}_t${t}.txt"
    printf 'model=%s threads=%s ' "$m" "$t"
    cat "speed_${m}_t${t}.txt"
  done
done
EOF
sbatch job_stories.sh
```

`--cpus-per-task=8` e la lista `1 2 4 8` sono un punto di partenza, non un fatto del cluster. Se `lscpu` nel `.out` mostra più core fisici, alza il valore e rilancia. Se il job muore per tempo (`TIMEOUT`), alza `--time`. `--hint=nomultithread` chiede core fisici, non hyperthread: riportalo come placement, insieme a `OMP_PROC_BIND` e `OMP_PLACES`.

Dal `.out` costruisci, per ogni modello, la tabella \(p\), tok/s, \(S_p\), \(E_p\). \(T_1\) è la riga `threads=1` dello **stesso** modello, non il 15M usato come riferimento del 110M.

Controllo minimo sul testo del job: i file `story_${m}_t*.txt` dello stesso modello devono essere identici (`diff`). Se a \(p=8\) il testo cambia, lo speedup non è utilizzabile.

### 10.8 Cosa scrivere nel report

Checklist del corso, con i file che questo punto produce:

- tok/s seriale dei tre modelli (`speed_stories*.txt`) e il profilo (`gprof`);
- byte letti per token (dimensione misurata del `.bin`) e il confronto con la banda del nodo, se l'hai;
- quale funzione hai parallelizzato e perché (riga del profilo);
- `diff` seriale vs OpenMP vuoto, con `-t 0`;
- tabella o plot tok/s, \(S_p\), \(E_p\) vs thread, per i tre modelli;
- per ogni misura: modello, `-n`, prompt, `OMP_NUM_THREADS`, `OMP_PROC_BIND`/`OMP_PLACES`, nodo (`hostname` nel `.out`), moduli (`GCC/13.2.0`).

### 10.9 MPI, molte storie (opzionale)

Non è richiesto. Se lo fai: `prompts.txt` ha un prompt per riga. Il seriale genera una storia per riga, in ordine. Con MPI, il rank 0 legge il file, distribuisce i prompt e **ristampa le storie nell'ordine del file**, non nell'ordine di completamento. Con `-t 0` l'output deve coincidere con il seriale per ogni numero di rank (`diff`).

Due assegnazioni da confrontare, come chiede il corso:

- statica: il rank \(r\) prende i prompt \(r, r+P, r+2P, \ldots\) prima di partire;
- dinamica: un rank manager consegna il prompt successivo al primo worker libero.

Le storie hanno lunghezze diverse (finiscono al token di fine storia), quindi i tempi differiscono. Throughput = token totali / tempo di parete. Sbilanciamento = (tempo massimo di generazione tra i rank) / (tempo medio). La dinamica dovrebbe ridurre lo sbilanciamento quando le lunghezze variano; se non succede, le storie sono troppo poche o troppo simili — riportalo, non forzare il risultato.

## Da confermare in laboratorio

- Partizione `lab4` e limiti di tempo (`sinfo -p lab4`).
- Percorso del modulo `module use` e versioni `GCC/13.2.0`, `OpenMPI/4.1.6` (`module spider`).
- Percorso del virtualenv Python per la variante opzionale.
- Directory di lavoro remota indicata dal laboratorio: qui è `~/hpc4ai/es02-parallel-hello-world`.
- Cartella dell'esercizio 3: `/srv/data/wilson/project/hpc4ai/exercises/tiny_stories/` (`ls` prima di copiare).
- Core fisici del nodo `lab4` (`lscpu` dentro il job) e banda di memoria: non sono nella pagina del corso.
