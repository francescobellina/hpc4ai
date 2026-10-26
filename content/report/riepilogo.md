# Riepilogo finale

Checkpoint sintetici su tutti i risultati della relazione.

:::{table} Riepilogo delle esercitazioni: risultato chiave, esito della validazione e note aperte.
:name: tab-riepilogo

| Esercizio | Risultato chiave | Validazione superata | Note aperte |
|---|---|---|---|
| 1 — Problema di Basilea | In `float32` l'ordine diretto si ferma a $\Delta \approx 2.09\times10^{-4}$; l'ordine inverso raggiunge $\approx 1.08\times10^{-6}$ a $N=10^6$ e si appiattisce a $\approx 9\times10^{-9}$ per $N$ grandi. In `float64` l'ordine è ininfluente ($\Delta \approx 10^{-6}$ da troncamento). | Sì | Run di riferimento sul client macOS; da ripetere su WILSON per uniformità di compilatore/CPU. Parte optional SIMD non svolta. |
| 2 — Parallel Hello, World! | Una riga per thread (memoria condivisa); $P \times T$ righe nel caso ibrido. | Parziale | Validazione locale Python superata (4 righe attese/osservate). Mancano le esecuzioni Slurm OpenMP/MPI/ibrido su WILSON e le maschere di affinità. |

:::

## Stato complessivo

- **Esercitazione 1** — validata su client; risultato coerente con la teoria
  (crossover a $n \approx 1/\sqrt{\varepsilon\,S}$). Da completare: eventuale
  versione SIMD (Optional) e misura dei tempi.
- **Esercitazione 2** — schema di validazione definito e applicato localmente; il
  criterio di accettazione su WILSON è il confronto output/richiesta Slurm.

## Fonti di errore e limiti

- Esercitazione 1: il pairing compilatore/CPU influenza gli ultimi bit; le
  conclusioni sull'ordine sono robuste, i valori assoluti sono specifici della
  macchina di misura.
- Esercitazione 2: la demo Python non prova il parallelismo su più core per via
  del GIL; i run su WILSON sono necessari per la conclusione.
