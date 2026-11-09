# Riepilogo finale

Checkpoint sintetici su tutti i risultati della relazione.

:::{table} Riepilogo delle esercitazioni: risultato chiave, esito della validazione e note aperte.
:name: tab-riepilogo

| Esercizio | Risultato chiave | Validazione superata | Note aperte |
|---|---|---|---|
| 1 — Problema di Basilea | In `float32` l'ordine diretto si ferma a $\Delta \approx 2.09\times10^{-4}$; l'ordine inverso raggiunge $\approx 1.08\times10^{-6}$ a $N=10^6$ e si appiattisce a $\approx 9\times10^{-9}$ per $N$ grandi. In `float64` l'ordine è ininfluente ($\Delta \approx 10^{-6}$ da troncamento). | Sì | Run di riferimento sul client macOS; da ripetere su WILSON per uniformità di compilatore/CPU. Parte optional SIMD non svolta. |
| 2 — Parallel Hello, World! | Una riga per thread (memoria condivisa); $P \times T$ righe nel caso ibrido. | Parziale | Validazione locale Python superata (4 righe attese/osservate). Mancano le esecuzioni Slurm OpenMP/MPI/ibrido su WILSON e le maschere di affinità. |
| 4 — Profiling e data preparation | `compute_statistics` scende da 83.61% a 31.91% di Self (5 rip.; 86.62% → 38.14% a 30 rip.), 10.3× sulla fase; speedup complessivo su WILSON **3.83×** (mediane 1.902 s → 0.497 s, job 61207; 3.82× nel job 61199); `perf stat`: IPC 0.52 → 2.12, cache miss −79.6% (189.6 M → 38.6 M). | Sì (`1024 32 1 check`, `65536 256 1 check`, checksum completo entro la tolleranza della consegna) | Nessuna sulle misure: log completi in `results/es04/`. |

:::

## Stato complessivo

- **Esercitazione 1** — validata su client; risultato coerente con la teoria
  (crossover a $n \approx 1/\sqrt{\varepsilon\,S}$). Da completare: eventuale
  versione SIMD (Optional) e misura dei tempi.
- **Esercitazione 2** — schema di validazione definito e applicato localmente; il
  criterio di accettazione su WILSON è il confronto output/richiesta Slurm.
- **Esercitazione 4** — completata su WILSON in un unico job (`61207`, `wnode25`,
  `gcc 11.5.0`): validazione `PASS` a dimensione piccola e piena; `compute_statistics`
  passa da 83.61% a 31.91% di Self (10.3× sulla fase), con speedup wall-clock 3.83×
  e conferma hardware da `perf stat` (cicli −76.3%, cache miss −79.6%, IPC da 0.52
  a 2.12).

## Fonti di errore e limiti

- Esercitazione 1: il pairing compilatore/CPU influenza gli ultimi bit; le
  conclusioni sull'ordine sono robuste, i valori assoluti sono specifici della
  macchina di misura.
- Esercitazione 2: la demo Python non prova il parallelismo su più core per via
  del GIL; i run su WILSON sono necessari per la conclusione.
- Esercitazione 4: `perf` campiona tempo, non cause; il limite di memoria è
  dedotto dal codice, dal modello di traffico e dai contatori `perf stat`. La quota
  $f$ dell'hotspot ha un errore di campionamento ($\pm 0.027$ a 183 campioni), che
  sposta il bound di Amdahl fra 5.2× e 7.3×; lo speedup misurato (3.83×) è
  ripetibile fra job indipendenti (3.82× nel job 61199).
