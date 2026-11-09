# Esercitazione 5 — Benchmarking e scaling con HPL e HPCG

:::{note} Consegna
Dalla traccia del corso (*Exercises for the report*, sezione 5). Eseguire il
benchmark HPL sul cluster WILSON con Slurm, poi il benchmark HPCG, e confrontare le
prestazioni ottenute con HPL, con HPCG e con il picco teorico dei nodi. Quale
benchmark raggiunge la frazione più alta del picco, e perché?

1. **Esecuzione su un nodo**: entrambi i benchmark supportano OpenMP e MPI. Partire
   da una baseline valida su un nodo e provare diverse opzioni di
   parallelizzazione, cambiando **un solo aspetto alla volta**, con griglia dei
   processi e thread coerenti con la richiesta Slurm:
   $P \cdot Q = N_{\text{tasks}}$ e thread per processo $= N_{\text{CPU per task}}$
   (`OMP_NUM_THREADS` uguale a `--cpus-per-task`).
2. **Per ogni run**: conservare input e output completi e registrare job ID,
   partizione, nodi, tipo di nodo, task per nodo, CPU per task, `OMP_NUM_THREADS`,
   tempo e memoria richiesti, moduli; a fine job, stato finale, exit code ed elapsed
   da `sacct`; controllare il test del residuo di HPL e la validità di HPCG prima di
   usare le prestazioni.
3. **Studio di scaling**: per HPL, strong scaling a dimensione globale fissa e
   studio *memory-scaled* con memoria per processo costante ($N_p \propto \sqrt{p}$);
   per HPCG, weak scaling (griglia locale fissa) e strong scaling (griglia globale
   fissa), confrontando i rate validati $R_p$ con
   $S_p^{(R)} = R_p/R_1$ ed $E_p^{(R)} = S_p^{(R)}/p$ e la stessa durata richiesta in
   `hpcg.dat`.
4. **Picco teorico**: stimare $R_{\text{peak}} = N_{\text{core}}\, f\,
   (\text{flop per ciclo})$ dichiarando precisione, numero di core, frequenza,
   larghezza vettoriale e operazioni per ciclo.
5. **(Optional)** Confronto fra i tipi di nodo della partizione `lab4`, senza
   mescolare generazioni di processore nella stessa curva di scaling.
:::

:::{note} Stato del lavoro
Questa pagina contiene la parte su un nodo (punti 1, 2, 4 e il confronto con il
picco su un nodo). Gli studi di scaling del punto 3 sono in esecuzione e saranno
aggiunti nella sezione dei risultati.
:::

:::{tip} L'esercizio in breve
**Cosa misuriamo.** Due benchmark opposti sullo stesso tipo di nodo. HPL risolve un
sistema di equazioni denso: quasi tutto calcolo, con ogni dato riusato molte volte.
HPCG risolve un sistema sparso: poche operazioni per ogni dato letto, quindi passa il
tempo ad aspettare la memoria. Il **picco teorico** è quello che il nodo farebbe se
ogni core eseguisse il massimo di operazioni a ogni ciclo.

**La domanda su un nodo.** Un nodo ha 16 core (2 socket da 8). Possiamo usarli come
16 processi MPI indipendenti, come un solo processo con 16 thread o con una via di
mezzo (4 processi × 4 thread, 2 × 8, ...). Quale divisione va più veloce, e perché?

**Cosa abbiamo trovato.**

- **HPL**: la divisione conta poco. Tutte le ripartizioni con griglia equilibrata
  stanno entro il 3.5%; la migliore è **2 processi × 8 thread**, uno per socket
  ($260.3 \pm 3.1$ GFLOP/s), mentre la peggiore è 16 processi con griglia
  sbilanciata 1 × 16 (237.6 GFLOP/s, −8.7%).
- **HPCG**: la divisione conta moltissimo. **16 processi × 1 thread** dà 8.70 GFLOP/s,
  1 processo × 16 thread solo 1.34 (−85%), perché la parte più pesante (il
  multigrid) non sfrutta i thread.
- **Picco**: alla frequenza misurata durante il run (2.40 GHz) un nodo può fare
  307 GFLOP/s. HPL ne usa l'**85%**, HPCG il **2.8%**: il primo è limitato dal
  calcolo, il secondo dalla memoria.

Il resto della pagina mostra come sono stati costruiti i run, come sono stati
validati e i dettagli di ogni misura.
:::

:::{note} Richiami teorici
- **HPL** risolve un sistema lineare denso $A\boldsymbol{x} = \boldsymbol{b}$ di
  ordine $N$ con fattorizzazione LU a pivoting parziale. Esegue circa
  $\tfrac{2}{3}N^3 + 2N^2$ operazioni e memorizza $8N^2$ byte. La matrice è divisa in
  blocchi $NB \times NB$ distribuiti ciclicamente su una griglia di $P \times Q$
  processi MPI. Quasi tutto il lavoro è prodotto matrice-matrice (BLAS di livello 3,
  `DGEMM`): ogni dato letto dalla memoria viene riusato molte volte (alta intensità
  operazionale), quindi HPL è limitato dalla potenza di calcolo.
