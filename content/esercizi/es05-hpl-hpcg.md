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
   `hpcg.dat`. **Interpretazione**: per HPL, grafici di tempo, speedup ed efficienza
   contro core o nodi; per HPCG, grafici del rate validato e dello speedup e
   dell'efficienza ricavati da esso, con baseline il run completo su un nodo
   ($E_k = R_k/(k R_1)$ con $k$ nodi); confronto di entrambi con il picco, senza
   aspettarsi per HPCG una frazione simile. Dai run memory-scaled non si ricava uno
   speedup di strong scaling; 60 s bastano per i controlli di correttezza, mentre un
   run ufficiale di HPCG ne richiede almeno 1800.
4. **Picco teorico**: stimare $R_{\text{peak}} = N_{\text{core}}\, f\,
   (\text{flop per ciclo})$ dichiarando precisione, numero di core, frequenza,
   larghezza vettoriale e operazioni per ciclo.
5. **(Optional)** Confronto fra i tipi di nodo della partizione `lab4`, senza
   mescolare generazioni di processore nella stessa curva di scaling.
:::

:::{seealso} Teoria di riferimento
- **3. Performance e benchmarking** — {ref}`Il tetto teorico in doppia precisione <t-picco>`
- **3. Performance e benchmarking** — {ref}`HPL: parametri N, NB, P, Q e scelta di N <t-hpl>`
- **3. Performance e benchmarking** — {ref}`Strong scaling e memory scaling <t-hpl-scaling>`
- **3. Performance e benchmarking** — {ref}`HPCG: problema, hpcg.dat e tempo fisso <t-hpcg>`
- **2. Calcolo parallelo** — {ref}`Prestazioni e scalabilità: speedup ed efficienza <prestazioni-scalabilita>`
- **4. Gestione delle risorse** — {ref}`Disposizione, affinità e Slurm <disposizione-e-slurm>`
- **6. MPI** — {ref}`Programmazione ibrida MPI + OpenMP <ibrido-mpi-openmp>`
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

**La domanda su più nodi.** Se raddoppiamo le risorse, il lavoro va il doppio più
veloce? Nel caso ideale sì: l'**efficienza** (quanto rende ogni nodo rispetto a un
nodo da solo) resterebbe 1. Nella realtà i nodi devono scambiarsi dati attraverso la
rete, e quel tempo non diminuisce aggiungendo nodi. Abbiamo provato due modi di
crescere: a problema fisso (*strong scaling*: stesso lavoro, più nodi) e a problema
che cresce con i nodi (*memory-scaled* per HPL, *weak scaling* per HPCG: ogni nodo
ha sempre la stessa quantità di dati).

- **HPL**: a problema fisso ($N$ = 41280) il tempo scende da 180 s su un nodo a 68 s
  su 4 nodi, ma a 8 nodi **risale** a 82 s: ogni nodo ha troppo poco lavoro rispetto
  alla comunicazione. Facendo crescere la matrice con i nodi l'efficienza resta
  circa 0.85 fino a 4 nodi; a 8 nodi scende a 0.55 (0.27 a problema fisso).
- **HPCG**: con dati fissi per processo il rate cresce fino a **44.6 GFLOP/s su 8
  nodi** (efficienza per nodo 0.64). A problema fisso il massimo è a 2 nodi
  (16.9 GFLOP/s); oltre, il tempo passato nelle somme globali (`DDOT`, che
  sincronizzano tutti i processi) arriva al 77% del totale.
- **Picco su 8 nodi**: HPL al **47%**, HPCG all'**1.8%**. Già dentro un nodo HPCG
  guadagna solo il 17% passando da 8 a 16 processi, perché la banda di memoria del
  nodo è quasi satura.

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

:::{table} Macchina, software e parametri dei benchmark (job `61221`–`61344` su un nodo, `61392`–`61418` per lo scaling).
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
| Ripetizioni | HPL a $N$ = 41280: 3 run per ripartizione; HPCG: 1 run per ripartizione, più la baseline ripetuta; scaling: 1 run per punto |
| Frequenza misurata | 2.40 GHz con `perf stat` durante HPL (job `61344`) |
| Scaling HPL | 2 processi × 8 thread per nodo (il migliore su un nodo); strong a $N$ = 41280 da 1 core a 8 nodi; memory-scaled a $N$ = 41280, 58368, 82560, 116736 su 1, 2, 4, 8 nodi |
| Scaling HPCG | 16 processi × 1 thread per nodo (il migliore su un nodo), 60 s; weak con griglia locale 104³ da 1 a 128 processi; strong con griglia globale 256³ da 1 a 128 processi |
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
[`codes/exec5/es05.sh`](../../codes/exec5/README.md): parte dai file del corso e cambia
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
quando i processi diminuiscono. La griglia dei processi la sceglie HPCG: con $2^k$
processi divide l'esponente $k$ in tre parti il più possibile uguali, dando i fattori
in più prima a $x$ e poi a $y$ (128 = $2^7$ → 8 × 4 × 4). `es05.sh` cambia la riga 3
e aggiunge a `srun` la stessa griglia con le opzioni `--npx`, `--npy`, `--npz`; per
esempio, per 2 × 8:

```diff
-104 104 104
+208 208 208
...
-srun --cpu-bind=verbose --cpus-per-task="$SLURM_CPUS_PER_TASK" xhpcg
+srun --cpu-bind=verbose --cpus-per-task="$SLURM_CPUS_PER_TASK" xhpcg --npx=2 --npy=1 --npz=1
```

Queste opzioni in realtà non hanno effetto. Nel sorgente ufficiale di HPCG 3.1
(`src/init.cpp`), se la griglia locale non è data da riga di comando HPCG legge
`hpcg.dat` e prende la griglia dei processi dalla riga 5; il nostro file ha 4 righe,
quindi la griglia torna a 0 e HPCG la ricalcola da solo. I risultati non cambiano:
in tutti i 21 run la riga `Processor Dimensions` dell'output coincide con la griglia
passata, e il baseline del corso, senza opzioni, usa la stessa 4 × 2 × 2. Per imporre
una griglia diversa andrebbe scritta nella riga 5 di `hpcg.dat`.

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

### Configurazioni degli studi di scaling

**In breve.** Su più nodi si usa la ripartizione per nodo che ha vinto il confronto
su un nodo, e la si ripete uguale su ogni nodo: per HPL 2 processi × 8 thread, per
HPCG 16 processi × 1 thread. Cambiano solo il numero di nodi, la griglia dei
processi e, dove serve, la dimensione del problema.

