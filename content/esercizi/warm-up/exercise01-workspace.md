# Esercizio 1.1 — Creare il workspace locale del corso

## Obiettivo

Riprodurre il primo passo del warm-up del corso e creare un workspace locale
chiaramente associato all'username WILSON `fbellina2`.

## Dove eseguire

**Client di laboratorio** (la macchina locale del laboratorio), non WILSON.

## Procedura

Per la prima creazione del workspace, esegui:

```bash
cd
pwd
echo $HOME
mkdir fbellina2
cd fbellina2
mkdir hpc-lab-exercise
cd hpc-lab-exercise
pwd
```

Il primo `pwd` mostra la home locale. L'ultimo `pwd` deve puntare a un path che
termina con:

```text
fbellina2/hpc-lab-exercise
```

## Domande

- Perché la directory prende il nome dell'account WILSON?
- Perché il workspace del client non va confuso con la home remota di WILSON?
- Cosa contiene `$HOME` prima e dopo il cambio di directory?

::::{dropdown} Soluzione / verifiche attese

Il workspace esiste sul client sotto una directory chiamata `fbellina2` e la shell
è dentro `hpc-lab-exercise`. `$HOME` continua a puntare alla home dell'account
locale anche dopo che `cd` ha cambiato la directory di lavoro corrente.

::::
