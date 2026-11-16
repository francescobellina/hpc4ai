# Riepilogo finale

Checkpoint sintetici su tutti i risultati della relazione.

:::{table} Riepilogo delle esercitazioni: risultato chiave, esito della validazione e note aperte.
:name: tab-riepilogo

| Esercizio | Risultato chiave | Validazione superata | Note aperte |
|---|---|---|---|
| 1 — Problema di Basilea | In `float32` l'ordine diretto si ferma a $\Delta \approx 2.09\times10^{-4}$; l'ordine inverso raggiunge $\approx 1.08\times10^{-6}$ a $N=10^6$ e si appiattisce a $\approx 9\times10^{-9}$ per $N$ grandi. In `float64` l'ordine è ininfluente ($\Delta \approx 10^{-6}$ da troncamento). | Sì | Run di riferimento sul client macOS; da ripetere su WILSON per uniformità di compilatore/CPU. Parte optional SIMD non svolta. |
| 2 — Parallel Hello, World! | Una riga per thread e $P \times T$ righe nel caso ibrido in tutte le disposizioni; nei job Slurm ogni thread ha un core fisico suo (maschere `0xf`; 0, 16, 1, 17; 0–3 e 4–7). | Sì (13/13 controlli; job `61828`, `61829`, `61830` `COMPLETED 0:0`) | Numerazione delle CPU di `wnode26`–`27` assunta uguale a `wnode25`, non verificata con `lscpu`. |
| 4 — Profiling e data preparation | `compute_statistics` scende da 83.61% a 31.91% di Self (5 rip.; 86.62% → 38.14% a 30 rip.), 10.3× sulla fase; speedup complessivo su WILSON **3.83×** (mediane 1.902 s → 0.497 s, job 61207; 3.82× nel job 61199); `perf stat`: IPC 0.52 → 2.12, cache miss −79.6% (189.6 M → 38.6 M). | Sì (`1024 32 1 check`, `65536 256 1 check`, checksum completo entro la tolleranza della consegna) | Nessuna sulle misure: log completi in `results/es04/`. |
| 5 — HPL e HPCG | Un nodo: HPL 2 × 8, $260.3 \pm 3.1$ GFLOP/s (84.8% del picco di 307 GFLOP/s a 2.40 GHz misurati; 87.4% a $N$ = 82560); HPCG 16 × 1, 8.70 GFLOP/s (2.83%). Scaling fino a 8 nodi: HPL memory-scaled con efficienza 0.87, 0.85, 0.55 (1144 GFLOP/s, 46.6%); HPL strong con minimo di tempo a 4 nodi; HPCG weak 44.6 GFLOP/s (efficienza per nodo 0.64); HPCG strong con massimo a 2 nodi, poi `DDOT` fino al 77% del tempo. | Sì (36 run HPL `PASSED`, 21 run HPCG `VALID`, 57 job `COMPLETED 0:0`) | Un run per punto di scaling: il calo a 8 nodi andrebbe ripetuto, anche con griglia 2 × 8. Classifica delle ripartizioni non ricontrollata a $N$ = 82560. |

:::

## Stato complessivo

- **Esercitazione 1** — validata su client; risultato coerente con la teoria
  (crossover a $n \approx 1/\sqrt{\varepsilon\,S}$). Da completare: eventuale
  versione SIMD (Optional) e misura dei tempi.
- **Esercitazione 2** — completata su WILSON: test brevi OpenMP e MPI sul login
  node e i tre job Slurm (OpenMP, MPI, ibrido su 2 nodi), tutti con il numero di
  righe atteso e le maschere di affinità.
- **Esercitazione 4** — completata su WILSON in un unico job (`61207`, `wnode25`,
  `gcc 11.5.0`): validazione `PASS` a dimensione piccola e piena; `compute_statistics`
  passa da 83.61% a 31.91% di Self (10.3× sulla fase), con speedup wall-clock 3.83×
  e conferma hardware da `perf stat` (cicli −76.3%, cache miss −79.6%, IPC da 0.52
  a 2.12).

- **Esercitazione 5** — completata su nodi Sandy Bridge (`wnode01`–`08`):
  ripartizione migliore 2 × 8 per HPL e 16 × 1 per HPCG, picco stimato con la
  frequenza misurata; scaling fino a 8 nodi per HPL (strong e memory-scaled) e HPCG
  (weak e strong), con confronto finale fra HPL, HPCG e picco.

## Fonti di errore e limiti

- Esercitazione 1: il pairing compilatore/CPU influenza gli ultimi bit; le
  conclusioni sull'ordine sono robuste, i valori assoluti sono specifici della
  macchina di misura.
- Esercitazione 2: la maschera è quella del processo, non dice su quale core gira
  ogni singolo thread; sul login node `mpiexec` applica le regole di Open MPI, non
  quelle di Slurm.
- Esercitazione 4: `perf` campiona tempo, non cause; il limite di memoria è
  dedotto dal codice, dal modello di traffico e dai contatori `perf stat`. La quota
  $f$ dell'hotspot ha un errore di campionamento ($\pm 0.027$ a 183 campioni), che
  sposta il bound di Amdahl fra 5.2× e 7.3×; lo speedup misurato (3.83×) è
  ripetibile fra job indipendenti (3.82× nel job 61199).
- Esercitazione 5: la dispersione fra run HPL identici è circa l'1%, confrontabile
  con le differenze fra le ripartizioni migliori; i nodi non sono identici
  (`wnode05` circa −2%). La frequenza per il picco è misurata durante HPL a 16
  core e applicata anche a HPCG e ai run con meno core, dove il turbo la alza (il
  run HPL da 1 core supera il picco a 2.40 GHz). Gli studi di scaling hanno un run
  per punto; i log non separano latenza di rete e attesa nelle somme globali di
  HPCG.