Le cartelle sono generate da `es05.sh hpl-scaling` e `es05.sh hpcg-scaling` con lo
stesso `patch_script` di sopra, cambiando anche `--nodes`. Tutti i job usano
`--constraint=sandy_bridge`: la partizione ha solo 8 nodi di questo tipo, quindi
8 nodi è il massimo senza mescolare generazioni di CPU.

- **HPL strong** ($N$ = 41280 fisso). Fino a 8 core c'è un solo processo con 1, 2,
  4 o 8 thread; da 16 core in su ogni nodo ha 2 processi da 8 thread, con griglia
  $P \times Q$ = 1 × 2, 2 × 2, 2 × 4, 4 × 4 per 1, 2, 4, 8 nodi.
- **HPL memory-scaled**. Per tenere fissa la memoria per nodo, $N$ cresce come
  $\sqrt{\text{nodi}}$ ed è arrotondato al multiplo di $NB$ = 192 più vicino:
  $41280 = 215 \cdot 192$; $215\sqrt{2} = 304.1$, quindi $N = 304 \cdot 192 = 58368$;
  poi $430 \cdot 192 = 82560$ e $608 \cdot 192 = 116736$. La matrice per nodo è
  $8N^2/\text{nodi} = 12.7$ GiB in tutti e quattro i casi. Il punto a 1 nodo è il run
  strong a 16 core.