- **HPCG** risolve un sistema sparso (stencil a 27 punti su una griglia 3D) con il
  gradiente coniugato precondizionato da un multigrid con smoother di Gauss-Seidel
  simmetrico. Ogni dato letto serve a pochissime operazioni (bassa intensità
  operazionale): HPCG è limitato dalla banda di memoria e dalla comunicazione. La
  durata è un **input** (`hpcg.dat`), quindi si confronta il **rate validato** in
  GFLOP/s, non il tempo.
- **Picco teorico**: $R_{\text{peak}} = N_{\text{core}} \cdot f \cdot r$, con $f$ la
  frequenza di clock e $r$ le operazioni in virgola mobile per ciclo per core.
- **Processi e thread**: un processo MPI è un programma separato con la sua memoria
  e comunica con gli altri scambiando messaggi; i thread OpenMP sono "lavoratori"
  dentro lo stesso processo e condividono la sua memoria. Su un nodo da 16 core si
  può scegliere qualsiasi combinazione $\text{processi} \times \text{thread} = 16$:
  16 processi da 1 thread (solo MPI), 1 processo da 16 thread (solo OpenMP) o
  qualcosa in mezzo (ibrido).
:::

## Parametri

:::{table} Macchina, software e parametri dei benchmark (job `61221`–`61344`).
:name: tab-es05-params

| Parametro | Valore |
|---|---|
| Partizione e nodi | `wilson`, con `--constraint=sandy_bridge`: nodi `wnode01`–`wnode08` |
| CPU (da `lscpu` su `wnode01`) | 2 × Intel Xeon E5-2650 @ 2.00 GHz (massimo 2.8 GHz), 8 core per socket, 2 hardware thread per core; AVX presente, FMA e AVX2 assenti |
| Cache e NUMA | L1d 32 KiB e L2 256 KiB per core, L3 20 MiB per socket; 2 nodi NUMA: CPU logiche 0–7 e 16–23 sul socket 0, 8–15 e 24–31 sul socket 1 |
| Memoria per nodo | 62500 MB configurati in Slurm (`sinfo`) |
| Moduli | `GCC/13.2.0`, `OpenMPI/4.1.6`, poi `HPL/2.3` o `HPCG/3.1`; BLAS: `FlexiBLAS/3.3.1` con `OpenBLAS/0.3.24` |
| Risorse Slurm | 1 nodo esclusivo (`--exclusive`), tutta la memoria (`--mem=0`, `ReqMem` 62500M), `--hint=nomultithread` |
| HPL | variante `WR11C2R4`: `NB` = 192, `PFACT` Right, `NBMIN` 4, `NDIV` 2, `RFACT` Crout, `BCAST` 1ringM, `DEPTH` 1, `SWAP` mix (soglia 64), soglia del residuo 16.0; $N$ = 12288, 24576, 41280 |
| HPCG | durata richiesta 60 s; griglia globale 416 × 208 × 208 in tutte le ripartizioni |
| Ripetizioni | HPL a $N$ = 41280: 3 run per ripartizione; HPCG: 1 run per ripartizione, più la baseline ripetuta |
| Frequenza misurata | 2.40 GHz con `perf stat` durante HPL (job `61344`) |
:::

## Implementazione

**In breve.** Ogni run è un job Slurm a sé, in una cartella con il suo file di input
e il suo script batch. Lo script chiede a Slurm *quanti processi* e *quanti core per
processo* usare, imposta tanti thread quanti core e lancia il benchmark. Per provare
una ripartizione diversa si cambiano solo queste righe nei file del corso; tutto il
resto resta identico.

### Gli script del corso, riga per riga

Il corso fornisce in `/srv/data/wilson/project/hpc4ai/exercises/benchmark/` due script
batch, `HPL_wilson_n4c4_script.sh` e `HPCG_wilson_n16c1_script.sh`, e i due file di
input. Lo script HPL (il nome dice *n4c4*: 4 task, 4 CPU per task) è:

```bash
#!/usr/bin/bash
#SBATCH --job-name=HPL_single_node
#SBATCH --output=%x.%j.out
#SBATCH --error=%x.%j.err
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=4
#SBATCH --cpus-per-task=4
#SBATCH --hint=nomultithread
#SBATCH --distribution=block:block
#SBATCH --exclusive
#SBATCH --mem=0
#SBATCH --partition=wilson
#SBATCH --time=4:00:00

set -eo pipefail

cd "$SLURM_SUBMIT_DIR"
module load GCC/13.2.0 OpenMPI/4.1.6
module load HPL/2.3
export OMP_NUM_THREADS="$SLURM_CPUS_PER_TASK"

printf 'Job: %s; partition: %s; nodes: %s\n' \
    "$SLURM_JOB_ID" "$SLURM_JOB_PARTITION" "$SLURM_JOB_NODELIST"
printf 'Nodes: %s; MPI tasks: %s; tasks per node: %s\n' \
    "$SLURM_JOB_NUM_NODES" "$SLURM_NTASKS" "$SLURM_TASKS_PER_NODE"
printf 'CPUs per task: %s; OpenMP threads per task: %s\n' \
    "$SLURM_CPUS_PER_TASK" "$OMP_NUM_THREADS"
module list 2>&1
srun --cpu-bind=verbose --cpus-per-task="$SLURM_CPUS_PER_TASK" xhpl
```

