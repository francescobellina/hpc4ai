# Esercizio 1.2 — Completare un giro di sincronizzazione GitHub

## Obiettivo

Esercitare la sequenza usata per spostare il lavoro da un computer all'altro
passando da GitHub.

## Procedura

Sulla macchina corrente:

```bash
git status
git pull --ff-only
```

Fai una piccola modifica, poi:

```bash
git add -A
git status
git commit -m "Practice repository synchronization"
git push
```

Sulla seconda macchina:

```bash
git status
git pull --ff-only
```

## Domande

- Perché `pull` deve precedere la modifica?
- Qual è la differenza tra `commit` e `push`?

:::{dropdown} Soluzione / discussione
:color: success

Un commit registra una versione in locale. Il push pubblica i commit locali su
GitHub. Il pull recupera i commit remoti. Fare pull prima di modificare riduce la
divergenza tra le copie.

:::
