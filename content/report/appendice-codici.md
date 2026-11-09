# Appendice — Codici

Codice completo di ogni esercizio, in una cartella per esercizio. Ogni cartella
contiene un `README.md` con dipendenze, comandi di build/esecuzione e parametri di
default. Nel corpo della relazione restano solo brevi estratti a supporto della
discussione.

| Esercizio | Cartella | Contenuto |
|---|---|---|
| 1 — Problema di Basilea | [`codes/exec1/`](codes/exec1/README.md) | `basel_naive.c` — somma parziale di $\zeta(2)$, ordine e precisione a runtime |
| 2 — Parallel Hello, World! | [`codes/exec2/`](codes/exec2/README.md) | programmi a memoria condivisa (OpenMP) e ibrido (MPI + OpenMP); script Slurm |
| 4 — Profiling e ottimizzazione | [`codes/exec4/`](codes/exec4/README.md) | `preprocess.c` originale, `preprocess_rows.c` con i cicli di `compute_statistics` scambiati, `es04_all.sh` che riproduce tutte le misure in un job Slurm (log in `results/es04/`) |
| 5 — HPL e HPCG | [`codes/exec5/`](codes/exec5/README.md) | `es05.sh` (setup, serie di run, raccolta su WILSON) e `analyze_es05.py` (tabelle e figure dai log in `results/es05/`) |

Il notebook [`report-exercises.ipynb`](notebooks/report-exercises.ipynb) contiene
la versione Python/NumPy dell'Esercitazione 1 (studio di convergenza e grafici) e
i template di riferimento per l'Esercitazione 2 (C, MPI, Slurm).

:::{note}
Le cartelle `codes/` sono escluse dalla build del libro: il codice è materiale
della relazione, non una pagina navigabile del sito.
:::