:::{table} Significato delle direttive Slurm e delle righe dello script, con la loro lettura intuitiva.
:name: tab-es05-sbatch

| Riga | Cosa fa | In pratica |
|---|---|---|
| `--nodes=1` | Numero di nodi | Un solo computer del cluster |
| `--ntasks-per-node=4` | **Task** per nodo: ogni task è un processo MPI | 4 copie del programma, ognuna con la sua memoria, che si parlano con messaggi |
| `--cpus-per-task=4` | CPU riservate a ogni task | Ogni processo ha 4 core suoi, su cui girano i suoi 4 thread |
| `--hint=nomultithread` | Una sola CPU logica per core fisico | Per Slurm una "CPU" è un hardware thread: senza questa riga, 4 CPU potrebbero essere 2 core con i loro 2 hardware thread |
| `--distribution=block:block` | Come si distribuiscono i task sui nodi (prima parte) e sui socket (seconda parte) | `block` riempie il socket 0 prima di passare al socket 1, quindi i task consecutivi stanno vicini |
| `--exclusive` | Nodo non condiviso con altri job | Nessun altro programma disturba le misure (`sacct` riporta tutte le 32 CPU logiche allocate) |
| `--mem=0` | Tutta la memoria configurata del nodo | 62500 MB disponibili per la matrice |
| `--partition=wilson`, `--time` | Partizione e tempo massimo | Il job viene ucciso se supera il tempo |
| `--output=%x.%j.out` | File di output con nome del job (`%x`) e job ID (`%j`) | Ogni run lascia un file distinto, mai sovrascritto |
| `export OMP_NUM_THREADS="$SLURM_CPUS_PER_TASK"` | Numero di thread per processo uguale alle CPU per task | È il vincolo della consegna: tanti thread quanti core riservati, né di più (sovraccarico) né di meno (core inutilizzati) |
| `srun ... --cpus-per-task=... xhpl` | Lancia i task MPI e assegna i core a ciascuno | Ripetere `--cpus-per-task` su `srun` garantisce che ogni task riceva davvero i suoi core, perché a seconda della versione di Slurm `srun` non eredita questo valore da `sbatch` |
| `--cpu-bind=verbose` | Stampa su `.err` la maschera dei core di ogni task | La prova di dove è finito ogni processo (vedi sotto) |
:::

In HPL i thread non vengono da OpenMP dentro `xhpl`, ma dalla libreria BLAS
multithread (`FlexiBLAS` con `OpenBLAS`), che legge `OMP_NUM_THREADS`: con 4 task ×
4 CPU, ogni processo esegue le sue moltiplicazioni di matrici con 4 thread. Lo
script HPCG è identico salvo il modulo `HPCG/3.1`, 16 task × 1 CPU, nessuna riga
`--distribution` e la variabile `PMIX_MCA_psec=^munge`, che il corso indica come
necessaria per l'avvio di MPI su WILSON.

### Il file `HPL.dat`

`HPL.dat` ha 31 righe; la consegna permette di cambiare solo le righe 6 ($N$), 8
($NB$), 11 ($P$) e 12 ($Q$). Le prime righe del file del corso:

```text
HPLinpack benchmark input file
Innovative Computing Laboratory, University of Tennessee
HPL.out                             # output file name (if any)
6                                   # device out (6=stdout,7=stderr,file)
1                                   # of problems sizes (N)
12288                               # Ns
1                                   # of NBs
192                                 # NBs
0                                   # PMAP process mapping (0=Row-,1=Column-major)
1                                   # of process grids (P x Q)
2                                   # Ps
2                                   # Qs
```

Con $N = 12288$ la matrice occupa $8N^2 \approx 1.1$ GiB, il caso piccolo per
verificare la configurazione. Per le misure si usa $N = 41280$ ($= 215 \times 192$,
multiplo di $NB$): $8N^2 \approx 12.7$ GiB, circa un quinto della memoria del nodo,
e $\tfrac{2}{3}N^3 \approx 4.7 \times 10^{13}$ operazioni, cioè circa 3 minuti a
250 GFLOP/s.

### Come sono state generate le configurazioni

Ogni configurazione ha la sua cartella in `~/es05/`, con input, script batch e
output, come chiede la consegna. Le cartelle sono create da
[`codes/exec5/es05.sh`](../codes/exec5/README.md): parte dai file del corso e cambia
solo le righe necessarie. Per lo script batch:

```bash
# Copia uno script batch del corso cambiando solo layout, nome, tempo e vincolo sul nodo.
patch_script() {
    awk -v name="$2" -v nodes="$3" -v nt="$4" -v nc="$5" -v t="$6" -v extra="${7:-}" -v cons="$CONSTRAINT" '
        /^#SBATCH --job-name=/        { print "#SBATCH --job-name=" name; next }
        /^#SBATCH --nodes=/           { print "#SBATCH --nodes=" nodes; next }
        /^#SBATCH --ntasks-per-node=/ { print "#SBATCH --ntasks-per-node=" nt; next }
        /^#SBATCH --cpus-per-task=/   { print "#SBATCH --cpus-per-task=" nc; next }
        /^#SBATCH --time=/            { print "#SBATCH --time=" t; next }
        /^#SBATCH --partition=/       { print; print "#SBATCH --constraint=" cons; next }
        /^srun .*xhp(l|cg)$/ && extra != "" { print $0 " " extra; next }
        { print }' "$1"
}
```

