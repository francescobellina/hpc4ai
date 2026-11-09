# codes/exec5 — Benchmarking e scaling con HPL e HPCG

Esercitazione 5 della relazione: HPL e HPCG su WILSON, confronto delle opzioni di
parallelizzazione su un nodo, scaling, confronto con il picco teorico.

## File

| File | Scopo |
|---|---|
| `es05.sh` | ricognizione, cartelle di lavoro, invio delle baseline e raccolta di input, output e `sacct` |

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
bash es05.sh collect   # quando i job sono finiti (squeue vuoto)
```

`setup` stampa i file di riferimento, lo stato delle partizioni `wilson`,
`wilson2` e `lab4` e `module spider` di HPL e HPCG, copia i file in `~/es05/` e
invia tre tipi di job: `lscpu` su un nodo di ciascuna partizione e le baseline HPL e
HPCG con i file del corso non modificati, ognuna nella sua cartella
(`~/es05/hpl/00_baseline`, `~/es05/hpcg/00_baseline`). Non reinvia una cartella che
ha già un `.jobid`.

`collect` scrive, per ogni cartella con un job: input, script batch, riga `sacct`
(stato, exit code, tempo), output completi, righe `WR...`/`PASSED` di HPL e
`Final Summary` di HPCG.

Entrambi scrivono il log in `~/es05/logs/<sottocomando>_<data>.txt`.
