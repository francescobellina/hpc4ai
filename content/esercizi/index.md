# Esercizi

Gli esercizi sono la parte pratica del corso: il warm-up per prendere confidenza con
client, GitHub e WILSON, poi gli **esercizi per la relazione**, numerati come nella
[traccia del corso](https://virgilio.mib.infn.it/~marcoce/teaching/hpc4ai/content/exercises/index.html).
Ogni pagina è il quaderno completo dell'esercizio: dati, log, script e dettagli. La
[relazione](../relazione/index.md) ne è la sintesi, in inglese.

All'inizio di ogni esercizio, subito dopo la consegna, il riquadro **Teoria di
riferimento** rimanda alle sezioni dei capitoli di teoria che servono.

## Esercizi per la relazione

| Esercizio | Argomento | Teoria di riferimento |
|---|---|---|
| [1 — Problema di Basilea](es01-basilea.md) | aritmetica in virgola mobile, ordine di somma, troncamento contro arrotondamento | cap. 1 |
| [2 — Parallel Hello, World!](es02-parallel-hello-world.md) | thread OpenMP, rank MPI, layout ibrido, Slurm | cap. 2, 4, 5, 6 |
| 3 — Tiny stories, many threads | non ancora svolto; la preparazione è nella [guida di laboratorio](preparazione-laboratorio.md) | — |
| [4 — Profiling e ottimizzazione della data preparation](es04-profiling-data-preparation.md) | profilo con `perf`, hotspot memory-bound, scambio dei cicli, Amdahl | cap. 1, 2, 3 |
| [5 — Benchmarking e scaling con HPL e HPCG](es05-hpl-hpcg.md) | ripartizione MPI × thread, picco teorico, scaling su più nodi | cap. 2, 3, 4, 6 |

Ogni esercizio segue lo schema fisso: **consegna** (evidenziata), **teoria di
riferimento**, **parametri**, **implementazione**, **procedura di validazione**,
**risultati e plot**, **commenti**, **checkpoint**. Il [riepilogo](riepilogo.md)
raccoglie i risultati chiave, l'[appendice](appendice-codici.md) il codice completo.

## Come si scrive la relazione

Dalla traccia del corso. La relazione è individuale, scritta con parole proprie e
basata sulle proprie implementazioni e misure. Va inviata come **singolo PDF**
almeno due settimane prima dell'esame ed è discussa durante la prova orale. Le parti
*Optional* non sono richieste ma sono benvenute. Per ogni esercizio:

- descrivere l'implementazione e la procedura usata per validarla;
- includere solo **brevi** estratti di codice a supporto della discussione, più i
  comandi per compilare ed eseguire;
- fornire il **codice completo a parte** (repository privato condiviso solo con il
  docente, oppure cartella condivisa);
- dichiarare **tutti i parametri** che influenzano il risultato: dimensione del
  problema, precisione numerica, iterazioni e criteri di arresto, seed casuali,
  dataset e configurazione del modello.

Per ogni misura di prestazioni, registrare la macchina: su WILSON la partizione,
il numero e il tipo di nodi, i rank MPI, i thread OpenMP, l'allocazione di CPU e i
moduli caricati; su un altro computer il modello di processore, il sistema operativo
e la versione del compilatore. Riportare i tempi **insieme** alle dimensioni del
problema e delle risorse, e ripetere le esecuzioni brevi quando la loro variabilità
è confrontabile con le differenze studiate.

- **Strong scaling**: dimensione globale fissa, $S_p = T_1/T_p$ ed $E_p = S_p/p$.
- **Weak scaling**: dichiarare esattamente come cresce il problema globale e quale
  convenzione di efficienza si usa.
- Presentare i risultati in grafici o tabelle e discutere le tendenze principali,
  non numeri isolati.

### Checklist del corso per esercizio

| Esercizio | Cosa deve contenere la relazione |
|---|---|
| 1 | precisione usata (opzioni di compilazione o tipi NumPy); quanto la somma in singola precisione si avvicina a $\pi^2/6$; se ordine diretto e inverso coincidono; campionamento di $N$; grafico dell'errore assoluto contro $N$ per i due ordini; dove dominano troncamento e arrotondamento. SIMD opzionale |
| 2 | programmi a memoria condivisa e ibrido MPI/OpenMP con i comandi di build e lancio; run di validazione ($P \times T$ righe, rank, indici dei thread); script batch e output dei run OpenMP, MPI e ibrido; maschere di affinità se riprodotte |
| 3 | velocità seriale, profilo e stima del traffico di memoria per token per i tre modelli; parti parallelizzate e validazione contro l'output seriale; token/s, speedup ed efficienza contro il numero di thread, con i parametri di ogni misura; scaling spiegato con la banda di memoria effettiva. Storie con MPI opzionali |
| 4 | relazione breve: previsione iniziale dell'hotspot e motivazione; macchina e allocazione; comando di compilazione e dimensioni; hotspot dei due profili; estratto del cambio dei cicli; controlli di correttezza; tabella dei tempi prima/dopo; speedup complessivo; stima di Amdahl e spiegazione |
| 5 | parametri di input e script batch di ogni run, con partizione, tipo di nodo, layout e moduli; job ID, risorse richieste, stati finali, tempi; residuo HPL e validità HPCG; confronto su un nodo; HPL strong e memory-scaled (spiegando la differenza); grafici di scaling HPCG basati sul rate, con convenzione di efficienza e durata richiesta; stima del picco con le ipotesi; confronto HPL, HPCG e picco |

La checklist è una sintesi in italiano della traccia del corso: in caso di dubbio
fa fede la [pagina originale](https://virgilio.mib.infn.it/~marcoce/teaching/hpc4ai/content/exercises/index.html).