e per `HPL.dat` un `awk` sostituisce il numero iniziale delle righe 6, 11 e 12. Per
esempio, la configurazione **2 × 8** (2 processi da 8 thread) differisce dai file del
corso solo per queste righe. Il `diff` è calcolato sui file registrati nel log:

```diff
--- reference/HPL.dat
+++ hpl/15_N41280_2x8_P1Q2/HPL.dat
@@ -6 +6 @@
-12288                               # Ns
+41280                               # Ns
@@ -11 +11 @@
-2                                   # Ps
+1                                   # Ps
--- reference/HPL_wilson_n4c4_script.sh
+++ hpl/15_N41280_2x8_P1Q2/HPL_wilson_n2c8_script.sh
@@ -2 +2 @@
-#SBATCH --job-name=HPL_single_node
+#SBATCH --job-name=hpl_15_N41280_2x8_P1Q2
@@ -6,2 +6,2 @@
-#SBATCH --ntasks-per-node=4
-#SBATCH --cpus-per-task=4
+#SBATCH --ntasks-per-node=2
+#SBATCH --cpus-per-task=8
@@ -13 +13,2 @@
-#SBATCH --time=4:00:00
+#SBATCH --constraint=sandy_bridge
+#SBATCH --time=00:30:00
```

Lettura: `--ntasks-per-node=4` → `2` e `--cpus-per-task=4` → `8` trasformano "4
processi da 4 core" in "2 processi da 8 core"; la griglia diventa $P \times Q = 1
\times 2$ perché i processi sono 2 (la riga 12, $Q = 2$, era già giusta);
`OMP_NUM_THREADS` segue da solo, perché lo script lo ricava da `--cpus-per-task`. Il
vincolo `--constraint=sandy_bridge` serve perché la partizione `wilson` contiene tre
generazioni di CPU (`sinfo`: Sandy Bridge `wnode01`–`08`, Ivy Bridge `wnode09`–`12`,
Haswell `wnode13`–`20`) con picchi diversi, che non vanno mescolate. Il tempo massimo è
ridotto a 30 minuti per entrare prima in coda.

:::{table} Configurazioni HPL su un nodo: righe `#SBATCH` e griglia in `HPL.dat`.
:name: tab-es05-hpl-config

| Ripartizione | `--ntasks-per-node` | `--cpus-per-task` = `OMP_NUM_THREADS` | $P \times Q$ | $N$ |
|---|---|---|---|---|
| 16 × 1 (solo MPI) | 16 | 1 | 4 × 4, 2 × 8, 1 × 16 | 41280 |
| 8 × 2 | 8 | 2 | 2 × 4 | 41280 |
| 4 × 4 (baseline del corso) | 4 | 4 | 2 × 2 | 12288, 24576, 41280 |
| 2 × 8 (un processo per socket) | 2 | 8 | 1 × 2 | 41280 |
| 1 × 16 (solo thread) | 1 | 16 | 1 × 1 | 41280 |
:::

### HPCG: griglia locale e griglia dei processi

In `hpcg.dat` la riga 3 è la griglia **locale** di ogni processo e la riga 4 la
durata richiesta (60 s). La griglia **globale** è il prodotto della griglia locale
per la griglia dei processi $n_{px} \times n_{py} \times n_{pz}$. Per confrontare le
ripartizioni sullo **stesso problema** (416 × 208 × 208) la griglia locale cresce
quando i processi diminuiscono, e la griglia dei processi è fissata con le opzioni
`--npx`, `--npy`, `--npz` di `xhpcg`; per esempio, per 2 × 8:

```diff
-104 104 104
+208 208 208
...
-srun --cpu-bind=verbose --cpus-per-task="$SLURM_CPUS_PER_TASK" xhpcg
+srun --cpu-bind=verbose --cpus-per-task="$SLURM_CPUS_PER_TASK" xhpcg --npx=2 --npy=1 --npz=1
```

