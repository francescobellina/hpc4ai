# Esercitazione 2 — Parallel Hello, World!

:::{note} Consegna
Scrivere un piccolo programma che riporti **come è organizzata un'esecuzione
parallela**: quali processi e thread vengono avviati e su quali nodi girano. Il
programma è uno **strumento diagnostico**: eseguito con la stessa richiesta Slurm
e lo stesso ambiente di un calcolo reale, mostra se processi e thread sono
disposti come previsto.

- **Memoria condivisa (OpenMP)** — ogni **thread** stampa una riga con numero di
  thread, numero totale di thread e nome del nodo. Testare diversi
  `OMP_NUM_THREADS` e verificare **esattamente una riga per thread**.
- **Memoria distribuita (MPI) e ibrido** — estendere il programma perché **ogni
  processo MPI crei anche i suoi thread OpenMP**: ogni thread stampa rank e numero
  di rank, numero di thread e numero di thread nel processo, e nome del nodo. Con
  $P$ rank e $T$ thread il programma deve stampare $P \times T$ righe.

**(Optional)** Riportare la maschera di affinità di CPU.
:::

:::{seealso} Teoria di riferimento
- **2. Calcolo parallelo** — {ref}`Processo, thread, CPU logica e nodo <processi-thread-risorse>`
- **2. Calcolo parallelo** — {ref}`Schema riepilogativo dei tre modelli <schema-riepilogativo>`
- **4. Gestione delle risorse** — {ref}`Disposizione, affinità e Slurm <disposizione-e-slurm>`
- **4. Gestione delle risorse** — {ref}`Run OpenMP, MPI e ibridi con Slurm <t-slurm-esecuzione>`
- **5. OpenMP** — {ref}`Shared-memory e OpenMP <shared-memory-openmp>`
- **6. MPI** — {ref}`Programmazione ibrida MPI + OpenMP <ibrido-mpi-openmp>`
:::

:::{tip} L'esercizio in breve
**Cosa vogliamo sapere.** Quando chiediamo a Slurm "4 processi" o "4 thread", cosa
parte davvero, e dove? Il programma "Hello" non calcola nulla: ogni thread dice chi
è (thread, processo, nodo) e su quali core può girare. Se la richiesta è
rispettata, l'output ha esattamente una riga per thread, con tutti i numeri
attesi.

**Cosa abbiamo trovato.** Tutti i 13 controlli superati su WILSON: 4 valori di
`OMP_NUM_THREADS` (1, 2, 4, 8), 6 combinazioni rank × thread con `mpiexec` sul
login node e i 3 job Slurm della consegna (OpenMP 1 × 4, MPI 4 × 1, ibrido 4 × 4
su 2 nodi). Le maschere di affinità mostrano anche **dove** finiscono i processi:
Slurm dà a ogni task core fisici distinti, mentre `mpiexec` sul login node lega i
processi a un core se sono al massimo 2 e a un intero socket se sono di più.
:::

## Parametri

| Parametro | Valore |
|---|---|
| Programmi | `hello_shared_world.c` (OpenMP), `hello_parallel_world.c` (MPI + OpenMP, con maschera di affinità) |
| Ambiente | `GCC/13.2.0`, `OpenMPI/4.1.6` (gli stessi moduli per compilare ed eseguire) |
| Compilazione | `gcc -Wall -Wextra -O2 -fopenmp`, `mpicc -Wall -Wextra -O2 -fopenmp` |
| Test brevi (login node `wilson.bicqcd.internal`) | OpenMP con $T$ = 1, 2, 4, 8; `mpiexec` con $P \times T$ = 1 × 1, 1 × 2, 2 × 2, 2 × 3, 3 × 2, 4 × 1 |
| Job Slurm (partizione `lab4`, `--hint=nomultithread`) | OpenMP: 1 task × 4 CPU (job `61828`, `wnode25`); MPI: 4 task × 1 CPU (job `61829`, `wnode25`); ibrido: 2 nodi × 2 task × 4 CPU (job `61830`, `wnode[26-27]`) |
| Nodi | `wnode25`–`27`: feature `quanta` in `sinfo`; `wnode25` ha 2 × Intel Xeon E5-2683 v4, 16 core per socket, 2 hardware thread per core, CPU logiche 0–15 e 32–47 sul socket 0, 16–31 e 48–63 sul socket 1 (`lscpu` del job `61199`, esercizio 4) |

## Implementazione

**In breve.** Ogni thread chiede il suo numero a OpenMP, il processo chiede rank e
nome del nodo a MPI, e il sistema operativo dice su quali CPU logiche il thread può
girare. Gli script Slurm traducono "P processi × T thread" nelle righe `#SBATCH`.

Il cuore del programma ibrido (sorgente completo in
[`codes/exec2/`](../../codes/exec2/README.md)):

