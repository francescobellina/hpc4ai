# Riepilogo finale

Checkpoint sintetici su tutti i risultati della relazione.

:::{table} Riepilogo delle esercitazioni: risultato chiave, esito della validazione e note aperte.
:name: tab-riepilogo

| Esercizio | Risultato chiave | Validazione superata | Note aperte |
|---|---|---|---|
| 1 — Problema di Basilea | In `float32` l'ordine diretto si ferma a $\Delta \approx 2.09\times10^{-4}$; l'ordine inverso raggiunge $\approx 1.08\times10^{-6}$ a $N=10^6$ e si appiattisce a $\approx 9\times10^{-9}$ per $N$ grandi. In `float64` l'ordine è ininfluente ($\Delta \approx 10^{-6}$ da troncamento). | Sì | Run di riferimento sul client macOS; da ripetere su WILSON per uniformità di compilatore/CPU. Parte optional SIMD non svolta. |
| 2 — Parallel Hello, World! | Una riga per thread (memoria condivisa); $P \times T$ righe nel caso ibrido. | Parziale | Validazione locale Python superata (4 righe attese/osservate). Mancano le esecuzioni Slurm OpenMP/MPI/ibrido su WILSON e le maschere di affinità. |
| 4 — Profiling e data preparation | `compute_statistics` scende da 86.20% a 37.39% di Self (10.5× sulla fase); speedup complessivo su WILSON **3.85×–3.90×** (1.910 s → 0.496 s; `/usr/bin/time` 1.91 s → 0.49 s), `perf stat`: IPC 0.51 → 2.12, cache miss −79.6% (189.6 M → 38.6 M). | Sì (`1024 32 1` e `65536 256 1`, entrambe le versioni) | Nessuna: profili `before`/`after` (30 rip.) e contatori `perf stat` completi. |

:::

## Stato complessivo

- **Esercitazione 1** — validata su client; risultato coerente con la teoria
  (crossover a $n \approx 1/\sqrt{\varepsilon\,S}$). Da completare: eventuale
  versione SIMD (Optional) e misura dei tempi.
- **Esercitazione 2** — schema di validazione definito e applicato localmente; il
  criterio di accettazione su WILSON è il confronto output/richiesta Slurm.
- **Esercitazione 4** — completata su WILSON (`wnode25`, `gcc 11.5.0`): validazione
  `PASS` a dimensione piccola e piena; `compute_statistics` passa da 86.20% a 37.39%
  di Self (10.5× sulla fase), con speedup wall-clock 3.85×–3.90× e conferma hardware
  da `perf stat` (cicli −76.5%, cache miss −79.6%, IPC da 0.51 a 2.12).

## Fonti di errore e limiti

- Esercitazione 1: il pairing compilatore/CPU influenza gli ultimi bit; le
  conclusioni sull'ordine sono robuste, i valori assoluti sono specifici della
  macchina di misura.
- Esercitazione 2: la demo Python non prova il parallelismo su più core per via
  del GIL; i run su WILSON sono necessari per la conclusione.
- Esercitazione 4: `perf` campiona tempo, non cause; il limite di memoria è
  dedotto dal codice e dal modello di traffico. L'amplificazione dipende dalla
  riga di cache (8× su x86, 16× su Apple silicon), quindi il modello dei byte dà
  l'ordine di grandezza. Lo speedup di riferimento è 3.85× su WILSON; il 4.1×
  misurato sul client locale è una conferma, non la misura ufficiale.