- **HPL a memoria piena** (`R01`). Un run su un nodo con $N$ = 82560 (50.8 GiB, circa
  l'83% dei 62500 MB del nodo), per il confronto finale con il picco.
- **HPCG weak**. Griglia locale 104³ per processo in tutti i run, quindi la griglia
  globale cresce con i processi (da 104³ a 832 × 416 × 416). Il punto a 16 processi
  è il run `10_16x1` del confronto su un nodo.
- **HPCG strong**. Griglia globale 256³ fissa: la griglia locale si dimezza a ogni
  raddoppio dei processi (da 256³ a 32 × 64 × 64). La griglia globale deve dividersi
  per ogni griglia dei processi usata, fino a 8 × 4 × 4, e ogni lato della griglia
  locale deve essere un multiplo di 8, perché il multigrid di HPCG la dimezza tre
  volte (`assert(nxf%2==0)` in `src/GenerateCoarseProblem.cpp`), e almeno 16, perché
  sotto HPCG lo alza da solo (`src/init.cpp`). Quindi il lato globale in $x$ deve
  essere multiplo di 64, quelli in $y$ e $z$ multipli di 32. La griglia del confronto
  su un nodo non va bene: a 32 processi (4 × 4 × 2) la griglia locale sarebbe
  104 × 52 × 104, e 52 non è multiplo di 8. Fra i cubi ammessi (192³, 256³, 320³, …)
  256³ è il più vicino al problema su un nodo (16.8 contro 18.0 milioni di punti) e,
  essendo una potenza di 2, ogni griglia locale resta una potenza di 2. Il run da
  1 processo dura comunque 18 minuti (102 s solo di setup).

La griglia dei processi è quella che HPCG sceglie da solo (le opzioni `--npx`,
`--npy`, `--npz` aggiunte da `es05.sh` non hanno effetto, vedi sopra): 1 × 1 × 1,
2 × 1 × 1, 2 × 2 × 1, 2 × 2 × 2, 4 × 2 × 2, 4 × 4 × 2, 4 × 4 × 4, 8 × 4 × 4 per 1, 2,
4, …, 128 processi, come riporta la riga `Processor Dimensions` di ogni output.

Le due serie a problema crescente, nel formato degli esempi della traccia (tempi
misurati invece che previsti):

:::{table} HPL memory-scaled su WILSON: righe `#SBATCH`, ordine della matrice e tempi misurati. Tutti i run usano $NB$ = 192 e la variante `WR11C2R4`; la riga `R01` è il run a memoria piena su un nodo.
:name: tab-es05-hpl-memory-config

| `--nodes` | `--ntasks-per-node` | `--cpus-per-task` | `--time` | $N$ | $P \times Q$ | Matrice per nodo | Tempo di calcolo HPL | Elapsed del job |
|---|---|---|---|---|---|---|---|---|
| 1 | 2 | 8 | 00:30:00 | 41280 | 1 × 2 | 12.7 GiB | 180 s | 00:04:24 |
| 2 | 2 | 8 | 01:00:00 | 58368 | 2 × 2 | 12.7 GiB | 292 s | 00:06:15 |
| 4 | 2 | 8 | 01:00:00 | 82560 | 2 × 4 | 12.7 GiB | 423 s | 00:08:26 |
| 8 | 2 | 8 | 01:00:00 | 116736 | 4 × 4 | 12.7 GiB | 927 s | 00:16:51 |
| 1 (`R01`) | 2 | 8 | 01:00:00 | 82560 | 1 × 2 | 50.8 GiB | 1398 s | 00:28:46 |
:::

:::{table} HPCG weak su WILSON: righe `#SBATCH`, griglie e durate. La griglia locale e la durata richiesta restano fisse; l'elapsed comprende setup e validazione.
:name: tab-es05-hpcg-weak-config

| `--nodes` | `--ntasks-per-node` | `--cpus-per-task` | `--time` | Griglia locale | Griglia globale | Durata in `hpcg.dat` | Elapsed del job |
|---|---|---|---|---|---|---|---|
| 1 | 1 | 1 | 00:30:00 | 104³ | 104 × 104 × 104 | 60 s | 00:01:53 |
| 1 | 2 | 1 | 00:30:00 | 104³ | 208 × 104 × 104 | 60 s | 00:01:52 |
| 1 | 4 | 1 | 00:30:00 | 104³ | 208 × 208 × 104 | 60 s | 00:02:02 |
| 1 | 8 | 1 | 00:30:00 | 104³ | 208 × 208 × 208 | 60 s | 00:02:08 |
| 1 | 16 | 1 | 01:00:00 | 104³ | 416 × 208 × 208 | 60 s | 00:02:59 |
| 2 | 16 | 1 | 00:30:00 | 104³ | 416 × 416 × 208 | 60 s | 00:03:10 |
| 4 | 16 | 1 | 00:30:00 | 104³ | 416 × 416 × 416 | 60 s | 00:03:37 |
| 8 | 16 | 1 | 00:30:00 | 104³ | 832 × 416 × 416 | 60 s | 00:04:32 |
:::

**Rispetto agli esempi della traccia.** La traccia propone HPL memory-scaled con
4 processi × 4 thread per nodo e circa 51 GiB di matrice per nodo ($N$ = 82560 su un
nodo, poi fino a 20 nodi), e HPCG weak con 16 processi × 1 thread per nodo e griglia
locale fissa, fino a 20 nodi con `--time=00:10:00`. Le nostre serie seguono lo stesso
schema, con quattro differenze:

- **2 × 8 invece di 4 × 4 per HPL**: è la ripartizione migliore su un nodo; 4 × 4 è
  l'1.4% più lenta (sezione 3).
- **12.7 GiB di matrice per nodo invece di 51 GiB**: a 51 GiB il run su un nodo
  (`R01`) calcola per 23 minuti contro 3 minuti a $N$ = 41280, e la serie a 8 nodi
  richiederebbe $N \approx 82560\sqrt{8} \approx 233\,000$. Per una stima: il lavoro
  per nodo crescerebbe di $\sqrt{8} \approx 2.8$ volte, quindi almeno 66 minuti di
  calcolo anche con efficienza 1 (stima, non misurata). A 51 GiB per nodo c'è quindi
  solo il punto a un nodo, `R01`, usato per il confronto con il picco (sezione 11).
- **Al massimo 8 nodi invece di 10 e 20**: la partizione ha solo 8 nodi Sandy
  Bridge, e con 10 o 20 nodi si mescolerebbero generazioni di CPU con picchi
  diversi, cosa che la consegna chiede di evitare.
- **HPCG weak anche dentro un nodo** (1, 2, 4 e 8 processi), per separare l'effetto
  della banda di memoria da quello della rete, e `--time` di 30 minuti invece di 10.
  Il job più lungo è durato 4 min 32 s, quindi 10 minuti sarebbero bastati.

### Comandi

Sul login node di WILSON, nella home:

```bash
bash es05.sh setup         # file del corso, sinfo, module spider, lscpu, baseline
bash es05.sh node          # ripartizioni MPI x thread su un nodo
bash es05.sh repeat        # run 2 e 3 delle ripartizioni HPL, run con perf stat
bash es05.sh hpl-scaling   # HPL strong, memory-scaled e N = 82560 su un nodo
bash es05.sh hpcg-scaling  # HPCG weak e strong
bash es05.sh collect       # input, output, sacct e tabella riassuntiva in un log
```

Sul Mac, il log di `collect` viene letto da
[`codes/exec5/analyze_es05.py`](../../codes/exec5/README.md), che produce le tabelle e le
figure di questa pagina:

```bash
.venv/bin/python codes/exec5/analyze_es05.py results/es05/collect_20261116_091615.txt
```

Il log del 16 novembre contiene tutti i run, su un nodo e di scaling; quello del
9 novembre (`collect_20261109_121824.txt`) solo quelli su un nodo e dà le stesse
tabelle e figure per quella parte.

## Procedura di validazione

- **HPL**: ogni run calcola il residuo scalato
  $\lVert A\boldsymbol{x}-\boldsymbol{b}\rVert_\infty / \big(\varepsilon\,(\lVert A\rVert_\infty \lVert\boldsymbol{x}\rVert_\infty + \lVert\boldsymbol{b}\rVert_\infty)\,N\big)$
  con $\varepsilon = 1.11 \times 10^{-16}$, e il test passa se è minore di 16. Tutti i
  36 run (24 su un nodo, 12 di scaling) danno `PASSED`, con residui fra
  $2.1 \times 10^{-3}$ e $5.3 \times 10^{-3}$, oltre tre ordini di grandezza sotto la
  soglia, anche a $N$ = 116736 su 8 nodi ($3.4 \times 10^{-3}$). Le ripetizioni della stessa
  ripartizione danno lo stesso residuo a tutte le cifre stampate: la matrice casuale
  è generata in modo deterministico, quindi le ripetizioni risolvono lo stesso
  problema.
- **HPCG**: il risultato è `VALID` solo se superano i test di convergenza spettrale,
  di simmetria, del numero di iterazioni e di riproducibilità; tutti i 21 run (6 su
  un nodo, 15 di scaling) sono `VALID`. Estratto dal run 16 × 1 (job `61287`):

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
- **Slurm**: tutti i 57 job risultano `COMPLETED` con exit code `0:0` in `sacct`;
  per i job su più nodi `sacct` riporta tutti i nodi richiesti (per esempio
  `wnode[01-08]`, 256 CPU logiche allocate, `ReqMem` 500000M per 8 nodi).
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
(tutti i run su un nodo, con le ripetizioni) e
{download}`collect_20261116_091615.txt <../../../results/es05/collect_20261116_091615.txt>`
(tutti i run, compresi quelli di scaling).

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

**Perché non una matrice più grande.** Il guadagno si riduce a ogni raddoppio di $N$:
+16.7% da 12288 a 24576, poi +8.2% da 24576 a 41280, quando si è già all'84% del
picco. Il costo invece cresce come $N^3$. Il run `R01` lo conferma: con 2 × 8 e
$N$ = 82560 (50.8 GiB, quasi tutta la memoria del nodo) HPL dà **268.3 GFLOP/s**,
solo il 3.1% in più della media a $N$ = 41280 (260.3), ma impiega 1398 s invece di
180 e occupa il nodo per 29 minuti. Con 21 run a $N$ = 41280 per il confronto delle
ripartizioni, usare $N$ = 82560 avrebbe richiesto circa 10 ore di nodo invece di
1.4, per spostare tutti i risultati di pochi punti percentuali. `R01` resta il
risultato a memoria piena usato nel confronto finale con il picco
({numref}`tab-es05-final`). Un limite: la classifica delle ripartizioni non è stata
ricontrollata a $N$ = 82560.

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

```{figure} figures/es05-hpl-layout.png
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

```{figure} figures/es05-hpcg-layout.png
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

### 7. HPL: strong scaling a $N$ = 41280

**Idea.** Stessa matrice, sempre più core. Nel caso ideale il tempo si dimezza a
ogni raddoppio, cioè lo speedup $S = T_1/T$ è uguale al numero di core e
l'efficienza $E = S/\text{core}$ resta 1. In realtà la parte di comunicazione e di
coordinamento non si divide fra i core, e pesa sempre di più man mano che il lavoro
di ciascuno si riduce.

:::{table} HPL strong scaling a $N$ = 41280. Speedup ed efficienza rispetto al run da 1 core; efficienza per nodo rispetto al run da 16 core; frazione del picco a 2.40 GHz per i core usati.
:name: tab-es05-hpl-strong

| Core | Nodi | Processi × thread | $P \times Q$ | Time (s) | GFLOP/s | Speedup | Efficienza | Efficienza per nodo | Frazione del picco |
|---|---|---|---|---|---|---|---|---|---|
| 1 | 1 | 1 × 1 | 1 × 1 | 2259.8 | 20.8 | 1.00 | 1.00 | — | 108.1% |
| 2 | 1 | 1 × 2 | 1 × 1 | 1148.1 | 40.8 | 1.97 | 0.98 | — | 106.4% |
| 4 | 1 | 1 × 4 | 1 × 1 | 648.5 | 72.3 | 3.48 | 0.87 | — | 94.2% |
| 8 | 1 | 1 × 8 | 1 × 1 | 352.9 | 132.9 | 6.40 | 0.80 | — | 86.5% |
| 16 | 1 | 2 × 8 | 1 × 2 | 179.9 | 260.7 | 12.56 | 0.79 | 1.00 | 84.9% |
| 32 | 2 | 4 × 8 | 2 × 2 | 112.1 | 418.2 | 20.15 | 0.63 | 0.80 | 68.1% |
| 64 | 4 | 8 × 8 | 2 × 4 | 68.2 | **687.9** | 33.15 | 0.52 | 0.66 | 56.0% |
| 128 | 8 | 16 × 8 | 4 × 4 | 82.2 | 570.2 | 27.48 | 0.21 | 0.27 | 23.2% |
:::

```{figure} figures/es05-hpl-scaling.png
:name: fig-es05-hpl-scaling
:width: 100%

HPL, **strong scaling** (matrice fissa, $N$ = 41280; run `S001`–`S128`) su nodi
Sandy Bridge, da 1 core a 8 nodi. In alto: tempo di calcolo e speedup rispetto a
1 core (assi logaritmici; tratteggio: ideale). In basso a sinistra: efficienza
rispetto a 1 core, con un riferimento gonfiato dal turbo. In basso a destra:
efficienza rispetto a un nodo; per confronto c'è anche la curva dello studio
**memory-scaled** della sezione 8 (run `M02`–`M08`), dove invece $N$ cresce con i
nodi.
```

Dentro un nodo lo speedup è quasi ideale fino a 2 core e arriva a 12.6 con 16 core.
Il run da 1 core, però, va al **108%** del picco calcolato a 2.40 GHz: con un solo
core attivo la CPU sale più in alto in turbo (almeno 2.6 GHz, perché
$20.75 / 8 = 2.59$ GHz anche con un'efficienza del 100%; il massimo dichiarato è
2.8 GHz). Il riferimento a 1 core è quindi "gonfiato" dal turbo, e l'efficienza 0.79
a 16 core sottostima quella a frequenza costante. Per questo, da un nodo in su,
conviene confrontare con il run da 16 core (**efficienza per nodo**), in cui tutti i
core sono attivi come negli altri run.

Fra i nodi l'efficienza scende a 0.80 e 0.66, e a 8 nodi crolla a 0.27: il tempo
**risale** da 68 a 82 s. A 8 nodi ogni processo ha solo 1/16 della matrice
($8N^2/16 = 0.8$ GiB), quindi il calcolo per processo si riduce, mentre a ogni passo
il pannello va comunque inviato lungo le righe della griglia e lo scambio delle righe
di pivot lungo le colonne. Il risultato migliore in valore assoluto è a 4 nodi,
**688 GFLOP/s**.

### 8. HPL: memory-scaled, $N \propto \sqrt{p}$

**Idea.** A differenza dello strong scaling della sezione 7, qui la matrice **non**
resta fissa. Se il problema cresce con i nodi, ogni nodo ha sempre la stessa quantità di
dati (12.7 GiB) e il calcolo resta grande rispetto alla comunicazione. L'ideale è
che ogni nodo renda come da solo: $R_k = k \cdot R_1$, cioè efficienza
$E = R_k / (k R_1) = 1$. Il lavoro per nodo però cresce come $\sqrt{k}$
({ref}`t-hpl-scaling`), quindi anche nel caso ideale il tempo cresce.

:::{table} HPL memory-scaled, 2 processi × 8 thread per nodo ($p = 2k$). $N$ cresce come $\sqrt{k}$: $N/\sqrt{k}$ resta 41280 a meno dell'arrotondamento a multipli di 192. Memoria per processo $8N^2/p$, lavoro per processo $\tfrac23 N^3/p$ rispetto a un nodo; tempo ideale $T_1\sqrt{k}$, cioè quello a efficienza 1.
:name: tab-es05-hpl-memory

| Nodi $k$ | $N$ | $N/\sqrt{k}$ | $P \times Q$ | Memoria per processo | Lavoro per processo | Time (s) | Tempo ideale (s) | GFLOP/s | GFLOP/s per nodo | Efficienza | Frazione del picco |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 41280 | 41280 | 1 × 2 | 6.35 GiB | 1.00 | 179.9 | — | 260.7 | 260.7 | 1.00 | 84.9% |
| 2 | 58368 | 41272 | 2 × 2 | 6.35 GiB | 1.41 | 292.4 | 254.4 | 453.3 | 226.7 | 0.87 | 73.8% |
| 4 | 82560 | 41280 | 2 × 4 | 6.35 GiB | 2.00 | 422.9 | 359.7 | 887.2 | 221.8 | 0.85 | 72.2% |
| 8 | 116736 | 41272 | 4 × 4 | 6.35 GiB | 2.83 | 927.1 | 508.7 | **1144.0** | 143.0 | 0.55 | 46.6% |
:::

```{figure} figures/es05-hpl-memory.png
:name: fig-es05-hpl-memory
:width: 100%

HPL, studio **memory-scaled** (non strong scaling): $N$ cresce come $\sqrt{p}$ e la
memoria per processo resta costante; run `S016` (1 nodo, lo stesso punto di
partenza dello strong scaling), `M02`, `M04`, `M08`. Lo strong scaling, con $N$
fisso, è nella {numref}`fig-es05-hpl-scaling`. $p$ è il numero di processi MPI
($p = P \times Q$, 2 per nodo da 8 thread ciascuno). Linee: previsioni; punti: i
quattro run. **(a, d)** Come è impostato l'esperimento: $N$ sulla curva
$N_1\sqrt{p/p_1}$. **(b, e)** Il risultato: GFLOP/s totali, con l'ideale
$R_1\,p/p_1$ (ogni processo mantiene la sua velocità, efficienza 1) e il picco
teorico; accanto a ogni punto l'efficienza $E$. **(c, f)** Perché i run durano di
più: rispetto al run su un nodo, la memoria per processo è costante e il lavoro per
processo cresce come $\sqrt{p}$, che è il tempo a efficienza 1; il tempo misurato
sta sopra di ×1.15, ×1.18 e ×1.82 = $1/E$. In alto assi lineari, in basso log-log,
dove ogni legge $p^a$ è una retta di pendenza $a$.
```

**Segue l'andamento previsto?** $N$ e memoria per processo sì, per costruzione:
$N/\sqrt{k}$ si scosta dal valore di un nodo al massimo dello 0.02%, solo per
l'arrotondamento a multipli di 192. Il tempo dovrebbe crescere come $\sqrt{p}$: lo
segue con un fattore quasi costante fino a 4 nodi (×1.15 e ×1.18 sopra la retta,
cioè efficienza 0.87 e 0.85), mentre a 8 nodi se ne stacca (×1.82, efficienza
0.55). Nei pannelli log-log (e, f) la differenza si vede subito: fino a 8 processi i
punti corrono quasi paralleli alle rette ideali, l'ultimo se ne stacca. I GFLOP/s
(b, e) sono la grandezza che HPL misura e il risultato dello scaling; il tempo
(c, f) mostra l'avvertimento della consegna sulla durata dei casi grandi.

Il grafico mostra anche il punto della consegna. Tenere costante la **memoria** per
processo non tiene costante il **lavoro**: a 8 nodi ogni processo ha gli stessi
6.35 GiB di matrice ma deve fare 2.83 volte più operazioni. Una stima basata solo
sulla memoria ("stessi dati per processo, stesso tempo") darebbe 180 s anche a 8
nodi; il tempo ideale è già 509 s, e quello misurato è 927 s. Per questo non è
*weak scaling* classico, che terrebbe costante il lavoro con $N \propto p^{1/3}$
(a 8 nodi $N = 82560$, con 3.2 GiB per processo).

Come previsto, tenere grande il problema aiuta: a 2 e 4 nodi l'efficienza è 0.87 e
0.85, contro 0.80 e 0.66 a $N$ fisso. Il primo passo da 1 a 2 nodi costa il 13%,
il secondo quasi nulla: il costo si paga soprattutto quando i dati iniziano a
passare per la rete. A 8 nodi invece l'efficienza scende a **0.55** e il run dura
927 s invece dei 509 previsti a efficienza costante.

Il calo a 8 nodi compare in tutte e due le serie, quindi non dipende solo dalla
dimensione del problema: a parità di memoria per nodo, il passaggio da 4 a 8 nodi
costa da solo il 35% dell'efficienza. Rispetto ai run a 4 nodi cambiano due cose,
la griglia (da 2 × 4 a 4 × 4, cioè più processi su ogni colonna per lo scambio
delle righe di pivot) e i nodi coinvolti (tutti gli 8, `wnode[01-08]`). Con un solo
run per punto non si possono separare le due cause né escludere un disturbo
occasionale sulla rete: servirebbero una ripetizione di `M08` e `S128` e un run a
8 nodi con griglia 2 × 8.

### 9. HPCG: weak scaling

**Idea.** Ogni processo ha sempre la stessa griglia locale (104³), quindi il
problema totale cresce con i processi. Se ognuno lavorasse come da solo, il rate
crescerebbe in proporzione: $R_p = p \cdot R_1$ ed efficienza $E = R_p/(p R_1) = 1$.
HPCG però è limitato dalla memoria: finché i processi condividono la banda di un
nodo, aggiungerne non può far crescere il rate oltre quanto la memoria riesce a
fornire.

:::{table} HPCG weak scaling, griglia locale 104³, 60 s richiesti. Efficienza rispetto a 1 processo e, da 16 processi in su, rispetto a un nodo pieno; banda stimata da HPCG e quota del tempo in `DDOT`.
:name: tab-es05-hpcg-weak

| Processi | Nodi | Griglia globale | GFLOP/s | Efficienza | Efficienza per nodo | Banda (GB/s) | `DDOT` (% del tempo) |
|---|---|---|---|---|---|---|---|
| 1 | 1 | 104 × 104 × 104 | 1.21 | 1.00 | — | 9.6 | 1% |
| 2 | 1 | 208 × 104 × 104 | 2.47 | 1.02 | — | 19.5 | 1% |
| 4 | 1 | 208 × 208 × 104 | 4.57 | 0.94 | — | 36.0 | 2% |
| 8 | 1 | 208 × 208 × 208 | 7.46 | 0.77 | — | 58.7 | 1% |
| 16 | 1 | 416 × 208 × 208 | 8.70 | 0.45 | 1.00 | 67.5 | 2% |
| 32 | 2 | 416 × 416 × 208 | 16.53 | 0.43 | 0.95 | 128.1 | 3% |
| 64 | 4 | 416 × 416 × 416 | 28.27 | 0.36 | 0.81 | 218.2 | 14% |
| 128 | 8 | 832 × 416 × 416 | **44.63** | 0.29 | 0.64 | 343.3 | 27% |
:::

```{figure} figures/es05-hpcg-weak.png
:name: fig-es05-hpcg-weak
:width: 100%

HPCG weak scaling (griglia locale 104³), assi logaritmici: rate validato contro
l'ideale $p \cdot R_1$ (tratteggio) e contro l'ideale da un nodo pieno
$k \cdot R_{16}$ con $k$ nodi (puntini). Dentro il nodo il rate si appiattisce fra 8
e 16 processi; fra i nodi segue quasi l'ideale da un nodo fino a 2 nodi, poi se ne
allontana.
```

```{figure} figures/es05-hpcg-scaling.png
:name: fig-es05-hpcg-scaling
:width: 100%

HPCG su nodi Sandy Bridge, 16 processi da 1 thread per nodo, weak scaling (griglia
locale fissa) e strong scaling (griglia globale fissa). A sinistra: efficienza
$R_p / (p R_1)$ rispetto al run da 1 processo. A destra: efficienza per nodo
$R_k / (k R_{16})$ rispetto al run da 16 processi, lo stesso riferimento per i due
studi: a 16 processi weak e strong risolvono quasi lo stesso problema (18.0 e 16.8
milioni di punti, 8.70 e 8.64 GFLOP/s).
```

Il comportamento ha due fasi ({numref}`fig-es05-hpcg-weak`). **Dentro il nodo** l'efficienza resta vicina a 1 fino
a 4 processi, poi scende: con 8 processi la banda stimata da HPCG è già 58.7 GB/s,
con 16 solo 67.5 GB/s (+15%), e il rate cresce di conseguenza solo da 7.46 a 8.70
(+17%). Raddoppiare i core non serve se la memoria è già quasi satura. **Fra i
nodi** invece ogni nodo porta la sua banda di memoria: l'efficienza per nodo è 0.95 a
2 nodi, poi 0.81 e 0.64, e la banda per nodo scende in proporzione (64.0, 54.6 e
42.9 GB/s contro 67.5 su un nodo). Il calo segue la quota di tempo in `DDOT`, che
sale dal 2-3% al 14% e al 27% (sezione 10).

### 10. HPCG: strong scaling e il peso di `DDOT`

**Idea.** Stessa griglia globale (256³) divisa fra sempre più processi. HPCG riceve
solo la griglia locale: `es05.sh` gli passa 256 diviso per la griglia dei processi
(colonna "Griglia locale"), e l'output di ogni run conferma la griglia globale 256³. A ogni
iterazione del gradiente coniugato servono prodotti scalari globali (`DDOT`): ogni
processo calcola la sua parte, poi una `MPI_Allreduce` somma i contributi di
tutti. È un punto di sincronizzazione: nessun processo può proseguire finché tutti
non sono arrivati. Più piccola è la parte di ciascuno, più il tempo di queste
somme pesa rispetto al calcolo.

**Perché 256³.** Nessun documento parla di 256³: è una scelta nostra. La regola viene
da HPCG: ogni lato della griglia locale deve essere un multiplo di 8 e almeno 16. Nel
sorgente di HPCG 3.1 il multigrid ha 4 livelli
([`src/main.cpp`](https://github.com/hpcg-benchmark/hpcg/blob/HPCG-release-3-1-0/src/main.cpp#L139))
e passa da un livello al successivo dimezzando ogni lato, che deve essere pari
([`src/GenerateCoarseProblem.cpp`](https://github.com/hpcg-benchmark/hpcg/blob/HPCG-release-3-1-0/src/GenerateCoarseProblem.cpp#L50-L51)):
tre dimezzamenti richiedono un lato divisibile per $2^3 = 8$. Un lato sotto 16 viene
alzato da HPCG stesso
([`src/init.cpp`](https://github.com/hpcg-benchmark/hpcg/blob/HPCG-release-3-1-0/src/init.cpp#L103-L112)),
e il problema non sarebbe più quello voluto. 256 rispetta la regola con ogni griglia
dei processi fino a 8 × 4 × 4: la griglia locale più piccola è 32 × 64 × 64. Il
confronto con le altre griglie possibili è in "Configurazioni degli studi di scaling".

:::{table} HPCG strong scaling, griglia globale 256³, 60 s richiesti. Efficienza rispetto a 1 processo e, da 16 processi in su, rispetto a un nodo pieno; rate grezzo del multigrid; tempo in `DDOT` e tempo di `MPI_Allreduce` minimo e massimo fra i processi.
:name: tab-es05-hpcg-strong

| Processi | Nodi | Griglia locale | GFLOP/s | Efficienza | Efficienza per nodo | MG (GFLOP/s) | `DDOT` | `MPI_Allreduce` min–max (s) |
|---|---|---|---|---|---|---|---|---|
| 1 | 1 | 256 × 256 × 256 | 1.05 | 1.00 | — | 1.05 | 3.3 s (1%) | — |
| 2 | 1 | 128 × 256 × 256 | 2.17 | 1.04 | — | 2.18 | 1.7 s (1%) | 0.1–0.5 |
| 4 | 1 | 128 × 128 × 256 | 4.00 | 0.96 | — | 4.04 | 1.3 s (2%) | 0.4–1.2 |
| 8 | 1 | 128 × 128 × 128 | 6.78 | 0.81 | — | 6.92 | 1.8 s (2%) | 0.6–1.3 |
| 16 | 1 | 64 × 128 × 128 | 8.64 | 0.52 | 1.00 | 8.88 | 1.2 s (2%) | 0.3–0.8 |
| 32 | 2 | 64 × 64 × 128 | **16.90** | 0.51 | 0.98 | 17.66 | 2.1 s (3%) | 0.6–1.9 |
| 64 | 4 | 64 × 64 × 64 | 15.33 | 0.23 | 0.44 | 30.07 | 30.5 s (50%) | 9.3–30.4 |
| 128 | 8 | 32 × 64 × 64 | 12.10 | 0.09 | 0.18 | 50.32 | 59.0 s (77%) | 36.2–59.2 |
:::

```{figure} figures/es05-hpcg-strong.png
:name: fig-es05-hpcg-strong
:width: 100%

HPCG strong scaling (griglia globale 256³), assi logaritmici: rate validato e rate
del solo multigrid contro l'ideale $p \cdot R_1$. Il multigrid continua a crescere
fino a 8 nodi, il rate complessivo ha il massimo a 2 nodi e poi scende.
```

```{figure} figures/es05-hpcg-tempi.png
:name: fig-es05-hpcg-tempi
:width: 100%

HPCG strong scaling (griglia globale 256³) da 1 a 8 nodi: come si divide il tempo
del benchmark fra multigrid (MG), prodotto matrice-vettore (SpMV), prodotti scalari
con somma globale (DDOT) e aggiornamenti di vettori (WAXPBY).
```

Fino a 2 nodi lo strong scaling di HPCG è quasi perfetto fra i nodi (efficienza per
nodo 0.98) e dà il rate più alto della serie, 16.9 GFLOP/s. Poi il rate **scende**:
15.3 a 4 nodi e 12.1 a 8. I kernel di calcolo continuano a scalare (il multigrid
passa da 17.7 a 30.1 e 50.3 GFLOP/s, {numref}`fig-es05-hpcg-strong`), ma `DDOT`
passa da 2 s a 30 e 59 s, cioè dal 3% al 50% e al 77% del tempo
({numref}`fig-es05-hpcg-tempi`). I dati sommati in ogni `MPI_Allreduce` sono pochi
numeri, quindi il problema non è la quantità di dati. Anche il processo che aspetta
meno passa 9.3 s (4 nodi) e 36.2 s (8 nodi) nella riduzione, contro meno di 1 s su
un nodo: ogni somma globale fra nodi costa molto più che dentro un nodo, e i
processi più lenti fanno aspettare tutti gli altri. Il log non permette di separare
la latenza della rete dall'attesa dei processi in ritardo.

L'efficienza leggermente sopra 1 con 2 processi (1.04) viene da un singolo run e dal
confronto con un run da 1 processo su `wnode05`, il nodo che già nel confronto HPL
era circa il 2% più lento: rientra nella variabilità fra nodi e non è stata
indagata oltre.

### 11. HPL, HPCG e picco teorico su più nodi

**Idea.** Il punto 4 della consegna chiede quale benchmark si avvicina di più al
picco. Su un nodo la risposta era HPL (85%) contro HPCG (2.8%). Su più nodi si
aggiunge la rete, che pesa in modo diverso sui due benchmark.

:::{table} Migliori risultati su 1, 2, 4 e 8 nodi rispetto al picco teorico, 307.1 GFLOP/s per nodo a 2.40 GHz.
:name: tab-es05-final

| Nodi | Picco (GFLOP/s) | HPL migliore (run) | HPL / picco | HPCG migliore (run) | HPCG / picco | HPL / HPCG |
|---|---|---|---|---|---|---|
| 1 | 307.1 | 268.3 (`R01`, $N$ = 82560) | **87.4%** | 8.70 (16 × 1) | **2.83%** | 31× |
| 2 | 614.2 | 453.3 (`M02`) | 73.8% | 16.90 (strong) | 2.75% | 27× |
| 4 | 1228.4 | 887.2 (`M04`) | 72.2% | 28.27 (weak) | 2.30% | 31× |
| 8 | 2456.8 | 1144.0 (`M08`) | **46.6%** | 44.63 (weak) | **1.82%** | 26× |
:::

HPL resta sempre circa 30 volte più vicino al picco di HPCG. Il miglior risultato
su un nodo è `R01` a memoria piena, all'**87.4%** del picco. Su 8 nodi HPL scende al
47% e HPCG all'1.8%: entrambi perdono, ma per motivi diversi. HPL perde nel passaggio
a 8 nodi (sezione 8), mentre HPCG perde già dentro il nodo, per la banda di memoria,
e poi fra i nodi, per le somme globali.

### 12. Speedup, efficienza e confronto fra weak e strong

**Idea.** Gli studi di scaling rispondono a due domande diverse. Con il problema
fisso (strong) ci si chiede quanto più in fretta si risolve lo stesso problema; con
il problema che cresce insieme ai nodi (weak per HPCG, memory-scaled per HPL) quanto
più grande può diventare il problema mantenendo il ritmo di ogni nodo. L'ideale è lo
stesso: con $k$ nodi il rate diventa $k$ volte quello di un nodo. Lo si misura con lo
**speedup** $S_k = R_k / R_1$ e con l'**efficienza** $E_k = S_k / k$, dove $R_1$ è il
rate su un nodo pieno; l'ideale è $S_k = k$ ed $E_k = 1$. Nello strong $S_k$ è lo
speedup classico $T_1 / T_k$; negli studi a problema crescente è lo *scaled speedup*,
il rate rispetto a un nodo con un problema più grande. Come avverte la traccia, dai
run memory-scaled non si ricava lo speedup di strong scaling: il rapporto dei tempi
$T_1/T_k$ confronterebbe problemi diversi, e anzi il tempo cresce con i nodi
(sezione 8). Per questo negli studi a problema crescente si usa il rapporto dei
rate, che per HPCG weak è proprio quello indicato dalla traccia: rate validato,
baseline il run completo su un nodo, efficienza $R_k/(k R_1)$.

Il riferimento è un nodo pieno, non un processo o un core: il run HPL su 1 core è
gonfiato dal turbo (sezione 7), e i run HPCG da 1 processo di weak e strong
riguardano problemi diversi, 104³ contro 256³, cioè 1.12 contro 16.8 milioni di punti
(sezione 9). Su un nodo pieno invece i due studi partono dallo stesso punto: per HPL
è lo stesso run (`S016`), per HPCG due run quasi uguali. Con 16 processi il weak ha
griglia globale 416 × 208 × 208 (18.0 milioni di punti) e lo strong 256³ (16.8
milioni); ogni processo ha una griglia locale di 104³ (1.12 milioni di punti) contro
64 × 128 × 128 (1.05 milioni), con una superficie da scambiare con i vicini di
$6 \cdot 104^2 = 64.9$ mila punti contro $2\,(64 \cdot 128 + 64 \cdot 128 + 128 \cdot 128) = 65.5$
mila. Calcolo e comunicazione per processo sono quindi quasi gli stessi, e infatti il
rate differisce dello 0.7% (8.70 e 8.64 GFLOP/s). Da lì le due serie si separano per
costruzione: il weak tiene fissa la griglia locale, lo strong la griglia globale.

:::{table} Speedup $S_k$ ed efficienza $E_k$ (tra parentesi) rispetto a un nodo pieno. HPL: 2 processi × 8 thread per nodo; HPCG: 16 processi × 1 thread per nodo.
:name: tab-es05-confronto

| Nodi | HPL strong ($N$ = 41280) | HPL memory-scaled ($N \propto \sqrt{k}$) | HPCG weak (104³ per processo) | HPCG strong (256³) |
|---|---|---|---|---|
| 1 | 1.00 (1.00) | 1.00 (1.00) | 1.00 (1.00) | 1.00 (1.00) |
| 2 | 1.60 (0.80) | 1.74 (0.87) | 1.90 (0.95) | 1.96 (0.98) |
| 4 | **2.64** (0.66) | 3.40 (0.85) | 3.25 (0.81) | 1.77 (0.44) |
| 8 | 2.19 (0.27) | 4.39 (0.55) | **5.13** (0.64) | 1.40 (0.18) |
:::

```{figure} figures/es05-scaling-confronto.png
:name: fig-es05-scaling-confronto
:width: 100%

Speedup (in alto, assi logaritmici, tratteggio: ideale $S = k$) ed efficienza (in
basso) rispetto a un nodo pieno per i quattro studi di scaling. Arancione: problema
che cresce con i nodi (HPL memory-scaled, HPCG weak); blu: problema fisso (strong).
Linea continua e cerchi: HPL; tratteggio e quadrati: HPCG.
```

**Problema che cresce contro problema fisso.** In entrambi i benchmark lo studio a
problema crescente tiene meglio: a 8 nodi l'efficienza è 0.55 contro 0.27 per HPL e
0.64 contro 0.18 per HPCG. Con il problema fisso il lavoro di ogni nodo scende come
$1/k$, mentre la comunicazione di ogni passo scende meno: per HPL l'invio del
pannello e lo scambio delle righe di pivot (sezione 7), per HPCG le somme globali di
`DDOT`, che a ogni iterazione sono le stesse qualunque sia la taglia del problema
(sezione 10).

**Lo speedup strong ha un massimo.** HPL strong arriva a 2.64 con 4 nodi e scende a
2.19 con 8 (il tempo risale da 68 a 82 s); HPCG strong arriva a 1.96 con 2 nodi e
scende a 1.40 con 8. Oltre quel punto aggiungere nodi rallenta il calcolo: per questi
problemi conviene fermarsi a 4 nodi con HPL e a 2 con HPCG. Negli studi a problema
crescente lo speedup continua a salire (4.39 e 5.13 con 8 nodi), anche se più
lentamente dell'ideale. In HPCG weak e strong si comportano allo stesso modo fino a
2 nodi (0.95 e 0.98); da 4 nodi lo strong crolla (0.44), quando la griglia locale
scende a 64³, circa un quarto di quella del weak (104³).

**HPL contro HPCG.** Ogni curva è relativa al proprio nodo, quindi la figura
confronta la qualità dello scaling, non le prestazioni: in valore assoluto HPL fa
circa 30 volte i GFLOP/s di HPCG (sezione 11). I due problemi fissi hanno una taglia
simile, 12–14 GB, circa un quinto della memoria di un nodo (la matrice di HPL è
12.7 GiB, HPCG riporta 12.0 GB per 256³). Con il problema fisso HPCG crolla prima di
HPL perché fra una somma globale e l'altra fa poco calcolo, mentre HPL fra una
comunicazione e l'altra esegue molte operazioni di `DGEMM`. Con il problema che
cresce l'ordine si inverte (0.64 contro 0.55 a 8 nodi), ma con un solo run per punto
la differenza va presa come indicativa.

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
6. **Strong scaling: conviene fermarsi prima.** Per HPL a $N$ = 41280 il tempo
   minimo è a 4 nodi (68 s), per HPCG a 256³ il rate massimo è a 2 nodi: oltre, i
   nodi in più fanno andare **più piano**. In entrambi i casi la causa è che la parte
   di ciascun processo diventa piccola e il costo di comunicare e sincronizzarsi non
   si riduce. Un problema di questa dimensione non giustifica 8 nodi.
7. **Crescere con il problema funziona meglio, ma non all'infinito.** Tenendo
   costante la memoria per nodo, HPL resta a 0.85 di efficienza fino a 4 nodi e
   HPCG weak a 0.81: è il modo in cui un cluster viene usato davvero, cioè per
   problemi più grandi, non per lo stesso problema più in fretta. A 8 nodi però
   HPL perde molto più che fra 2 e 4 nodi (memory-scaled da 0.85 a 0.55); con un run
   per punto la causa resta da verificare (sezione 8).
8. **HPCG: due limiti diversi.** Dentro un nodo il limite è la banda di memoria (da 8
   a 16 processi la banda cresce solo del 15%); fra i nodi sono le somme globali di
   `DDOT`, che sincronizzano tutti i processi a ogni iterazione e arrivano al 77% del
   tempo nello strong scaling a 8 nodi. Per HPL, che comunica soprattutto blocchi
   grandi e calcola molto per ogni dato ricevuto, la rete pesa meno: a 4 nodi
   l'efficienza memory-scaled è 0.85.
9. **Riferimento a 1 core e turbo.** Il run HPL da 1 core supera il picco a
   2.40 GHz (108%) perché con pochi core attivi la frequenza sale. Le efficienze
   dentro un nodo misurate rispetto a 1 core includono quindi anche la perdita di
   frequenza, non solo quella di parallelismo; la frequenza è stata misurata solo a
   16 core, quindi i due effetti non si possono separare.

## Checkpoint

- **Tutti i run validi**: 36 run HPL `PASSED` (residuo massimo $5.3 \times 10^{-3}$
  contro soglia 16) e 21 run HPCG `VALID`, tutti `COMPLETED 0:0`.
- **HPL su un nodo**: miglior ripartizione **2 × 8** (un processo per socket),
  $260.3 \pm 3.1$ GFLOP/s su 3 run; solo MPI −3.5%; griglia 1 × 16 −8.7%.
- **HPCG su un nodo**: miglior ripartizione **16 × 1** (8.70 GFLOP/s); con 1 × 16 il
  rate scende dell'85% perché il multigrid non usa i thread.
- **Picco**: frequenza misurata 2.40 GHz, $R_{\text{peak}}$ = 307 GFLOP/s per nodo;
  HPL al 84.8%, HPCG al 2.83%; a memoria piena ($N$ = 82560) HPL arriva all'87.4%.
- **HPL strong** ($N$ = 41280): efficienza per nodo 0.80, 0.66, 0.27 a 2, 4, 8 nodi;
  massimo assoluto a 4 nodi (688 GFLOP/s, 68 s).
- **HPL memory-scaled**: efficienza 0.87, 0.85, 0.55 a 2, 4, 8 nodi; 1144 GFLOP/s a
  8 nodi ($N$ = 116736), il 46.6% del picco.
- **HPCG weak**: 44.6 GFLOP/s a 128 processi; efficienza per nodo 0.95, 0.81, 0.64.
- **HPCG strong** (256³): massimo a 2 nodi (16.9 GFLOP/s); a 8 nodi `DDOT` è il 77%
  del tempo e il rate scende a 12.1.
- **Limite**: un run per punto di scaling; il calo a 8 nodi non è stato ripetuto.
