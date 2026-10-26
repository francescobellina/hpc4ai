# Riferimento Git

Nel workflow del corso, controlla lo stato prima e dopo una modifica:

```bash
git status
git pull --ff-only
git add <FILE>
git commit -m "Descrivi la modifica"
git push
```

`pull --ff-only` aggiorna il branch solo quando Git può avanzare senza creare un merge. Se rifiuta, controlla modifiche locali e cronologia; non forzare l'aggiornamento. La pagina [Ambiente di lavoro e sincronizzazione](../workflow/overview.md) descrive il flusso tra le postazioni.
