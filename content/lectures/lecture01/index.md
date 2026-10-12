# Lezione 1 — Dal client a WILSON

Prima parte: concetti di base di HPC e nozioni storiche, da tenere a mente.

Questa lezione fissa il flusso operativo usato per tutto il corso. L'attenzione è
su **dove** il codice viene scritto, sincronizzato, trasferito ed eseguito.

Segue la struttura del warm-up del corso *From the client to WILSON*, integrando
il workflow personale GitHub/VS Code di questo repository.

## Ambienti confermati

| Ambiente | Ruolo |
|---|---|
| Mac / VS Code | ambiente di sviluppo principale, `/Users/francesco/dev/hpc4ai` |
| GitHub | repository canonico: `francescobellina/hpc4ai` |
| PC di laboratorio / client | clone locale e client per gli esercizi sul cluster |
| WILSON | ambiente HPC remoto, `fbellina2@wilson.mib.infn.it` |

## Obiettivi di apprendimento

Alla fine della lezione saprai:

- distinguere gli ambienti Mac, client di laboratorio, GitHub e WILSON;
- creare il workspace locale del corso con l'username WILSON `fbellina2`;
- sincronizzare il repository tra Mac e PC di laboratorio;
- trasferire i file degli esercizi tra client e WILSON quando serve;
- riconoscere se un comando appartiene al client locale o a WILSON;
- ispezionare l'ambiente Lmod senza inventare nomi di moduli;
- conservare sorgenti e risultati utili in modo riproducibile.

## Sequenza dell'esercizio del corso

1. Creare il workspace locale.
2. Scrivere e compilare il programma.
3. Configurare ed eseguire in locale.
4. Trasferire il sorgente e connettersi a WILSON.
5. Preparare l'ambiente software su WILSON con Lmod.
6. Eseguire da remoto e salvare il risultato.
7. Riportare il risultato e conservare il lavoro locale.

## Struttura

1. [Teoria e concetti di workflow](theory.md)
2. [Esempi svolti](examples.md)
3. [Esercizi](exercises/index.md)

Username e hostname WILSON sono confermati in questo progetto. Path remoti,
nomi esatti dei moduli, versioni dei compilatori e comandi dello scheduler
restano specifici dell'esercizio e non vanno indovinati.

Vedi anche la [Guida al laboratorio: client e WILSON](../../workflow/lab-client-wilson.md).
