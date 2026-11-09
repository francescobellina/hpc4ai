# codes/exec4 — Profiling e ottimizzazione della data preparation

Pipeline sintetica di preprocessing su una matrice $N \times D$: statistiche per
feature, standardizzazione, score lineare. Corrisponde all'[Esercitazione 4](../../esercitazioni/es04-profiling-data-preparation.md).

## File

| File | Scopo |
|---|---|
| `preprocess.c` | versione originale, fornita dal corso (invariata) |
| `preprocess_rows.c` | stessa pipeline con i cicli di `compute_statistics` scambiati: accessi contigui |
| `README-esercizio.txt` | readme distribuito con il materiale del corso |
| `es04_all.sh` | tutte le misure della relazione in un solo job Slurm, con riepilogo numerico |

Le due versioni differiscono **solo** in `compute_statistics`. Stesso algoritmo a
due passaggi, stesso ordine di accumulo per feature: il risultato numerico è
identico al bit, non solo equivalente entro tolleranza.

## Build (WILSON)

```bash
gcc -O2 -g -fno-inline -fno-omit-frame-pointer -Wall -Wextra preprocess.c      -lm -o preprocess
gcc -O2 -g -fno-inline -fno-omit-frame-pointer -Wall -Wextra preprocess_rows.c -lm -o preprocess_rows
```

I flag servono al profilo: `-g` per i simboli, `-fno-inline` perché le funzioni
restino visibili, `-fno-omit-frame-pointer` perché `perf -g` risalga lo stack.

## Esecuzione

```bash
salloc -plab4 --nodes=1 --ntasks=1 --cpus-per-task=1 \
    --hint=nomultithread --mem=1G --time=00:15:00

srun --cpu-bind=cores ./preprocess 1024 32 1 check          # validazione
srun --cpu-bind=cores /usr/bin/time -f 'Elapsed seconds: %e' ./preprocess 65536 256 5
srun --cpu-bind=cores perf record -e cpu-clock:u -F 99 -g \
    -o perf-before.data ./preprocess 65536 256 5
perf report --stdio -i perf-before.data
```

La variante ottimizzata usa gli stessi comandi con `preprocess_rows` e
`perf-after.data`. Per il confronto dei profili servono 30 ripetizioni per
entrambi, lasciando 5 per il confronto dei tempi.

## Esecuzione completa in un solo job

`es04_all.sh` raccoglie in un colpo tutti gli output della relazione. Sul login
node di WILSON, nella cartella con `preprocess.c` e `preprocess_rows.c`:

```bash
bash es04_all.sh
```

Compila con i flag sopra, invia un job su `lab4` (1 core, `--mem=1G`), ne attende
la fine con `sbatch --wait` e scrive `es04_run_<data>/es04_<JOBID>.txt`: build con
`diff -u preprocess.c preprocess_rows.c`, nodo e `lscpu`, validazione
`1024 32 1 check` e `65536 256 1 check`, checksum a `100000 256 5` e confronto con
la tolleranza della consegna, 3 run alternate per versione misurate sia dal `time`
di bash sia da GNU time, `perf record`/`perf report` a 5 ripetizioni (comando della
consegna) e a 30, `perf stat -r 3` e un riepilogo con mediane, speedup, quota $f$ e
bound di Amdahl. I `perf-*.data` restano nella cartella di run.

## Parametri di default

| Parametro | Default | Note |
|---|---|---|
| `observations` | `65536` | $N$, matrice da 128 MiB |
| `features` | `256` | $D$, passo fra osservazioni 2048 B |
| `repeats` | `5` | 30 per i profili |
| `check` | assente | quinta parola `check` per validare; mai nelle run temporizzate |

Uso: `./preprocess observations features repeats [check]`.

## Descrizione delle funzioni

| Funzione | Righe | Frequenza | Costo |
|---|---|---|---|
| `generate_data` | 25–31 | una volta | 128 MiB scritti |
| `compute_statistics` | 34–50 | ogni ripetizione | 2 passaggi strided sulla matrice, 2 GiB di traffico |
| `standardize` | 53–59 | ogni ripetizione | 256 MiB, contiguo |
| `compute_scores` | 62–71 | ogni ripetizione | 128 MiB, sola lettura contigua |
| `validate` | 74–107 | solo con `check` | fuori dalle misure |
| `main` | 109–157 | — | alloca, genera, cicla su `repeats` con `memcpy` |

## Verifica di equivalenza (senza Slurm)

```bash
./preprocess      1024 32 1 check
./preprocess_rows 1024 32 1 check
```

Atteso: `Validation: PASS` con `max |mean| 2.418e-14` e `max variance error
1.217e-11` in entrambe, e checksum `8173.5024171285777` identico. A dimensione
piena il checksum è `2261357.7191473623`.
