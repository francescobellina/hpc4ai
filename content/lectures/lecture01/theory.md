# Teoria — Dal client a WILSON

Prima parte: concetti di base di HPC e nozioni storiche, da tenere a mente. Poi
WILSON: comandi di base, salvataggio dei programmi, riga di comando, gestione file.

Un workflow HPC separa tre ruoli: l'**ambiente di sviluppo** (dove si scrivono
codice e note), il **controllo di versione** (dove la storia è sincronizzata) e
l'**ambiente di esecuzione** (dove girano i calcoli). In questo progetto sono
VS Code, GitHub e WILSON. Un repository utile risponde a: quale sorgente ha
prodotto il risultato, con quali input, con quale ambiente software, su quale
sistema.

## Client e WILSON

Il client è un Raspberry Pi 5 con account locale `student` condiviso tra corsi: non
è privato e non è salvato, trattalo come spazio temporaneo. WILSON è un cluster
(un nodo principale + fino a 32 nodi di calcolo) con home personale persistente:

```bash
ssh -l fbellina2 wilson.mib.infn.it
```

Il client offre desktop e strumenti locali; WILSON storage persistente, software
gestito e accesso ai nodi di calcolo.

## Moduli d'ambiente

Lmod cambia l'ambiente software attivo modificando le variabili di shell. I moduli
esatti dipendono dal sistema: documentali solo dopo conferma. Vedi il
[Riferimento Lmod](../../reference/lmod.md).

```text
Mac <-> GitHub <-> PC di laboratorio     controllo di versione / sincronizzazione
client di laboratorio <-> WILSON         ssh/scp + esecuzione HPC
```
