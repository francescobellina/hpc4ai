# Esercizio 1.3 — Trasferire, connettersi e documentare una sessione WILSON

## Obiettivo

Esercitare il confine tra client di laboratorio e WILSON senza salvare credenziali
né inventare impostazioni specifiche del cluster.

## 1. Connettersi dal client

```bash
ssh -l fbellina2 wilson.mib.infn.it
```

Prima di eseguire altri comandi, controlla il prompt e conferma che la sessione è
remota.

## 2. Ispezionare l'ambiente software su WILSON

```bash
module use /srv/software/easybuild/hmns/x86-64-v2/modules/all/Core
module list
module avail
```

Carica solo i moduli esplicitamente richiesti dall'esercizio attivo. Non indovinare
nomi o versioni di moduli.

## 3. Trasferire un sorgente quando richiesto

Esegui `scp` sul client con il file sorgente e la destinazione richiesti
dall'esercizio:

```bash
scp <FILE_SORGENTE> fbellina2@wilson.mib.infn.it:<DESTINAZIONE_REMOTA>
```

## 4. Eseguire e salvare il risultato remoto

Compila/esegui su WILSON secondo l'esercizio corrente. Registra nelle note comandi,
ambiente software e nome del file di risultato.

```bash
module load GCC/13.2.0
gcc -fopenmp -o thread-count thread-count.c
OMP_NUM_THREADS=4 ./thread-count > wilson-output.txt
head -n 5 wilson-output.txt
exit
```

## 5. Riportare il risultato sul client

Dal client:

```bash
scp fbellina2@wilson.mib.infn.it:<RISULTATO_REMOTO> <DESTINAZIONE_LOCALE>
```

Poi metti nel repository solo sorgenti, note o risultati piccoli e curati, e
sincronizza con GitHub.

## Importante

Non aggiungere al repository password, chiavi SSH private, token GitHub o file di
autenticazione. Username e hostname non bastano per autenticarsi e possono essere
documentati; le credenziali restano fuori da Git.

::::{dropdown} Soluzione / esito atteso

La sessione distingue chiaramente i comandi del client da quelli di WILSON, usa il
login `fbellina2@wilson.mib.infn.it`, registra solo configurazione software
confermata e trasferisce solo i file richiesti dall'esercizio. Nessuna credenziale
è salvata in Git.

::::
