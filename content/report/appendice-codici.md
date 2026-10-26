# Appendice — Codici

Codice completo di ogni esercizio, in una cartella per esercizio. Ogni cartella
contiene un `README.md` con dipendenze, comandi di build/esecuzione e parametri di
default. Nel corpo della relazione restano solo brevi estratti a supporto della
discussione.

| Esercizio | Cartella | Contenuto |
|---|---|---|
| 1 — Problema di Basilea | [`codes/exec1/`](codes/exec1/README.md) | `basel_naive.c` — somma parziale di $\zeta(2)$, ordine e precisione a runtime |
| 2 — Parallel Hello, World! | [`codes/exec2/`](codes/exec2/README.md) | programmi a memoria condivisa (OpenMP) e ibrido (MPI + OpenMP); script Slurm |

Il notebook [`report-exercises.ipynb`](notebooks/report-exercises.ipynb) contiene
la versione Python/NumPy dell'Esercitazione 1 (studio di convergenza e grafici) e
i template di riferimento per l'Esercitazione 2 (C, MPI, Slurm).

:::{note}
Le cartelle `codes/` sono escluse dalla build del libro: il codice è materiale
della relazione, non una pagina navigabile del sito.
:::
