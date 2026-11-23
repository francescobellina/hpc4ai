# codes/exec3 — Tiny stories, many threads

Esercitazione 3 della relazione: inferenza di `llama2.c` con i modelli TinyStories
(15M, 42M, 110M) su un nodo WILSON, profilo del programma seriale, versioni OpenMP
del forward pass, scaling e banda di memoria effettiva.

## File

| File | Scopo |
|---|---|
| `run.c` | programma seriale del corso, estratto dal log; SHA256 `2eebe23b…` uguale alla copia in `/srv/data/wilson/project/hpc4ai/exercises/tiny_stories/` |
| `run_omp_mm.c` | `run.c` con `#pragma omp parallel for` in `matmul` |
| `run_omp.c` | come `run_omp_mm.c`, più il ciclo sulle teste dell'attenzione in `forward` |
| `config.c` | stampa la configurazione (intestazione) e la dimensione di un `.bin`, per i byte per token |
| `triad.c` | banda di memoria con il kernel triad di STREAM (3 array da 4·10⁷ `double`) |
| `es03.sh` | `setup` (copia, compilazione, job di baseline), `omp` (versioni OpenMP e job `omp_job.sh`), `collect` (log unico) |
| `omp_job.sh` | job OpenMP: profilo senza inlining, configurazione, scaling 1–16 thread con 3 ripetizioni, confronto `close`/`spread` |
| `analyze_es03.py` | legge il log di `collect` e produce le tabelle (Markdown) e le figure `content/esercizi/figures/es03-*.png` |

## Uso (login node di WILSON)

```bash
bash -l es03.sh setup     # una volta: baseline seriale, gprof, perf, triad
bash -l es03.sh omp       # serve out_<modello>_r1.txt della baseline per la validazione
bash -l es03.sh collect   # quando squeue è vuoto
```

Tutti i job usano la partizione `wilson` con `--constraint=sandy_bridge`, un nodo
esclusivo e `GCC/13.2.0`. L'ultima riga di `omp_job.sh` (`grep -c DIVERSO …` con
`set -o pipefail`) fa uscire il job con codice 1 quando nessun testo è diverso: lo
stato `FAILED 1:0` di `sacct` va letto insieme alle righe `testo` di `scaling.txt`.

## Analisi (Mac)

```bash
.venv/bin/python codes/exec3/analyze_es03.py results/es03/collect_20261123_100859.txt
```