```c
MPI_Init(&argc, &argv);
MPI_Comm_rank(MPI_COMM_WORLD, &rank);
MPI_Comm_size(MPI_COMM_WORLD, &ranks);
MPI_Get_processor_name(processor_name, &name_length);

#pragma omp parallel
{
    int thread = omp_get_thread_num();      /* 0 ... T-1             */
    int threads = omp_get_num_threads();    /* T = OMP_NUM_THREADS   */
    cpu_set_t mask;
    sched_getaffinity(0, sizeof mask, &mask);   /* CPU logiche permesse */
    format_cpu_set(&mask, cpus, sizeof cpus);   /* es. "0-3" o "0,16"   */
    printf("Hello from thread %d/%d from rank %d/%d on %s (core affinity = %s)\n",
           thread, threads, rank, ranks, processor_name, cpus);
}
MPI_Finalize();
```

Il programma a memoria condivisa è lo stesso senza MPI: il nome del nodo viene da
`gethostname`. I tre script batch differiscono solo nelle righe di layout:

| Script | Righe `#SBATCH` | Thread | Lancio |
|---|---|---|---|
| `run_openmp.slurm` | `--ntasks=1 --cpus-per-task=4` | `OMP_NUM_THREADS=$SLURM_CPUS_PER_TASK` | `srun --cpu-bind=verbose --cpus-per-task="$SLURM_CPUS_PER_TASK" ./hello_shared_world` |
| `run_mpi.slurm` | `--ntasks=4 --cpus-per-task=1` | `OMP_NUM_THREADS=1` | `srun --cpu-bind=verbose ./hello_parallel_world` |
| `run_hybrid.slurm` | `--nodes=2 --ntasks-per-node=2 --cpus-per-task=4` | `OMP_NUM_THREADS=$SLURM_CPUS_PER_TASK` | `srun --cpu-bind=verbose --cpus-per-task="$SLURM_CPUS_PER_TASK" ./hello_parallel_world` |

Tutti usano `--partition=lab4`, `--hint=nomultithread` (un hardware thread per core)
e caricano `GCC/13.2.0` e `OpenMPI/4.1.6`. Come nell'esercizio 5, `srun` ripete
`--cpus-per-task`, perché a seconda della versione di Slurm non lo eredita da
`sbatch`; `--cpu-bind=verbose` scrive nel file `.err` la maschera assegnata a ogni
task.

Tutto il lavoro su WILSON è in un solo comando:

```bash
bash -l checks.sh all    # compila, test brevi, 3 job Slurm, attesa, controllo, log
```

## Procedura di validazione

`checks.sh` legge ogni output e controlla, per $P$ rank e $T$ thread attesi:

- **conto delle righe**: esattamente $P \times T$ righe `Hello from thread`;
- **tutte le coppie**: ogni rank $0 \dots P-1$ compare con ogni thread
  $0 \dots T-1$;
- **totali stampati**: ogni riga riporta $T$ thread e $P$ rank;
- **nodi**: il numero di nodi distinti, che per il job ibrido deve essere 2.

La **separazione dei ruoli** (cambiare `OMP_NUM_THREADS` cambia i thread, non i
rank) è verificata dalle combinazioni 2 × 2, 2 × 3 e 3 × 2 dei test brevi. Per i job
Slurm si controllano anche `sacct` (stato ed exit code) e le maschere.

## Risultati e plot

Log completo:
{download}`es02_collect_20261116_124412.txt <../../../results/es02/es02_collect_20261116_124412.txt>`
(sorgenti, script, tutti gli output, `sacct`, maschere e controlli).

### 1. Una riga per thread e per rank

**Idea.** Se il programma e la richiesta sono coerenti, il numero di righe è sempre
$P \times T$, e cambiando solo `OMP_NUM_THREADS` cambiano solo i thread.

:::{table} Esito dei controlli automatici di `checks.sh`.
:name: tab-es02-checks

| Esecuzione | $P \times T$ | Righe | Nodi distinti | Esito |
|---|---|---|---|---|
| OpenMP sul login node, `OMP_NUM_THREADS` = 1, 2, 4, 8 | 1 × 1, 1 × 2, 1 × 4, 1 × 8 | 1, 2, 4, 8 | 1 | OK |
| `mpiexec` sul login node | 1 × 1, 1 × 2, 2 × 2, 2 × 3, 3 × 2, 4 × 1 | 1, 2, 4, 6, 6, 4 | 1 | OK |
| Slurm OpenMP (job `61828`) | 1 × 4 | 4 | 1 (`wnode25`) | OK |
| Slurm MPI (job `61829`) | 4 × 1 | 4 | 1 (`wnode25`) | OK |
| Slurm ibrido (job `61830`) | 4 × 4 | 16 | 2 (`wnode26`, `wnode27`) | OK |
:::

Tutti i job risultano `COMPLETED 0:0` in `sacct`. L'ordine delle righe cambia da un
run all'altro (per esempio con 8 thread: 0, 3, 2, 6, 5, 1, 7, 4), perché i thread
stampano quando arrivano; non fa parte del risultato. I programmi di riferimento del
corso (`/srv/software2/lab/bin/hello_*`) producono lo stesso formato, con le stesse
maschere: per 2 × 2, `core affinity = 0,16` e `1,17`, come il nostro.

Il job ibrido, per esempio:

```{code-block} text
:class: terminal

Hello from thread 0/4 from rank 0/4 on wnode26 (core affinity = 0-3)
Hello from thread 0/4 from rank 1/4 on wnode26 (core affinity = 4-7)
Hello from thread 0/4 from rank 2/4 on wnode27 (core affinity = 0-3)
Hello from thread 0/4 from rank 3/4 on wnode27 (core affinity = 4-7)
... (16 righe in tutto: per ogni rank i thread 0, 1, 2, 3)
```

### 2. Dove finiscono processi e thread

**Idea.** La maschera dice su quali CPU logiche un thread può girare. Su `wnode25`
le CPU 0–15 sono i core fisici del socket 0 e 16–31 quelli del socket 1 (32–63 sono
i secondi hardware thread degli stessi core).

:::{table} Maschere di affinità nei job Slurm (da `--cpu-bind=verbose` e dal programma).
:name: tab-es02-masks

| Job | Task | Maschera | CPU logiche | Lettura |
|---|---|---|---|---|
| OpenMP (`61828`) | 0 | `0xf` | 0–3 | 4 core fisici del socket 0 per i 4 thread |
| MPI (`61829`) | 0, 1, 2, 3 | `0x1`, `0x10000`, `0x2`, `0x20000` | 0, 16, 1, 17 | un core fisico per rank, alternando i socket |
| Ibrido (`61830`) | 0, 1 su `wnode26`; 2, 3 su `wnode27` | `0xf`, `0xf0` su ogni nodo | 0–3, 4–7 | 4 core consecutivi per rank, 2 rank per nodo |
:::

- **OpenMP**: con `--cpus-per-task=4 --hint=nomultithread` il processo ha 4 core
  fisici diversi, non 2 core con i loro 2 hardware thread. `sacct` riporta però
  `AllocCPUS = 8`: con `nomultithread` Slurm assegna core interi, cioè entrambi gli
  hardware thread di ogni core, anche se il programma ne usa uno.
- **MPI**: i rank 0, 1, 2, 3 stanno sulle CPU 0, 16, 1, 17, cioè sul core 0 del
  socket 0, sul core 0 del socket 1, sul core 1 del socket 0, ... Senza
  `--distribution`, Slurm distribuisce i task alternando i socket, come avevamo
  visto per HPCG nell'esercizio 5.
- **Ibrido**: su ogni nodo i due rank hanno blocchi di 4 core consecutivi (0–3 e
  4–7), e i 4 thread di un rank condividono la stessa maschera. La maschera è del
  processo: dice dove i thread *possono* girare, non su quale core gira ciascuno.
  Che `wnode26` e `wnode27` abbiano la stessa numerazione di `wnode25` è
  plausibile (stessa feature `quanta` in `sinfo`), ma non è stato verificato con
  `lscpu`.

**Sul login node le maschere sono diverse** (righe `quick_mpi_*` del log): con
`mpiexec -n 1` o `-n 2` ogni rank ha `0,16` o `1,17`, cioè un core con i suoi due
hardware thread; con 3 o 4 rank ogni rank ha `0-7,16-23` o `8-15,24-31`, cioè un
intero socket. È il comportamento predefinito di Open MPI 4: lega i processi a un
core se sono al massimo 2, a un socket se sono di più. Il login node ha quindi una
numerazione diversa da `wnode25` (con 2 socket da 8 core, secondo queste maschere;
`lscpu` del login node non è nel log).

## Commenti

1. **Il programma diagnostico funziona** in tutti i casi richiesti: una riga per
   thread, $P \times T$ righe nel caso ibrido, rank e thread completi, e il job
   ibrido distribuito su 2 nodi distinti come chiesto da `--nodes=2`.
2. **Le maschere sono la parte più utile.** Il solo conteggio delle righe direbbe
   che "ci sono 4 thread", ma non se stanno su 4 core o su 1. Le maschere mostrano
   che Slurm, con `--hint=nomultithread` e `--cpus-per-task` ripetuto su `srun`,
   dà a ogni thread un core fisico suo. È il controllo che conviene ripetere prima
   di ogni misura di prestazioni (esercizi 3, 5, 6).
3. **Login node e nodi di calcolo non si comportano allo stesso modo**: `mpiexec`
   sul login node applica le regole di Open MPI, `srun` quelle di Slurm. I test sul
   login node servono solo a verificare il programma, non la disposizione.
4. Nei file `.err` compaiono messaggi di `module` ("Due to MODULEPATH changes...")
   dovuti alla riga `module use` negli script: sono innocui, perché il percorso dei
   moduli del corso è già nel `MODULEPATH` predefinito.

## Checkpoint

- 13 controlli su 13 superati: OpenMP con 1, 2, 4, 8 thread; 6 combinazioni
  `mpiexec`; job Slurm OpenMP (`61828`), MPI (`61829`) e ibrido (`61830`), tutti
  `COMPLETED 0:0`.
- Job ibrido: 16 righe = 4 rank × 4 thread su `wnode26` e `wnode27`.
- Maschere di affinità riprodotte (parte optional): un core fisico per thread nei
  job Slurm; legame a core o a socket con `mpiexec` sul login node.
- La validazione Python locale della versione precedente è superata da questi run
  in C su WILSON.
