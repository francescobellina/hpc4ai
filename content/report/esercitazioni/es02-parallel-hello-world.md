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

## Parametri

| Parametro | Valore |
|---|---|
| Dimensione del problema | numero di rank $P$ e thread per rank $T$ |
| Precisione numerica | non applicabile (nessun calcolo in virgola mobile) |
| Iterazioni / arresto | nessuna iterazione |
| Seed casuali | non applicabile |
| Ambiente | moduli WILSON: `GCC/13.2.0`, `OpenMPI/4.1.6` (ambiente gerarchico) |
| Richiesta Slurm | `--nodes`, `--ntasks=P`, `--cpus-per-task=T` |

:::{note}
I test sul login node servono solo a controlli molto brevi. Le esecuzioni reali
passano da Slurm con uno script di batch che carica gli stessi moduli usati per
compilare.
:::

## Implementazione

Il programma a memoria condivisa crea $T$ thread con OpenMP; il programma ibrido
avvia $P$ rank MPI, ciascuno dei quali crea $T$ thread OpenMP. Moduli e
compilazione su WILSON:

```bash
module use /srv/software/easybuild/hmns/x86-64-v2/modules/all/Core
module load GCC/13.2.0
module load OpenMPI/4.1.6

gcc   -fopenmp hello_shared_world.c   -o hello_shared_world
mpicc -fopenmp hello_parallel_world.c -o hello_parallel_world
```

Esecuzione:

```bash
export OMP_NUM_THREADS=4
./hello_shared_world

mpiexec -n 4 ./hello_parallel_world
```

Chiamate utili: `MPI_Get_processor_name` (MPI), `gethostname` (`<unistd.h>`),
`socket.gethostname` (Python); maschera di affinità con `sched_getaffinity`
(`<sched.h>`) o `os.sched_getaffinity` (Python, non su macOS).

## Procedura di validazione

- **Una riga per thread** nel caso a memoria condivisa, indipendente dall'ordine
  di stampa.
- **Conto delle righe**: esattamente $P \times T$ nel caso ibrido.
- **Presenza dei rank**: tutti i rank $0 \dots P-1$ compaiono, ciascuno con thread
  $0 \dots T-1$.
- **Separazione dei ruoli**: cambiare `OMP_NUM_THREADS` cambia i thread, non il
  numero di processi MPI; cambiare `mpiexec -n` cambia i rank.
- **Coerenza con la richiesta Slurm**: numero di righe, rank, thread e nomi dei
  nodi devono corrispondere a `--nodes`, `--ntasks`, `--cpus-per-task`.

## Risultati e plot

Validazione locale (Python `threading`), eseguita sul client macOS
(Apple M3 Pro, arm64) per riprodurre la **gerarchia** dei thread. L'output è una
riga per thread, l'ordine non fa parte del risultato:

```text
4 lines (expected 4), order not part of the result:
thread= 0 of  4 on MacBook-Pro-di-Francesco.local
thread= 1 of  4 on MacBook-Pro-di-Francesco.local
thread= 2 of  4 on MacBook-Pro-di-Francesco.local
thread= 3 of  4 on MacBook-Pro-di-Francesco.local
```

:::{note}
Il modulo Python `threading` riproduce la gerarchia dei thread, ma il codice
Python ordinario è limitato dal GIL e non gira necessariamente in parallelo su più
core. C con OpenMP sì.
:::

Su WILSON restano da produrre gli script di batch e gli output delle tre
esecuzioni (OpenMP, MPI, ibrido), con il conteggio $P \times T$ e le maschere di
affinità; il confronto con la richiesta Slurm è il criterio di accettazione.

## Commenti

- La demo locale conferma che il modello a **memoria condivisa** produce un thread
  distinto per indice, con una riga per thread, indipendentemente dall'ordine.
- Il caso Python non è una prova di parallelismo reale (GIL): la verifica su più
  core richiede OpenMP in C.
- I controlli chiave (conteggio righe, presenza dei rank, separazione rank/thread)
  sono definiti in modo che l'output su WILSON possa essere confrontato
  direttamente con la richiesta Slurm.

## Checkpoint

- Il programma diagnostico produce una riga per thread e, nel caso ibrido, una
  riga per combinazione rank/thread ($P \times T$).
- Validazione locale superata: 4 righe attese e 4 osservate, un thread per indice.
- Validazione su WILSON da completare: mancano output delle esecuzioni Slurm
  OpenMP, MPI e ibrido e le maschere di affinità.
- Il confronto con la richiesta Slurm è il criterio di accettazione principale.
