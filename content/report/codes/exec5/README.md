# codes/exec5 — Benchmarking e scaling con HPL e HPCG

Esercitazione 5 della relazione: HPL e HPCG su WILSON, confronto delle opzioni di
parallelizzazione su un nodo, scaling, confronto con il picco teorico.

## File

| File | Scopo |
|---|---|
| `es05.sh` | ricognizione, baseline, serie di run (una cartella per configurazione) e raccolta di input, output e `sacct` con tabella riassuntiva |

## Riferimenti del corso

I file di input e gli script batch del corso sono in
`/srv/data/wilson/project/hpc4ai/exercises/benchmark/` e non vanno modificati.
Secondo la consegna gli script caricano `GCC/13.2.0`, `OpenMPI/4.1.6` e poi
`HPL/2.3` o `HPCG/3.1`, richiedono nodi esclusivi con `--mem=0`. `HPL.dat` parte
da `N=12288`, `NB=192`, `P=Q=2` (variante `WR11C2R4`); `hpcg.dat` imposta griglia
locale e durata richiesta di 60 s.

## Uso (login node di WILSON)

```bash
bash es05.sh setup     # una volta sola
bash es05.sh node      # confronto delle ripartizioni MPI x OpenMP su un nodo
bash es05.sh repeat    # run 2 e 3 delle ripartizioni HPL, frequenza effettiva
bash es05.sh hpl-scaling    # HPL strong e memory-scaled fino a 8 nodi
bash es05.sh hpcg-scaling   # HPCG weak e strong fino a 8 nodi
bash es05.sh collect   # quando i job sono finiti (squeue vuoto)
```

Tutte le serie usano `--constraint=sandy_bridge`: la partizione `wilson` contiene
nodi Sandy Bridge, Ivy Bridge e Haswell, che non vanno mescolati in una curva.

`setup` stampa i file di riferimento, lo stato delle partizioni `wilson`,
`wilson2` e `lab4` e `module spider` di HPL e HPCG, copia i file in `~/es05/` e
invia tre tipi di job: `lscpu` su un nodo di ciascuna partizione e le baseline HPL e
HPCG con i file del corso non modificati, ognuna nella sua cartella
(`~/es05/hpl/00_baseline`, `~/es05/hpcg/00_baseline`). Non reinvia una cartella che
ha già un `.jobid`.

`node` crea e invia, ognuna nella sua cartella, le configurazioni su un nodo da 16
core: HPL a N = 24576 con il layout della baseline e, a N = 41280 fisso, le
ripartizioni 16×1 (griglie 4×4, 2×8, 1×16), 8×2, 4×4, 2×8 e 1×16 (task MPI ×
thread); HPCG a griglia globale fissa 416×208×208 con 16×1, 8×2, 4×4, 2×8 e 1×16.
Le cartelle copiano i file del corso cambiando solo `N`, `P`, `Q` (righe 6, 11 e 12
di `HPL.dat`), la griglia locale (riga 3 di `hpcg.dat`), le righe `#SBATCH` del
layout, il nome del job, il tempo e il vincolo sul nodo; il log mostra il `diff`
di ogni file rispetto al riferimento.

`repeat` rilancia due volte ciascuna delle 7 ripartizioni HPL a N = 41280 (cartelle
`*_r2`, `*_r3`): le differenze fra layout sono di pochi punti percentuali e il primo
giro ha usato un nodo diverso per ogni layout. Un run 2×8 in più
(`17_N41280_2x8_P1Q2_perf`) esegue `xhpl` sotto `perf stat -e cycles,task-clock`
per misurare la frequenza di clock effettiva (`perfstat.<rank>.txt`), necessaria
per il picco teorico.

`hpl-scaling` usa il layout per nodo fissato in `HPL_TPR` (thread per processo
MPI): strong scaling a N = 41280 da 1 core a 8 nodi (cartelle `S<core>_...`; sotto
`HPL_TPR` core un solo processo con un thread per core), memory-scaled con
N = 41280·√k su k = 2, 4, 8 nodi (`M<nodi>_...`; il punto a 1 nodo è `S016`) e un
run su un nodo a N = 82560 (`R01_...`) per il confronto con il picco.

`hpcg-scaling` usa 16 processi × 1 thread per nodo: weak scaling con griglia locale
104³ da 1 a 128 processi (`W<proc>_...`; il punto a 16 è `10_16x1`) e strong
scaling con griglia globale 256³ (`S<proc>_...`), con griglie locali multiple di 8
e griglia dei processi passata con `--npx/--npy/--npz`.

`collect` scrive, per ogni cartella con un job: input, script batch, riga `sacct`
(stato, exit code, tempo), output completi, righe `WR...`/`PASSED` di HPL e
`Final Summary` di HPCG; in fondo una tabella con un run per riga (nodo, layout,
GFLOP/s, frazione del picco dei core allocati, validazione).

Entrambi scrivono il log in `~/es05/logs/<sottocomando>_<data>.txt`.
