# Relazione di laboratorio

Questa sezione raccoglie il materiale per la **relazione di laboratorio** del
corso. Segue le linee guida di stesura: la teoria in una sezione separata, gli
esercizi numerati con uno schema fisso, un riepilogo finale e un'appendice con i
codici completi.

## Struttura della relazione

1. **[Teoria](teoria.md)** — solo i richiami essenziali. La trattazione completa
   resta nel notebook Jupyter.
2. **[Esercitazioni](esercitazioni/index.md)** — numerate progressivamente
   (Esercitazione 1, 2, ...), ciascuna con consegna, implementazione, procedura di
   validazione, risultati e plot, commenti e checkpoint.
3. **[Riepilogo finale](riepilogo.md)** — tabella di checkpoint su tutti i
   risultati.
4. **[Appendice — Codici](appendice-codici.md)** — codice completo in una cartella
   per esercizio (`codes/execN/`), ordinata e linkata.

Il notebook [`report-exercises.ipynb`](notebooks/report-exercises.ipynb) contiene
la versione eseguibile (Python/NumPy) dell'Esercitazione 1 e il materiale di
riferimento dell'Esercitazione 2: è la trattazione estesa che la teoria qui
riassume.

## Due esercitazioni

1. **Problema di Basilea** — aritmetica in virgola mobile: somme parziali di
   $\zeta(2)$ in singola precisione, ordine di somma, errore di troncamento
   contro errore di arrotondamento.
2. **Parallel Hello, World!** — organizzazione di un'esecuzione parallela:
   thread OpenMP, rank MPI, layout ibrido, scheduling Slurm.

## Come si scrive la relazione

Inviare la relazione come **singolo PDF** almeno due settimane prima dell'esame;
la relazione è discussa durante la prova orale. Per ogni esercizio:

- descrivere l'implementazione e la procedura usata per validarla;
- includere solo **brevi** estratti di codice a supporto della discussione, più i
  comandi per compilare ed eseguire;
- fornire il **codice completo a parte** (repository privato o cartella condivisa,
  qui in `codes/`);
- dichiarare **tutti i parametri** che influenzano il risultato: dimensione del
  problema, precisione numerica, iterazioni e criteri di arresto, seed casuali,
  dataset e configurazione del modello.

Per ogni misura di prestazioni, registrare la macchina: su WILSON la partizione,
il numero e il tipo di nodi, i rank MPI, i thread OpenMP, l'allocazione di CPU e i
moduli caricati; su un laptop il modello di processore, il sistema operativo e la
versione del compilatore. Riportare i tempi di esecuzione **insieme** alle
dimensioni del problema e delle risorse. Ripetere le esecuzioni brevi quando la
loro variabilità è confrontabile con le differenze studiate.

Le definizioni di scaling (speedup, efficienza) sono nella [Teoria](teoria.md).