:::{table} Configurazioni HPCG su un nodo (griglia globale 416 × 208 × 208, confermata dall'output di ogni run).
:name: tab-es05-hpcg-config

| Processi × thread | Griglia locale (`hpcg.dat`, riga 3) | Griglia dei processi |
|---|---|---|
| 16 × 1 (baseline del corso) | 104 × 104 × 104 | 4 × 2 × 2 |
| 8 × 2 | 208 × 104 × 104 | 2 × 2 × 2 |
| 4 × 4 | 208 × 104 × 208 | 2 × 2 × 1 |
| 2 × 8 | 208 × 208 × 208 | 2 × 1 × 1 |
| 1 × 16 | 416 × 208 × 208 | 1 × 1 × 1 |
:::

### Dove finiscono i processi: le maschere di `--cpu-bind=verbose`

`--cpu-bind=verbose` scrive, per ogni task, una maschera esadecimale: il bit $k$ a 1
significa "questo task può girare sulla CPU logica $k$". Sul nodo Sandy Bridge le CPU
0–7 sono i core del socket 0 e le CPU 8–15 quelli del socket 1. Alcuni esempi dai
file `.err`:

```{code-block} text
:class: terminal

# HPL 2 x 8 (job 61285): un processo per socket
cpu-bind=MASK - wnode07, task  0  0 [8247]: mask 0xff set
cpu-bind=MASK - wnode07, task  1  1 [8248]: mask 0xff00 set
# HPL 4 x 4 (job 61284): blocchi di 4 core consecutivi, due per socket
cpu-bind=MASK - wnode06, task  0  0 [7399]: mask 0xf set
cpu-bind=MASK - wnode06, task  1  1 [7400]: mask 0xf0 set
cpu-bind=MASK - wnode06, task  2  2 [7401]: mask 0xf00 set
cpu-bind=MASK - wnode06, task  3  3 [7402]: mask 0xf000 set
# HPL 1 x 16 (job 61286): un solo processo su entrambi i socket
cpu-bind=MASK - wnode08, task  0  0 [7219]: mask 0xffff set
# HPCG 16 x 1 (job 61287): senza --distribution=block:block i task alternano i socket
cpu-bind=MASK - wnode01, task  0  0 [9583]: mask 0x1 set
cpu-bind=MASK - wnode01, task  1  1 [9584]: mask 0x100 set
cpu-bind=MASK - wnode01, task  2  2 [9585]: mask 0x2 set
cpu-bind=MASK - wnode01, task  3  3 [9586]: mask 0x200 set
```

`0xff` = bit 0–7 = tutto il socket 0; `0xff00` = bit 8–15 = tutto il socket 1;
`0xffff` = tutti i 16 core. Le maschere confermano che ogni processo ha esattamente
i core richiesti e mostrano la differenza di distribuzione fra i due script: HPL
riempie un socket alla volta (`block:block`), HPCG usa il default di Slurm, che
alterna i socket (task 0 sul core 0, task 1 sul core 8, ...).

### Comandi

Sul login node di WILSON, nella home:

```bash
bash es05.sh setup     # file del corso, sinfo, module spider, lscpu, baseline
bash es05.sh node      # ripartizioni MPI x thread su un nodo
bash es05.sh repeat    # run 2 e 3 delle ripartizioni HPL, run con perf stat
bash es05.sh collect   # input, output, sacct e tabella riassuntiva in un log
```

Sul Mac, il log di `collect` viene letto da
[`codes/exec5/analyze_es05.py`](../codes/exec5/README.md), che produce le tabelle e le
figure di questa pagina:

```bash
.venv/bin/python content/report/codes/exec5/analyze_es05.py results/es05/collect_20261109_121824.txt
```

## Procedura di validazione

- **HPL**: ogni run calcola il residuo scalato
  $\lVert A\boldsymbol{x}-\boldsymbol{b}\rVert_\infty / \big(\varepsilon\,(\lVert A\rVert_\infty \lVert\boldsymbol{x}\rVert_\infty + \lVert\boldsymbol{b}\rVert_\infty)\,N\big)$
  con $\varepsilon = 1.11 \times 10^{-16}$, e il test passa se è minore di 16. Tutti i
  24 run danno `PASSED`, con residui fra $2.1 \times 10^{-3}$ e $5.3 \times 10^{-3}$,
  oltre tre ordini di grandezza sotto la soglia. Le ripetizioni della stessa
  ripartizione danno lo stesso residuo a tutte le cifre stampate: la matrice casuale
  è generata in modo deterministico, quindi le ripetizioni risolvono lo stesso
  problema.
- **HPCG**: il risultato è `VALID` solo se superano i test di convergenza spettrale,
  di simmetria, del numero di iterazioni e di riproducibilità; tutti i 6 run sono
  `VALID`. Estratto dal run 16 × 1 (job `61287`):

  ```{code-block} text
  :class: terminal

  Spectral Convergence Tests::Result=PASSED
  Departure from Symmetry |x'Ay-y'Ax|/(2*||x||*||A||*||y||)/epsilon::Result=PASSED
  Iteration Count Information::Result=PASSED
  Reproducibility Information::Result=PASSED
  Final Summary::HPCG result is VALID with a GFLOP/s rating of=8.70409
  ```

  HPCG avverte che i risultati ufficiali richiedono almeno 1800 s e che usa le
  versioni di riferimento dei kernel ("Performance results are most likely
  suboptimal"); la consegna indica che i 60 s sono sufficienti per l'esercizio.
- **Slurm**: tutti i job risultano `COMPLETED` con exit code `0:0` in `sacct`.
- **Layout**: l'intestazione di ogni output conferma la richiesta, per esempio
  `MPI tasks: 2; tasks per node: 2` e `CPUs per task: 8; OpenMP threads per task: 8`
  per 2 × 8; per HPL $P \cdot Q$ coincide con il numero di task, per HPCG la griglia
  globale stampata è sempre 416 × 208 × 208; le maschere confermano il piazzamento.

## Risultati e plot

I log completi da cui provengono tutti i numeri sono
{download}`setup_20261109_110357.txt <../../../results/es05/setup_20261109_110357.txt>`
(file del corso, `sinfo`, moduli),
{download}`collect_20261109_115110.txt <../../../results/es05/collect_20261109_115110.txt>`
(primo giro) e
{download}`collect_20261109_121824.txt <../../../results/es05/collect_20261109_121824.txt>`
(tutti i run su un nodo, con le ripetizioni).

### 1. Baseline con i file del corso

:::{table} Baseline con i file del corso non modificati.
:name: tab-es05-baseline

| Benchmark | Job | Nodo | Configurazione | Risultato | Validità | Elapsed |
|---|---|---|---|---|---|---|
| HPL | `61221` | `wnode01` | $N$ = 12288, $NB$ = 192, 4 task × 4 thread, $P \times Q$ = 2 × 2 | 203.3 GFLOP/s in 6.09 s | `PASSED` ($5.3 \times 10^{-3}$) | 0:12 |
| HPCG | `61222` | `wnode03` | 16 × 1, griglia locale 104³, 60 s | 8.73 GFLOP/s | `VALID` | 2:58 |
:::

### 2. HPL: dimensione del problema

**Idea.** In una matrice più grande la parte di calcolo pesante (prodotti fra
blocchi, che sfruttano bene i core) cresce più in fretta delle parti di contorno
(fattorizzazione dei pannelli, scambi, comunicazione). Ci aspettiamo quindi più
GFLOP/s al crescere di $N$. Con la stessa ripartizione (4 × 4, griglia 2 × 2):

:::{table} HPL al variare di $N$ (4 task × 4 thread). Per $N$ = 41280, media di 3 run.
:name: tab-es05-hpl-n

| $N$ | Memoria matrice | Time (s) | GFLOP/s | Frazione del picco a 2.40 GHz |
|---|---|---|---|---|
| 12288 | 1.1 GiB | 6.09 | 203.3 | 66.2% |
| 24576 | 4.5 GiB | 41.71 | 237.3 | 77.3% |
| 41280 | 12.7 GiB | 182.8 | 256.6 | 83.5% |
:::

Il lavoro utile cresce come $N^3$, mentre le parti che non sfruttano bene i core
(fattorizzazione dei pannelli, scambi di righe, comunicazione) crescono più
lentamente, come $N^2$: più grande è la matrice, più tempo si passa in `DGEMM`, che
lavora vicino al picco. Per questo il confronto delle ripartizioni usa $N$ = 41280 e
non il caso piccolo della baseline.

### 3. HPL: come dividere i 16 core

**Idea.** Stesso problema ($N$ = 41280) e stessi 16 core: cambia solo come li
dividiamo fra processi MPI e thread, e come disponiamo i processi nella griglia
$P \times Q$. Se la divisione non contasse, tutte le righe darebbero lo stesso
risultato entro il rumore fra run identici (circa l'1%).

:::{table} HPL a $N$ = 41280 per ripartizione dei 16 core (processi MPI × thread) e griglia $P \times Q$; 3 run per configurazione.
:name: tab-es05-hpl-layout

| Ripartizione (griglia) | Run (GFLOP/s) | Media | Dev. std | Rispetto al migliore |
|---|---|---|---|---|
| **2 × 8 (1 × 2)** | 261.9 / 256.8 / 262.3 | **260.3** | 3.1 | — |
| 4 × 4 (2 × 2) | 257.4 / 256.4 / 255.9 | 256.6 | 0.8 | −1.4% |
| 8 × 2 (2 × 4) | 251.3 / 257.6 / 256.3 | 255.1 | 3.3 | −2.0% |
| 1 × 16 (1 × 1) | 248.2 / 253.7 / 253.0 | 251.6 | 3.0 | −3.3% |
| 16 × 1 (4 × 4) | 251.9 / 252.0 / 249.4 | 251.1 | 1.5 | −3.5% |
| 16 × 1 (2 × 8) | 246.7 / 246.3 / 242.2 | 245.1 | 2.5 | −5.9% |
| 16 × 1 (1 × 16) | 235.9 / 238.5 / 238.4 | 237.6 | 1.4 | −8.7% |
:::

```{figure} ../figures/es05-hpl-layout.png
:name: fig-es05-hpl-layout
:width: 100%

HPL a $N$ = 41280 su un nodo Sandy Bridge per ripartizione dei 16 core
(processi MPI × thread, griglia $P \times Q$). Punti pieni: media di 3 run; barre:
± deviazione standard; cerchi vuoti: singoli run. L'asse parte da 232 GFLOP/s per
rendere leggibili differenze di pochi punti percentuali.
```

La ripartizione migliore è **2 × 8**, un processo MPI per socket con 8 thread BLAS
ciascuno. Il distacco da 4 × 4 (1.4%) è dell'ordine di una deviazione standard, quindi
le due sono quasi equivalenti; quello da solo MPI (16 × 1, −3.5%) supera il rumore.
L'effetto più grande è la **forma della griglia**: con 16 processi, passare da
4 × 4 a 1 × 16 costa l'8.7%.

### 4. HPCG: come dividere i 16 core

**Idea.** Stessa domanda per HPCG, a problema fisso (416 × 208 × 208). Qui il
risultato dipende da quanto ogni parte del calcolo sa usare i thread: una parte che
gira su un thread solo lascia fermi gli altri core del suo processo.

:::{table} HPCG a griglia globale fissa 416 × 208 × 208, 60 s richiesti: rate validato, rate dei due kernel principali (GFLOP/s), tempo di setup e durata del job.
:name: tab-es05-hpcg-layout

| Processi × thread | Rate validato | SpMV | MG | Setup (s) | Tempo misurato (s) | Elapsed |
|---|---|---|---|---|---|---|
| **16 × 1** (job `61287`) | **8.70** | 9.26 | 8.96 | 8.3 | 75.3 | 2:59 |
| 8 × 2 (job `61288`) | 7.46 (−14%) | 9.25 | 7.57 | 12.5 | 87.3 | 3:33 |
| 4 × 4 (job `61289`) | 5.21 (−40%) | 9.30 | 5.07 | 20.1 | 62.2 | 4:00 |
| 2 × 8 (job `61290`) | 3.15 (−64%) | 9.28 | 2.88 | 38.1 | 102.6 | 6:42 |
| 1 × 16 (job `61291`) | 1.34 (−85%) | 4.68 | 1.22 | 114.3 | 237.6 | 15:53 |
:::

```{figure} ../figures/es05-hpcg-layout.png
:name: fig-es05-hpcg-layout
:width: 100%

HPCG su un nodo Sandy Bridge per ripartizione dei 16 core, a problema fisso: rate
validato e rate dei kernel SpMV (prodotto matrice-vettore sparso) e MG (multigrid,
che contiene lo smoother di Gauss-Seidel).
```

Per HPCG la ripartizione migliore è nettamente **solo MPI, 16 × 1**; la baseline
ripetuta (8.73 contro 8.70 GFLOP/s) mostra una variabilità dello 0.3%, molto più
piccola delle differenze fra ripartizioni, per cui non servono altre ripetizioni.
Il campo `Threads per processes` dell'output vale 2, 4, 8 e 16: il modulo usa
davvero OpenMP. Il kernel SpMV resta a circa 9.3 GFLOP/s fino a 8 thread, mentre MG
crolla da 8.96 a 1.22 GFLOP/s.

### 5. Frequenza effettiva e picco teorico

**Idea.** Il picco è core × frequenza × operazioni per ciclo. Le operazioni per ciclo
dipendono dall'architettura; la frequenza invece cambia durante il run (turbo), quindi
va misurata invece che presa dalla scheda tecnica.

Un run 2 × 8 in più (job `61344`, 261.9 GFLOP/s, come gli altri 2 × 8) esegue ogni
processo sotto `perf stat`:

```{code-block} text
:class: terminal

[fbellina2@wilson 17_N41280_2x8_P1Q2_perf]$ cat perfstat.0.txt
 Performance counter stats for 'xhpl':

 3,464,210,857,614      cycles:u                         #    2.395 GHz
      1,446,209.76 msec task-clock:u                     #    5.536 CPUs utilized
[fbellina2@wilson 17_N41280_2x8_P1Q2_perf]$ cat perfstat.1.txt
 Performance counter stats for 'xhpl':

 3,460,796,236,402      cycles:u                         #    2.404 GHz
      1,439,406.02 msec task-clock:u                     #    5.510 CPUs utilized
```

Il rapporto fra cicli e tempo CPU dà la frequenza media effettiva durante HPL,
**2.40 GHz**: sotto carico la CPU gira sopra la frequenza base (2.0 GHz) grazie al
turbo, ma sotto il massimo (2.8 GHz). Le operazioni per ciclo vengono
dall'architettura: Sandy Bridge ha istruzioni AVX a 256 bit (4 valori in doppia
precisione) e, per ciclo, un'unità di somma e una di moltiplicazione vettoriali, senza
FMA; `lscpu` conferma `avx` e l'assenza di `fma` e `avx2`. Quindi
$r = 4 \times 2 = 8$ flop/ciclo per core in doppia precisione e

$$R_{\text{peak}} = 16 \text{ core} \times 2.40 \times 10^9 \ \tfrac{\text{cicli}}{\text{s}} \times 8 \ \tfrac{\text{flop}}{\text{ciclo}} = 307 \ \text{GFLOP/s per nodo}.$$

:::{table} Picco teorico di un nodo (doppia precisione, 16 core, 8 flop/ciclo) secondo l'ipotesi sulla frequenza, e frazione raggiunta dai migliori risultati su un nodo.
:name: tab-es05-peak

| Frequenza | $R_{\text{peak}}$ (GFLOP/s) | HPL 2 × 8 (260.3) | HPCG 16 × 1 (8.70) |
|---|---|---|---|
| base, 2.0 GHz | 256.0 | 101.7% | 3.40% |
| **misurata, 2.40 GHz** | **307.1** | **84.8%** | **2.83%** |
| turbo massimo, 2.8 GHz | 358.4 | 72.6% | 2.43% |
:::

Un'efficienza sopra il 100% con la frequenza base mostra che quella ipotesi non
descrive il run: si usa la frequenza misurata. La frequenza è misurata durante HPL e
viene usata anche per HPCG, assumendo lo stesso clock con tutti i core attivi.

### 6. Tempo del job e tempo del benchmark

**Idea.** Il tempo del job non coincide con il tempo del benchmark: prima e dopo la
parte misurata ci sono l'avvio, la generazione della matrice e il controllo del
risultato. L'`Elapsed` di Slurm comprende tutto il job, il `Time` di HPL solo la soluzione del
sistema:

:::{table} HPL a $N$ = 41280: elapsed del job, tempo del benchmark e loro differenza (medie di 3 run).
:name: tab-es05-elapsed

| Ripartizione | Processi | Elapsed (s) | Time HPL (s) | Differenza (s) | Differenza × processi (s) |
|---|---|---|---|---|---|
| 16 × 1 (4 × 4) | 16 | 201 | 186.8 | 14 | 228 |
| 8 × 2 | 8 | 208 | 183.9 | 24 | 196 |
| 4 × 4 | 4 | 226 | 182.8 | 44 | 174 |
| 2 × 8 | 2 | 271 | 180.2 | 91 | 181 |
| 1 × 16 | 1 | 353 | 186.4 | 167 | 167 |
:::

La parte fuori dal benchmark raddoppia ogni volta che i processi si dimezzano, e il
prodotto differenza × processi resta fra 167 e 228 s: è il comportamento di una fase
eseguita da ogni processo sulla sua parte di matrice con un solo thread, come la
generazione della matrice casuale e il controllo del residuo.

## Commenti

1. **Come dividere i 16 core: HPL.** Tutte le ripartizioni che non sbilanciano la
   griglia stanno entro il 3.5%, perché quasi tutto il tempo è in `DGEMM`, che scala
   bene sia con più processi sia con più thread. La migliore è un processo per
   socket (2 × 8). Un'interpretazione plausibile: rispetto a 16 processi, due
   processi grandi scambiano meno messaggi e duplicano meno lavoro di
   coordinamento; rispetto a un unico processo (1 × 16), ognuno tiene i suoi dati
   nella memoria del proprio socket. La forma
   della griglia pesa di più: a ogni passo HPL fattorizza un pannello di colonne,
   lavoro che spetta a una sola colonna di processi della griglia (i $P$ processi di
   quella colonna), mentre gli altri aspettano; con griglia 1 × 16 un solo processo da
   1 thread fattorizza ogni pannello e il pannello va poi inviato agli altri 15. È
   un'interpretazione coerente con il calo dell'8.7%, non una misura diretta.
2. **Come dividere i 16 core: HPCG.** Qui conta solo MPI. SpMV è parallelizzato con
   OpenMP e resta a 9.3 GFLOP/s con 2, 4 e 8 thread; MG invece usa uno smoother di
   Gauss-Seidel, in cui ogni punto aspetta il risultato del precedente, e i dati
   indicano che nella versione di riferimento gira su un solo thread per processo. Il rate di MG segue
   quindi il numero di processi: 8.96, 7.57, 5.07, 2.88, 1.22 GFLOP/s per 16, 8, 4, 2,
   1 processi. Il primo dimezzamento costa solo il 15%, plausibilmente perché con 16
   processi il nodo è già limitato dalla banda di memoria; poi ogni dimezzamento si avvicina a un
   dimezzamento del rate. Anche il setup non usa i thread (da 8 a 114 s).
3. **Lo stesso effetto NUMA, due conseguenze opposte.** Con 1 × 16 un solo processo
   occupa entrambi i socket. Per HPL costa poco (−3.3%): `DGEMM` riusa ogni dato
   molte volte dalla cache, quindi da quale memoria arrivi conta poco. Per HPCG, SpMV
   scende da 9.3 a 4.7 GFLOP/s, quasi la metà: il setup è eseguito da un solo thread,
   che alloca la matrice nella memoria del suo socket (*first touch*), e così si usano
   i canali di memoria di un solo socket su due. È la spiegazione coerente con il
   dimezzamento; la collocazione delle pagine non è stata misurata. La previsione
   iniziale, cioè che 1 × 16 fosse la ripartizione peggiore anche per HPL, era
   sbagliata proprio per questo motivo.
4. **Variabilità.** La dispersione fra run identici è dell'1% circa
   ({numref}`tab-es05-hpl-layout`), confrontabile con le differenze fra le ripartizioni
   migliori: da qui le 3 ripetizioni. Si vede anche un effetto del nodo: `wnode05` dà
   il valore più basso del suo gruppo in tutti e tre i run in cui compare (circa −2%).
5. **HPL, HPCG e picco su un nodo.** HPL raggiunge l'85% del picco alla frequenza
   misurata, HPCG il 2.8%. La differenza non indica un difetto della macchina ma due
   carichi opposti: HPL fa decine di operazioni per ogni dato letto, HPCG circa 0.13
   operazioni per byte trasferito (8.70 GFLOP/s su 67.5 GB/s di traffico stimato da
   HPCG stesso), quindi è la memoria, non l'unità di calcolo, a fissarne il limite.

## Checkpoint

- **Tutti i run validi**: 24 run HPL `PASSED` (residuo massimo $5.3 \times 10^{-3}$
  contro soglia 16) e 6 run HPCG `VALID`, tutti `COMPLETED 0:0`.
- **HPL su un nodo**: miglior ripartizione **2 × 8** (un processo per socket),
  $260.3 \pm 3.1$ GFLOP/s su 3 run; solo MPI −3.5%; griglia 1 × 16 −8.7%.
- **HPCG su un nodo**: miglior ripartizione **16 × 1** (8.70 GFLOP/s); con 1 × 16 il
  rate scende dell'85% perché il multigrid non usa i thread.
- **Picco**: frequenza misurata 2.40 GHz, $R_{\text{peak}}$ = 307 GFLOP/s per nodo;
  HPL al 84.8%, HPCG al 2.83%.
